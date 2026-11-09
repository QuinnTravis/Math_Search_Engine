# Results

Every evaluation run is logged here as JSON by `mathsearch.evaluate`:

- `baseline.json` holds the three baseline runs on both splits (`make baseline`): BM25, the original dense pipeline, and the original dense pipeline with chunks that fit the 256-token limit.
- `runs/<timestamp>_<runs>_<splits>.json` holds every other evaluation (`make eval`).

Each file records the git commit (and whether the working tree had uncommitted changes), the machine,
the SHA-256 of `benchmark/queries.jsonl`, the split seed, and the evaluation settings (depth,
minimum overlap, gain). For each run it records the index configuration with chunk-length statistics,
summary metrics (including the mean chunk words of the index and of the retrieved chunks),
per-category metrics, and each query's retrieved pages and scores. Runs are never deleted. A
configuration that did not help stays here as evidence.

`make report` prints one table from all runs and warns if they were scored against different benchmark versions.
