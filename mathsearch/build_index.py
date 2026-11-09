"""Build a search index from the corpus: extract pages, chunk, embed, save.

Usage:  python -m mathsearch.build_index            (writes data/index/fixed400-minilm/)

Output folder:
  chunks.jsonl   one chunk per line: id, book, page_start, page_end, text
  dense.faiss    the FAISS index (row i is chunk id i)
  config.json    the configuration, the books (with hashes) and the git commit it was built from
"""
import argparse
import json
from datetime import datetime, timezone

from mathsearch import dense
from mathsearch.chunking import fixed_size_chunks
from mathsearch.corpus import load_books, verify_books
from mathsearch.extract import load_pages
from mathsearch.paths import CORPUS_MANIFEST, INDEX_DIR, PAGES_DIR
from mathsearch.provenance import git_info

# The original project's pipeline. Phase 1 adds new configurations next to this one.
BASELINE_CONFIG = {
    "name": "fixed400-minilm",
    "chunker": "fixed_words",
    "chunk_size": 400,
    "model": dense.MODEL_NAME,
    "faiss_index": "IndexFlatIP",
}


def make_chunks(books, config, pages_dir):
    chunks = []
    for book in books:
        pages = load_pages(book, pages_dir)
        chunks.extend(fixed_size_chunks(book["id"], pages, config["chunk_size"]))
    for chunk_id, chunk in enumerate(chunks):
        chunk["id"] = chunk_id
    return chunks


def write_chunks(chunks, path):
    with open(path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def build_index(config=BASELINE_CONFIG, manifest=CORPUS_MANIFEST, index_root=INDEX_DIR,
                pages_dir=PAGES_DIR, with_dense=True):
    """Build and save one index. `with_dense=False` skips embedding (used by fast tests)."""
    books = load_books(manifest)
    problems = verify_books(books)
    if problems:
        raise SystemExit("Corpus check failed:\n  " + "\n  ".join(problems))

    out_dir = index_root / config["name"]
    out_dir.mkdir(parents=True, exist_ok=True)

    chunks = make_chunks(books, config, pages_dir)
    write_chunks(chunks, out_dir / "chunks.jsonl")
    print(f"{len(chunks)} chunks from {len(books)} books")

    if with_dense:
        model = dense.load_model(config["model"])
        vectors = dense.embed(model, [chunk["text"] for chunk in chunks], show_progress=True)
        dense.save_index(dense.build_flat_index(vectors), out_dir / "dense.faiss")

    info = {
        "config": config,
        "num_chunks": len(chunks),
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
    parser.parse_args()
    build_index()


if __name__ == "__main__":
    main()
