# Math Textbook Search

Keyword (BM25) and semantic (Sentence-BERT + FAISS) search over four openly licensed math textbooks
(1,882 pages), measured on a hand-labeled benchmark.

> **Status: upgrade in progress.** The original project had no evaluation. The benchmark is now being
> written. Results will appear here only once they are measured, and none are claimed before then.
> Plan: [`docs/UPGRADE_SPEC.md`](docs/UPGRADE_SPEC.md). Audit of the original code: [`docs/audit.md`](docs/audit.md).

## Quick start

Requires Python 3.13 and Tesseract (`brew install tesseract` or `apt install tesseract-ocr`).

```bash
make setup     # create .venv and install pinned dependencies
make index     # extract, chunk, embed and save the index to data/index/ (a few minutes, first run only)
make app       # search UI at http://localhost:8501
make test
```

Command line: `.venv/bin/python -m mathsearch.search "conditions for an Eulerian circuit" --system bm25`

## Benchmark workflow

```bash
make label     # labeling tool: write queries, mark answer pages
make split     # once, after all 100 queries exist: 60 dev / 40 held-out
make baseline  # BM25 + original dense pipeline -> results/baseline.json
make report    # table of every logged run
```

Method and labeling rules: [`benchmark/README.md`](benchmark/README.md). Corpus and licenses: [`benchmark/CORPUS.md`](benchmark/CORPUS.md).

## Layout

```
corpus/       books.json (manifest with SHA-256) and the open-license PDFs
mathsearch/   extraction, chunking, BM25, dense retrieval, index builder, metrics, evaluation harness
benchmark/    queries + labels, labeling tool, method notes
results/      one JSON log per evaluation run
app/          Streamlit search UI
docs/         spec, audit, one note per phase
tests/        pytest
data/         generated (git-ignored): extracted pages and built indexes
```

## Licenses

No license has been chosen for the code yet. The textbooks keep their own licenses (GNU FDL, CC BY-SA, CC BY-NC-SA), listed in
[`benchmark/CORPUS.md`](benchmark/CORPUS.md). Search results show each book's title for attribution.
