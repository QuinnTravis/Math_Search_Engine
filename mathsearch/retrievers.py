"""Load a built index and search it. Every retriever has the same interface:

    retriever.search(query, top_k) -> list of chunk ids, best first

A "run" names an index and a retriever, e.g. "fixed400-minilm:bm25". Each row of the
results table is one run, so a new chunker and a new retriever are compared the same way.
"""
import json

from mathsearch import dense
from mathsearch.bm25 import BM25
from mathsearch.paths import INDEX_DIR

DEFAULT_INDEX = INDEX_DIR / "fixed400-minilm"
SYSTEMS = ["bm25", "dense"]
BASELINE_RUNS = [
    "fixed400-minilm:bm25",  # keyword baseline
    "fixed400-minilm:dense",  # the original pipeline, unchanged
    "fixedtok256-minilm:dense",  # the original pipeline with chunks that fit the model's 256-token input
]


def load_index_info(index_dir):
    return json.loads((index_dir / "config.json").read_text())


def load_chunks(index_dir):
    with open(index_dir / "chunks.jsonl") as f:
        return [json.loads(line) for line in f]


class BM25Retriever:
    name = "bm25"

    def __init__(self, chunks, k1=1.2, b=0.75):
        self.params = {"k1": k1, "b": b}
        self.bm25 = BM25([chunk["text"] for chunk in chunks], k1=k1, b=b)

    def search(self, query, top_k=10):
        return [doc_id for doc_id, _ in self.bm25.search(query, top_k)]


class DenseRetriever:
    name = "dense"

    def __init__(self, index_dir, model_name):
        self.params = {"model": model_name, "faiss_index": "IndexFlatIP"}
        self.model = dense.load_model(model_name)
        self.index = dense.load_index(index_dir / "dense.faiss")

    def search(self, query, top_k=10):
        return [row_id for row_id, _ in dense.search(self.index, self.model, query, top_k)]


def make_retriever(name, index_dir, chunks):
    if name == "bm25":
        return BM25Retriever(chunks)
    if name == "dense":
        return DenseRetriever(index_dir, load_index_info(index_dir)["config"]["model"])
    raise ValueError(f"unknown system {name!r}; choose from {SYSTEMS}")


def parse_run(spec):
    """'fixed400-minilm:bm25' -> ('fixed400-minilm', 'bm25')"""
    index_name, _, system = spec.partition(":")
    if system not in SYSTEMS:
        raise SystemExit(f"Bad run {spec!r}: expected <index>:<system> with system in {SYSTEMS}")
    return index_name, system


def index_is_built(index_name, index_root=INDEX_DIR):
    return (index_root / index_name / "config.json").exists()


def load_run(spec, index_root=INDEX_DIR):
    """Return (index_info, chunks, retriever) for a run such as 'fixed400-minilm:dense'."""
    index_name, system = parse_run(spec)
    if not index_is_built(index_name, index_root):
        raise SystemExit(f"Index {index_name!r} is not built. Run: make index")
    index_dir = index_root / index_name
    chunks = load_chunks(index_dir)
    return load_index_info(index_dir), chunks, make_retriever(system, index_dir, chunks)
