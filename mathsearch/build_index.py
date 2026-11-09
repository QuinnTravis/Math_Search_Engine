"""Build search indexes from the corpus: extract pages, chunk, embed, save.

Usage:
  python -m mathsearch.build_index                              # every configuration
  python -m mathsearch.build_index --config fixedtok256-minilm  # just one

Output folder data/index/<config name>/:
  chunks.jsonl   one chunk per line: id, book, page_start, page_end, page_words, text
  dense.faiss    the FAISS index (row i is chunk id i)
  config.json    configuration, chunk-length statistics, books (with hashes), git commit
"""
import argparse
import json
import statistics
from datetime import datetime, timezone

from mathsearch import dense
from mathsearch.chunking import fixed_size_chunks, token_capped_chunks
from mathsearch.corpus import load_books, verify_books
from mathsearch.extract import load_pages
from mathsearch.paths import CORPUS_MANIFEST, INDEX_DIR, PAGES_DIR
from mathsearch.provenance import git_info

CONFIGS = {
    # The original project's pipeline, unchanged.
    "fixed400-minilm": {
        "name": "fixed400-minilm",
        "chunker": "fixed_words",
        "chunk_size": 400,
        "model": dense.MODEL_NAME,
        "faiss_index": "IndexFlatIP",
    },
    # Same pipeline, but every chunk fits the model's 256-token input, so nothing is truncated.
    "fixedtok256-minilm": {
        "name": "fixedtok256-minilm",
        "chunker": "fixed_tokens",
        "max_content_tokens": 254,  # the model's 256-token limit minus [CLS] and [SEP]
        "model": dense.MODEL_NAME,
        "faiss_index": "IndexFlatIP",
    },
}
BASELINE_CONFIG = CONFIGS["fixed400-minilm"]


def make_chunks(books, config, pages_dir, model=None):
    chunks = []
    for book in books:
        pages = load_pages(book, pages_dir)
        if config["chunker"] == "fixed_words":
            chunks.extend(fixed_size_chunks(book["id"], pages, config["chunk_size"]))
        elif config["chunker"] == "fixed_tokens":
            count = lambda words: dense.token_counts(model, words)  # noqa: E731
            chunks.extend(token_capped_chunks(book["id"], pages, count, config["max_content_tokens"]))
        else:
            raise ValueError(f"unknown chunker {config['chunker']!r}")
    for chunk_id, chunk in enumerate(chunks):
        chunk["id"] = chunk_id
    return chunks


def chunk_stats(chunks, token_lengths=None, token_limit=None):
    """Chunk-length statistics, logged with the index and with every evaluation run.
    Recall-style metrics favour longer chunks, so length must be reported next to them."""
    words = [len(chunk["text"].split()) for chunk in chunks]
    stats = {
        "num_chunks": len(chunks),
        "mean_words": statistics.mean(words),
        "median_words": statistics.median(words),
    }
    if token_lengths:
        stats["mean_tokens"] = statistics.mean(token_lengths)
        stats["median_tokens"] = statistics.median(token_lengths)
        stats["max_tokens"] = max(token_lengths)
        # What each vector actually sees: tokens past the limit are cut off before embedding.
        stats["mean_embedded_tokens"] = statistics.mean(min(n, token_limit) for n in token_lengths)
        stats["token_limit"] = token_limit
        stats["share_over_token_limit"] = sum(n > token_limit for n in token_lengths) / len(token_lengths)
    return stats


def write_chunks(chunks, path):
    with open(path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def build_index(config=BASELINE_CONFIG, manifest=CORPUS_MANIFEST, index_root=INDEX_DIR,
                pages_dir=PAGES_DIR, with_dense=True):
    """Build and save one index. `with_dense=False` skips the model entirely (used by fast tests)."""
    books = load_books(manifest)
    problems = verify_books(books)
    if problems:
        raise SystemExit("Corpus check failed:\n  " + "\n  ".join(problems))
    if config["chunker"] == "fixed_tokens" and not with_dense:
        raise ValueError("token-capped chunking needs the model's tokenizer")

    out_dir = index_root / config["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    model = dense.load_model(config["model"]) if with_dense else None

    chunks = make_chunks(books, config, pages_dir, model)
    write_chunks(chunks, out_dir / "chunks.jsonl")

    if with_dense:
        texts = [chunk["text"] for chunk in chunks]
        stats = chunk_stats(chunks, dense.token_lengths(model, texts), model.max_seq_length)
        if config["chunker"] == "fixed_tokens" and stats["share_over_token_limit"] > 0:
            raise SystemExit("Token-capped chunks exceed the model's limit; the chunker has a bug.")
        dense.save_index(dense.build_flat_index(dense.embed(model, texts, show_progress=True)),
                         out_dir / "dense.faiss")
    else:
        stats = chunk_stats(chunks)
    print(f"{config['name']}: {json.dumps(stats)}")

    info = {
        "config": config,
        "chunk_stats": stats,
        "books": [{"id": b["id"], "pages": b["pages"], "sha256": b["sha256"]} for b in books],
        "has_dense": with_dense,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": git_info(),
    }
    (out_dir / "config.json").write_text(json.dumps(info, indent=2) + "\n")
    print(f"Index written to {out_dir}")
    return out_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", nargs="+", choices=list(CONFIGS), default=list(CONFIGS))
    args = parser.parse_args()
    for name in args.config:
        build_index(CONFIGS[name])


if __name__ == "__main__":
    main()
