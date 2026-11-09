"""End-to-end: tiny generated PDFs -> index -> labeled toy queries -> metrics and a run record.

BM25 only, so the test needs no model download. The queries here are toy fixtures for
testing the code, not part of the benchmark.
"""
import json

import pymupdf
import pytest

from mathsearch.build_index import BASELINE_CONFIG, build_index
from mathsearch.corpus import sha256_of
from mathsearch.evaluate import evaluate

PAGES = [
    "A group is a set together with an associative operation, an identity and inverses.",
    "Lagrange's theorem says the order of a subgroup divides the order of the group.",
    "A graph has an Eulerian circuit exactly when it is connected and every vertex has even degree.",
]


def make_corpus(folder):
    (folder / "pdfs").mkdir(parents=True)
    pdf_path = folder / "pdfs" / "toy.pdf"
    doc = pymupdf.open()
    for text in PAGES:
        doc.new_page().insert_textbox(pymupdf.Rect(72, 72, 540, 300), text, fontsize=11)
    doc.save(pdf_path)
    manifest = folder / "books.json"
    manifest.write_text(json.dumps([{
        "id": "toy", "title": "Toy", "authors": "Test", "file": "toy.pdf", "pages": len(PAGES),
        "license": "none", "source_url": "", "sha256": sha256_of(pdf_path),
    }]))
    return manifest


def write_queries(path):
    queries = [
        {"id": "q001", "query": "eulerian circuit even degree", "category": "theorem", "split": "dev",
         "notes": "", "labels": [{"book": "toy", "start": 3, "end": 3, "grade": 2}]},
        {"id": "q002", "query": "order of a subgroup", "category": "theorem", "split": "dev",
         "notes": "", "labels": [{"book": "toy", "start": 2, "end": 2, "grade": 2},
                                 {"book": "toy", "start": 1, "end": 1, "grade": 1}]},
        {"id": "q003", "query": "identity and inverses", "category": "definition", "split": "test",
         "notes": "", "labels": [{"book": "toy", "start": 1, "end": 1, "grade": 2}]},
    ]
    path.write_text("".join(json.dumps(q) + "\n" for q in queries))


@pytest.fixture
def toy_index(tmp_path):
    manifest = make_corpus(tmp_path / "corpus")
    config = {**BASELINE_CONFIG, "name": "toy"}
    build_index(config, manifest, tmp_path / "index", tmp_path / "pages", with_dense=False)
    queries_path = tmp_path / "queries.jsonl"
    write_queries(queries_path)
    return tmp_path / "index", queries_path


def test_bm25_end_to_end(toy_index):
    index_root, queries_path = toy_index
    (queries_path.parent / "split.json").write_text(json.dumps({"seed": 3}))
    record = evaluate(["toy:bm25"], ["dev"], queries_path, index_root)

    (run,) = record["runs"]
    assert run["split"] == "dev" and run["summary"]["num_queries"] == 2  # held-out query excluded
    assert run["index"] == "toy" and run["system"] == "bm25"
    assert run["summary"]["span_recall_at_10"] == 1.0
    assert run["summary"]["mrr"] == 1.0  # each answer page ranks first
    assert run["summary"]["latency_p95_ms"] >= run["summary"]["latency_p50_ms"] > 0
    assert record["benchmark"]["sha256"] == sha256_of(queries_path)
    assert record["benchmark"]["split_seed"] == 3
    assert record["eval_settings"]["min_overlap"] == 0.5
    # chunk length is logged with the run: each toy page is one chunk
    word_counts = [len(text.split()) for text in PAGES]
    assert run["summary"]["mean_chunk_words"] == pytest.approx(sum(word_counts) / len(word_counts))
    assert run["summary"]["mean_retrieved_chunk_words"] > 0
    assert record["git"]["commit"]
    json.dumps(record)  # the record must be serialisable


def test_bad_labels_stop_the_run(toy_index):
    index_root, queries_path = toy_index
    queries_path.write_text(json.dumps({
        "id": "q001", "query": "x", "category": "theorem", "split": "dev", "notes": "",
        "labels": [{"book": "toy", "start": 9, "end": 9, "grade": 2}],
    }) + "\n")
    with pytest.raises(SystemExit, match="bad page range"):
        evaluate(["toy:bm25"], ["dev"], queries_path, index_root)


def test_unbuilt_index_is_reported(toy_index):
    index_root, queries_path = toy_index
    with pytest.raises(SystemExit, match="not built"):
        evaluate(["missing:bm25"], ["dev"], queries_path, index_root)
