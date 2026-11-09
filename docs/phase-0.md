# Phase 0: corpus, benchmark tooling and baselines

**Status:** tooling done. The baseline numbers are still waiting on the 100 hand-written queries
(`make label`, then `make split`, then `make baseline`). Phase 1 does not start until
`results/baseline.json` is committed.

## What changed

- **Corpus.** Three books were removed from the public version: one copyrighted, two licensed "no derivatives". They are kept in the git-ignored `private_corpus/`. Two open books were added (Judson, Levin), and Lebl's book was updated to the author's current version. That gives four books and 1,882 pages, each pinned by SHA-256 in `corpus/books.json`. Details are in `benchmark/CORPUS.md`.
- **Layout.** `Project Search/` became a `mathsearch/` package plus `app/`, `benchmark/`, `results/`, `docs/` and `tests/`. There is a `Makefile` for one-command tasks and pinned requirements for Python 3.13.
- **Indexing is separate from serving.** `make index` extracts, chunks and embeds once and saves the result to `data/index/<config>/`. The apps and the evaluation harness load that saved index.
- **Baselines.** BM25 (`mathsearch/bm25.py`, written out in about 40 lines) and the original dense pipeline, run unchanged on the same chunks.
- **Labeling tool** (`benchmark/label_app.py`). It provides keyword search over pages, a viewer showing the real rendered page, span entry, and an optional review of system results with the system names hidden.
- **Evaluation harness** (`mathsearch/evaluate.py`). It computes Recall@5, Recall@10, MRR, nDCG@10 and P50/P95 latency, overall and per category. Each run is logged with its config, git commit, machine and the hash of the benchmark file.
- **Tests** cover the metrics against hand-computed values, BM25 against hand-computed scores, chunking, label validation, the split, and an end-to-end harness run on generated PDFs.
- **Bug fixes the baseline needed.** The FAISS `-1` padding, the macOS OpenMP segfault, and the Streamlit app rebuilding on every click.

## Why, and the alternatives considered

| Decision | Chosen | Alternatives and why not |
| --- | --- | --- |
| Label unit | Page spans | **Chunk IDs** change every time chunking changes. **Character offsets** are more precise, but they break when extraction changes, and Phase 1 changes extraction. |
| Binary relevance (Recall, MRR) | Grade 2 only | Counting grade 1 as well would reward finding background material rather than the answer. nDCG still gives grade 1 partial credit. |
| Duplicate hits in nDCG | Each labeled span earns its grade once | Crediting every overlapping chunk lets a chunker that slices pages finer score higher for no real gain. |
| nDCG gain | Linear (`grade / log2(rank+1)`) | Exponential gain (`2^grade − 1`) weights grade 2 three times grade 1 instead of twice. Linear is easier to explain, and with only two grades the choice matters little. |
| BM25 | Own implementation, Lucene IDF, k1=1.2, b=0.75 (untuned) | The `rank_bm25` library would work. Writing it out makes every number explainable and testable. The parameters are deliberately left untuned so the baseline stays honest. |
| Baseline text processing | Unchanged, ligatures included | Normalising text inside BM25 only would mix two changes into one comparison. Normalisation is its own Phase 1 step, applied to both systems. |
| Corpus distribution | Commit the PDFs | A download script with checksums keeps the repo smaller, but some URLs (Lebl's `realanal.pdf`) are replaced in place by new versions, which would break the checksum and shift labels. |
| Book count | 4 books, 1,882 pages | Adding Beezer (5 books, 2,528 pages) means more places for relevant passages to go unlabeled. |
| Dev/test split | Random, stratified by category, fixed seed, assigned once | Choosing the split by hand risks putting easy queries in the tuning set. |
| Labeling UI | Streamlit (already a dependency) | Label Studio is heavier to run, and a spreadsheet has no page viewer or search. |
| Python | 3.13 | Installed locally, with wheels for every dependency. 3.14 works for most packages, but 3.13 is more widely supported. |

## Caveats to remember for Phase 1

- **Recall rewards bigger chunks.** A chunk that covers more pages overlaps more labels. When comparing chunkers, report average chunk length next to the metrics.
- **MRR is truncated at rank 10**, like everything else here (`EVAL_DEPTH = 10`).
- **Latency is measured on an Apple M4 Pro CPU**, single process, after a warm-up pass. It includes query embedding. It is not a server benchmark.
- **The labels are incomplete by construction** (one labeler, pooled from two systems). The `found_via` counts estimate how incomplete.

## Five interview questions

**1. Why label page spans instead of the chunks your system returns?**
Because the labels must outlive the system. Chunk IDs change every time I change chunking, which is one of the main experiments, so chunk labels would have to be redone for every comparison. Page spans describe where the answer is in the book. A chunk counts as a hit when it overlaps a labeled span, so one set of 100 labeled queries can score fixed-size chunks, structure-aware chunks and anything else. I didn't use character offsets because they depend on the text extraction, which I also plan to change.

**2. If two of your top-10 chunks come from the same answer page, how does nDCG treat that?**
Only the first one gets credit. Each labeled span earns its grade once, and the second chunk counts as gain 0. Without that rule, a chunker that cuts a page into five pieces could fill the top 10 with copies of one answer and look better while giving the user less. The ideal ranking is then simply "every labeled span once, best grade first", so nDCG means the same thing for every chunking strategy.

**3. You wrote and labeled the queries yourself. How do you know the labels aren't biased toward one system?**
I don't fully, so I limit the bias and measure it. I write each query before looking at the books, so it doesn't copy the book's wording, which would favour keyword search. I find answers with keyword search and also with the tables of contents and indexes. Only after that do I review the systems' top results, with the system and rank hidden. Every label records whether I found it myself or in that review. If many answers were only found in the review, my own search was missing things, and later systems may be unfairly penalised for pages nobody labeled. That count goes in the README with the other limitations: one labeler, 100 queries.

**4. How did you measure latency, and what does the number include?**
Each system answers every query once untimed first. That warm-up gets one-time costs like loading model weights out of the measurement. Then each query is timed with `time.perf_counter()` around the full search call. For dense retrieval that includes embedding the query, which is most of the cost; the FAISS lookup itself is small. I report P50 and P95 rather than the mean, because a few slow queries can pull the mean around and P95 is closer to what a user notices. It runs on a laptop CPU in a single process, so it compares systems with each other; it isn't a capacity number for a server.

**5. What was the biggest problem you found in the original pipeline?**
Most of the text was never embedded. Chunks were 400 words, but the embedding model reads at most 256 tokens and silently drops the rest. Measured with the model's own tokenizer, 69% of chunks were over the limit and only 55% of the corpus text made it into an embedding. Dense search was effectively blind to the second half of most chunks, so chunk size is the first thing Phase 1 looks at. I only found it by checking the model's configuration against the chunking code, which is why the audit came before any changes.
