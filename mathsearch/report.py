"""Print one results table from every logged run in results/.

Usage:  python -m mathsearch.report [--split test]

Runs scored against different versions of benchmark/queries.jsonl are not comparable,
so the table shows a short hash of the benchmark file and warns if they differ.
"""
import argparse
import json
from pathlib import Path

from mathsearch.paths import RESULTS_DIR

HEADER = ("| Run file | Index | System | Split | n | Avg chunk words | SpanRecall@5 | SpanRecall@10 | MRR "
          "| nDCG@10 | P50 ms | P95 ms | Commit | Benchmark |")


def load_records(results_dir=RESULTS_DIR):
    records = []
    for path in sorted(results_dir.rglob("*.json")):
        record = json.loads(path.read_text())
        if "runs" in record:
            records.append((path, record))
    return records


def table_rows(records, results_dir=RESULTS_DIR, split=None):
    rows = []
    for path, record in records:
        for run in record["runs"]:
            if split and run["split"] != split:
                continue
            s = run["summary"]
            rows.append(
                f"| {path.relative_to(results_dir)} | {run['index']} | {run['system']} | {run['split']} | "
                f"{s['num_queries']} | {s['mean_chunk_words']:.0f} | {s['span_recall_at_5']:.3f} | "
                f"{s['span_recall_at_10']:.3f} | {s['mrr']:.3f} | {s['ndcg_at_10']:.3f} | "
                f"{s['latency_p50_ms']:.1f} | {s['latency_p95_ms']:.1f} | "
                f"{(record['git']['commit'] or '?')[:7]} | {record['benchmark']['sha256'][:8]} |"
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=["dev", "test"])
    parser.add_argument("--results", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    records = load_records(args.results)
    if not records:
        raise SystemExit(f"No run records in {args.results}")
    print(HEADER)
    print("|" + " --- |" * 14)
    print("\n".join(table_rows(records, args.results, args.split)))

    hashes = {record["benchmark"]["sha256"] for _, record in records}
    if len(hashes) > 1:
        print("\nWarning: these runs used different versions of the benchmark. Re-run older configurations before comparing.")
    settings = {json.dumps(record.get("eval_settings"), sort_keys=True) for _, record in records}
    if len(settings) > 1:
        print("\nWarning: these runs used different evaluation settings (see eval_settings in each file).")


if __name__ == "__main__":
    main()
