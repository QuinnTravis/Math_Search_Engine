"""Run the benchmark against one or more runs (index + retrieval system) and log the result.

Usage:
  python -m mathsearch.evaluate                                     # the three baselines, dev split
  python -m mathsearch.evaluate --runs fixedtok256-minilm:dense --split dev
  python -m mathsearch.evaluate --split both --out results/baseline.json

Every invocation writes one JSON file to results/ with the git commit, machine, benchmark
hash and split seed, the evaluation settings, and for each run: the index configuration,
chunk-length statistics, summary metrics, per-category metrics and per-query results.

Latency: each run first answers every query once untimed (warm-up: loads model weights
into caches), then answers every query again while timed. The time covers the whole
search call, including embedding the query for dense retrieval.
"""
import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from mathsearch import metrics
from mathsearch.corpus import sha256_of
from mathsearch.paths import INDEX_DIR, QUERIES_PATH, REPO_ROOT, RESULTS_DIR
from mathsearch.provenance import git_info, machine_info
from mathsearch.queries import CATEGORIES, all_problems, load_queries
from mathsearch.retrievers import BASELINE_RUNS, load_run

EVAL_DEPTH = 10  # every run returns its top 10; all metrics are computed at or below this depth
METRIC_NAMES = ["span_recall_at_5", "span_recall_at_10", "mrr", "ndcg_at_10"]


def display_path(path):
    """Path relative to the repo root when possible, so logs do not contain my home directory."""
    path = Path(path).resolve()
    if path.is_relative_to(REPO_ROOT):
        return str(path.relative_to(REPO_ROOT))
    return str(path)


def eval_settings():
    """The rules every metric was computed under, logged so old runs stay interpretable."""
    return {
        "depth": EVAL_DEPTH,
        "answer_grade": metrics.ANSWER_GRADE,
        "min_overlap": metrics.MIN_OVERLAP,
        "overlap_measure": "share of the chunk's words on pages inside the span",
        "ndcg_gain": "linear, each span credited once (actual and ideal)",
    }


def split_seed(queries_path):
    """The seed recorded by `make split` in split.json next to the queries file, if any."""
    split_file = Path(queries_path).parent / "split.json"
    if split_file.exists():
        return json.loads(split_file.read_text())["seed"]
    return None


def check_queries(queries, index_info):
    """Stop with a clear message if any query cannot be evaluated against this index."""
    pages_by_book = {book["id"]: book["pages"] for book in index_info["books"]}
    problems = all_problems(queries, pages_by_book)
    if problems:
        lines = [f"{qid}: {'; '.join(msgs)}" for qid, msgs in sorted(problems.items())]
        raise SystemExit("Benchmark has problems, fix them first:\n  " + "\n  ".join(lines))


def run_queries(retriever, queries, chunks):
    """Warm-up pass, then a timed pass. Returns one result dict per query."""
    for query in queries:
        retriever.search(query["query"], EVAL_DEPTH)

    results = []
    for query in queries:
        start = time.perf_counter()
        chunk_ids = retriever.search(query["query"], EVAL_DEPTH)
        latency_ms = (time.perf_counter() - start) * 1000
        retrieved = [chunks[i] for i in chunk_ids]
        results.append({
            "id": query["id"],
            "category": query["category"],
            "latency_ms": latency_ms,
            "retrieved": [f"{c['book']}:{c['page_start']}-{c['page_end']}" for c in retrieved],
            "retrieved_words": [len(c["text"].split()) for c in retrieved],
            **metrics.query_metrics(retrieved, query["labels"]),
        })
    return results


def summarize(per_query, index_info):
    latencies = [r["latency_ms"] for r in per_query]
    retrieved_words = [n for r in per_query for n in r["retrieved_words"]]
    summary = {"num_queries": len(per_query)}
    for name in METRIC_NAMES:
        summary[name] = float(np.mean([r[name] for r in per_query]))
    summary["latency_p50_ms"] = float(np.percentile(latencies, 50))
    summary["latency_p95_ms"] = float(np.percentile(latencies, 95))
    summary["mean_chunk_words"] = index_info["chunk_stats"]["mean_words"]  # over the whole index
    summary["mean_retrieved_chunk_words"] = statistics.mean(retrieved_words) if retrieved_words else 0.0
    return summary


def summarize_by_category(per_query):
    by_category = {}
    for category in CATEGORIES:
        rows = [r for r in per_query if r["category"] == category]
        if rows:
            by_category[category] = {name: float(np.mean([r[name] for r in rows])) for name in METRIC_NAMES}
            by_category[category]["num_queries"] = len(rows)
    return by_category


def evaluate(run_specs, splits, queries_path=QUERIES_PATH, index_root=INDEX_DIR):
    """Evaluate each run on each split and return the full record."""
    all_queries = load_queries(queries_path)
    if not all_queries:
        raise SystemExit(f"No queries found in {queries_path}. Write them with `make label` first.")

    runs = []
    for spec in run_specs:
        index_info, chunks, retriever = load_run(spec, index_root)
        check_queries(all_queries, index_info)
        for split in splits:
            queries = [q for q in all_queries if q["split"] == split]
            per_query = run_queries(retriever, queries, chunks)
            runs.append({
                "run": spec,
                "index": index_info["config"]["name"],
                "system": retriever.name,
                "params": retriever.params,
                "index_info": index_info,
                "split": split,
                "summary": summarize(per_query, index_info),
                "per_category": summarize_by_category(per_query),
                "per_query": per_query,
            })

    return {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": git_info(),
        "machine": machine_info(),
        "benchmark": {
            "path": display_path(queries_path),
            "sha256": sha256_of(queries_path),
            "num_queries": len(all_queries),
            "split_seed": split_seed(queries_path),
        },
        "eval_settings": eval_settings(),
        "runs": runs,
    }


def format_table(record):
    header = ("| Index | System | Split | n | Avg chunk words | SpanRecall@5 | SpanRecall@10 | MRR | nDCG@10 "
              "| P50 ms | P95 ms |")
    lines = [header, "|" + " --- |" * 11]
    for run in record["runs"]:
        s = run["summary"]
        lines.append(
            f"| {run['index']} | {run['system']} | {run['split']} | {s['num_queries']} | "
            f"{s['mean_chunk_words']:.0f} | {s['span_recall_at_5']:.3f} | {s['span_recall_at_10']:.3f} | "
            f"{s['mrr']:.3f} | {s['ndcg_at_10']:.3f} | {s['latency_p50_ms']:.1f} | {s['latency_p95_ms']:.1f} |"
        )
    return "\n".join(lines)


def default_out_path(run_specs, splits):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = "+".join(spec.replace(":", "-") for spec in run_specs)
    return RESULTS_DIR / "runs" / f"{stamp}_{name}_{'+'.join(splits)}.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", nargs="+", default=BASELINE_RUNS, help="<index>:<system> pairs")
    parser.add_argument("--split", default="dev", choices=["dev", "test", "both"])
    parser.add_argument("--queries", type=Path, default=QUERIES_PATH)
    parser.add_argument("--out", type=Path, help="where to write the record (default: results/runs/<timestamp>...json)")
    args = parser.parse_args()

    splits = ["dev", "test"] if args.split == "both" else [args.split]
    if "test" in splits:
        print("Note: includes the held-out split. Report it once per phase; never tune on it.\n")

    record = evaluate(args.runs, splits, args.queries)
    if record["git"]["dirty"]:
        print("Warning: uncommitted changes. This run is logged, but its commit hash does not fully describe the code.\n")

    out_path = args.out or default_out_path(args.runs, splits)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2) + "\n")
    print(format_table(record))
    print(f"\nLogged to {out_path}")


if __name__ == "__main__":
    main()
