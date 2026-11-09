PY := .venv/bin/python
INDEX := data/index/fixed400-minilm/config.json

.PHONY: setup index label split baseline eval report test app

setup:            ## create .venv (Python 3.13) and install pinned dependencies
	python3.13 -m venv .venv
	$(PY) -m pip install -r requirements.txt

$(INDEX):
	$(PY) -m mathsearch.build_index

index: $(INDEX)   ## extract, chunk, embed and save the baseline index (skipped if it exists)

label: $(INDEX)   ## open the benchmark labeling tool
	$(PY) -m streamlit run benchmark/label_app.py

split:            ## assign dev/test splits (once, after all 100 queries are written)
	$(PY) -m mathsearch.split_queries

baseline: $(INDEX) ## BM25 and the original dense pipeline, on dev and held-out
	$(PY) -m mathsearch.evaluate --systems bm25 dense --split both --out results/baseline.json

eval: $(INDEX)    ## dev-set evaluation of both systems, logged to results/runs/
	$(PY) -m mathsearch.evaluate --split dev

report:           ## one table from every logged run
	$(PY) -m mathsearch.report

test:
	$(PY) -m pytest -q

app: $(INDEX)
	$(PY) -m streamlit run app/streamlit_app.py
