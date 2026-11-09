"""Load a built index and search it. Every retriever has the same interface:

    retriever.search(query, top_k) -> list of chunk ids, best first
"""
import json

from mathsearch import dense
from mathsearch.bm25 import BM25
from mathsearch.paths import INDEX_DIR

DEFAULT_INDEX = INDEX_DIR / "fixed400-minilm"
SYSTEMS = ["bm25", "dense"]


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
