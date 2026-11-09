# Results

Every evaluation run is logged here as JSON by `mathsearch.evaluate`:

- `baseline.json` is BM25 and the original dense pipeline on both splits (`make baseline`).
- `runs/<timestamp>_<systems>_<splits>.json` holds every other run (`make eval`).

Each file records the git commit (and whether the working tree had uncommitted changes), the machine,
the SHA-256 of `benchmark/queries.jsonl`, the full index configuration, summary metrics,
per-category metrics, and each query's retrieved pages and scores. Runs are never deleted. A
configuration that did not help stays here as evidence.

`make report` prints one table from all runs and warns if they were scored against different benchmark versions.
