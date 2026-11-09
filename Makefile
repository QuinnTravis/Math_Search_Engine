PY := .venv/bin/python
SEED ?= 0
INDEXES := data/index/fixed400-minilm/config.json data/index/fixedtok256-minilm/config.json

.PHONY: setup index label split baseline eval report test app

setup:            ## create .venv (Python 3.13) and install pinned dependencies
	python3.13 -m venv .venv
	$(PY) -m pip install -r requirements.txt

data/index/%/config.json:
	$(PY) -m mathsearch.build_index --config $*

index: $(INDEXES) ## extract, chunk, embed and save every index configuration (skips built ones)

label: $(INDEXES) ## open the benchmark labeling tool
	$(PY) -m streamlit run benchmark/label_app.py

split:            ## once, after all 100 queries are labeled: stratified 60/40, shared answers kept together (SEED=n)
	$(PY) -m mathsearch.split_queries --seed $(SEED)

baseline: $(INDEXES) ## the three baseline runs, on dev and held-out
	$(PY) -m mathsearch.evaluate --split both --out results/baseline.json

eval: $(INDEXES)  ## the three baseline runs on dev, logged to results/runs/
	$(PY) -m mathsearch.evaluate --split dev

report:           ## one table from every logged run
	$(PY) -m mathsearch.report

test:
	$(PY) -m pytest -q

app: data/index/fixed400-minilm/config.json
	$(PY) -m streamlit run app/streamlit_app.py
