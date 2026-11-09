# Math Search Engine: Upgrade Spec

Nov 9, 2026 · @R

## Context and goal

The goal is to turn the Math PDF Semantic Search Engine from a Streamlit demo into a measured, tested, deployable retrieval system, where every claim on the resume is backed by a number from a benchmark I built.

**What exists today** (repo: [QuinnTravis/Math\_Search\_Engine](https://github.com/QuinnTravis/Math_Search_Engine), last touched Dec 24, 2025): a semantic search engine over about 2,000 pages of math textbooks. PyMuPDF extracts text, Tesseract OCR is the fallback, text is chunked, embedded with Sentence-BERT, indexed in FAISS, and served through a Streamlit UI. There is no evaluation, no tests, no CI, no container and no deployment.

**Why this matters:** I am applying to software engineering internships (Pinterest first). A search project with no metrics reads as a demo. The posting asks for code that is "well-documented, tested, and operable," and this project should show all three.

**Done means:**

1. A 100-query hand-labeled benchmark with baseline and improved numbers (Recall@5, Recall@10, MRR, nDCG@10, P50/P95 latency).
2. Retrieval that measurably beats the baseline, with an error analysis of what still fails.
3. A FastAPI service with tests, CI, Docker and a deployed demo.
4. A README with an architecture diagram, a results table and a "what failed" section.

## Ground rules for Claude

I must be able to explain and defend every part of this project in an interview, so how you work matters as much as what you build.

1. **Audit first.** Read the whole repo and report what is there (structure, extraction, chunking, embedding model, FAISS index type, UI) and what is broken or missing, before changing anything. Work on a branch, one pull request per phase.
2. **Teach as you go.** After each phase, write a short note in `docs/` covering what changed, why, which alternatives you considered, and five questions an interviewer could ask about it, with answers. Keep functions small and plain. No clever code I could not rewrite from memory.
3. **I write the benchmark.** You build the labeling tool and the evaluation harness. I write and label the 100 queries myself, since the resume will say "hand-labeled." You may suggest query categories and a labeling format, but do not generate queries or relevance judgments for me to approve.
4. **No claim without a number.** Log every experiment (config, git commit, metrics) to a file in `results/`. If hybrid search or the reranker does not help, say so and keep the finding.
5. **Stay in scope.** Do not build a React rewrite, document upload, async indexing, authentication or Postgres status tracking. Add something only if a benchmark result or a failure case justifies it, and ask me first.
6. **Open-license corpus only.** The demo and benchmark must be shareable without copyright problems.
7. **Ask, don't assume,** when a choice changes the scope, the corpus or the evaluation method.

## Phase 0: corpus, benchmark and baselines (week 1)

Nothing in Phase 1 starts until baseline numbers are committed.

**Corpus.** Switch the public version to openly licensed textbooks, and keep any copyrighted books in a private, untracked folder. Candidates to check (verify each book's current license, and that it allows redistributing excerpts and derived indexes): Judson's *Abstract Algebra: Theory and Applications*, Beezer's *A First Course in Linear Algebra*, Levin's *Discrete Mathematics: An Open Introduction*, Lebl's *Basic Analysis*. Aim for about 2,000 pages across 4 to 6 books, as now.

**License check first.** For every book in the current index, find its copyright or license page and record the license in `benchmark/CORPUS.md`. Any book without a clear open license stays in the private folder and is replaced in the public version.

**Benchmark design.**

- 100 queries, covering: definition lookup, theorem statement, proof technique, paraphrased concept (different wording from the text), notation-heavy, and multi-concept questions. Example: "conditions under which a graph has an Eulerian circuit."
- Split 60 development / 40 held-out. Tune only on the development set, and report held-out numbers once at the end of each phase.
- Label by source location (book, page range), not by chunk ID, so labels survive any re-chunking. A retrieved chunk is a hit if it overlaps a labeled span.
- Graded relevance for nDCG: 2 = directly answers the query, 1 = related background.
- Record the labeling rules in `benchmark/README.md` so the method can be reproduced and criticized.

**Baselines to run** on the same machine, with a warm-up pass before timing:

1. BM25 keyword retrieval.
2. The current Sentence-BERT + FAISS pipeline, unchanged.

**Metrics:** Recall@5, Recall@10, MRR, nDCG@10, and P50/P95 query latency.

**Acceptance:** `results/baseline.json` and a results table are committed, the harness runs with one command, and the labeling rules are written down.

## Phase 1: retrieval improvements (week 2)

Add one change at a time and re-run the development benchmark after each, so every row of the final results table is an ablation. Keep a change only if it helps, and record the ones that do not.

1. **Audit extraction.** Check how equations, symbols and theorem headings come out of PyMuPDF and the Tesseract fallback. Write down the failure patterns with examples before fixing anything. Many openly licensed books also publish their source (LaTeX or PreTeXt); if one does, compare extracting from source against extracting from the PDF.
2. **Chunk-length sweep, with truncation held at zero.** The Phase 0 token-capped baseline removed truncation but also roughly halved chunk length, so its gain mixes the two effects. Re-chunk with the token-capped chunker at **128, 192 and 254** content tokens. Keep everything else fixed: the same cleaning, the same per-page cutting, the same dense model (`all-MiniLM-L6-v2`) and the same flat index. The 254 point is the existing `fixedtok256-minilm` index.
   - No chunk is truncated at any of the three sizes, so differences between them are the effect of **chunk length alone**.
   - The effect of **truncation** is the gap between `fixed400-minilm` and the 254 point. Each vector sees at most 254 content tokens in both, but the original silently drops the rest of each chunk. Compare `mean_embedded_tokens` in each index's `config.json` to confirm the two embed similar amounts per vector before attributing the gap to truncation.
   - Report chunk count, mean words and mean embedded tokens next to each row, because SpanRecall depends on chunk length.
   - Dev set only. The chosen size becomes the default chunk budget for structure-aware chunking (step 3), so that comparison is not confounded by length either.
3. **Structure-aware chunking.** Split at definition, theorem, lemma, proof and example boundaries, and attach the section title to each chunk as context. Compare against the current fixed-size chunks. I expect this to matter as much as any model change.
4. **Hybrid retrieval.** Combine BM25 and dense scores with reciprocal rank fusion. Tune the fusion constant on the development set only.
5. **Cross-encoder reranking.** Rerank the top 50 candidates with a pretrained cross-encoder. Do not fine-tune unless the benchmark shows a clear reason. Report the added latency.
6. **Notation handling.** Normalize Unicode math symbols and test notation-heavy queries separately. If dense retrieval still fails on them, document that rather than hiding it.
7. **Index comparison.** Compare flat FAISS, IVF and HNSW on recall versus latency. At this corpus size, exact search may already be fastest; if so, the finding is that approximate indexes add nothing here.
8. **Optional, time-boxed:** one alternative embedding model, compared on the same benchmark.
9. **Error analysis.** Take the 20 worst development queries and classify each failure (extraction, chunking, vocabulary mismatch, notation, ambiguous label). Summarize the counts and give two or three examples.

**Acceptance:** the best configuration beats both baselines on the held-out set, reported with a paired bootstrap confidence interval over queries (100 queries is small, so state the uncertainty), and the error analysis is written up in `docs/`.

## Phase 2: engineering quality (week 3)

The point of this phase is to show the code is tested and operable, not to add features.

- **FastAPI service.** A `/search` endpoint (query, number of results, retrieval mode) and a `/health` endpoint. Validate input with Pydantic and return clear errors. Log structured JSON with a request ID and per-stage latency.
- **Separate indexing from serving.** Build the index with one command, version the index artifacts, and load them at service startup.
- **Failure handling.** Corrupted PDFs and OCR failures must be skipped, logged and counted in an indexing report, not crash the run. Cover each case with a test using a small fixture file.
- **Tests (pytest).** Unit tests for chunking, rank fusion and the metric functions, with metric values checked against hand-computed examples on a toy set. One integration test runs the API against a tiny fixture corpus.
- **CI (GitHub Actions).** Lint, run tests, and build the Docker image on every push. Use the tiny fixture and cached models so the run stays fast.
- **Docker.** A single image, non-root user, health check, and `docker compose up` working from a clean clone.
- **UI.** Keep Streamlit, but have it call the API. Show the source book, page and surrounding text for each result.
- **Caching.** Add a simple query cache only if the latency numbers justify it.
- **Deployment.** Deploy a demo with the open-license corpus only. Ask me which free-tier host to use, and note cold-start behavior in the README.

**Acceptance:** CI is green, the API runs from a clean clone with one command, and the demo URL works. Report test coverage, but do not chase a percentage.

## Deliverables and README

The project is finished when every box below is ticked and the README tells an honest story.

- [ ] `benchmark/` holds the 100 queries, labels, split and labeling rules
- [ ] `results/` holds one logged run per configuration (config, git commit, metrics)
- [ ] `docs/` holds one note per phase, plus the error analysis
- [ ] Tests and CI pass, and the Docker image builds
- [ ] The demo is deployed and linked from the README
- [ ] The GitHub repo has a description, topics and a pinned slot on my profile

**README must contain:**

1. A two-sentence description and the demo link.
2. An architecture diagram (extraction, chunking, indexing, retrieval, reranking, API).
3. The results table below, filled from `results/`, with held-out numbers and the confidence interval.
4. A "what failed" section covering ideas that did not help and queries that still fail.
5. Limitations stated plainly: small corpus, 100 queries, one labeler.
6. One-command instructions to run the service and to reproduce the benchmark.

**Results table to fill (one row per ablation step, held-out set):**

| Configuration | Recall@5 | Recall@10 | MRR | nDCG@10 | P50 latency (ms) | P95 latency (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| BM25 |  |  |  |  |  |  |
| Sentence-BERT + FAISS (original) |  |  |  |  |  |  |
| + structure-aware chunking |  |  |  |  |  |  |
| + hybrid (BM25 + dense, rank fusion) |  |  |  |  |  |  |
| + cross-encoder reranker |  |  |  |  |  |  |

## Resume bullet (write last)

Write the bullet only after the held-out numbers exist. Fill each bracket with a real value, and delete any claim the data does not support. If hybrid search or the reranker did not help, the bullet should say what the benchmark taught me instead.

**Math Search Engine** | Python, FastAPI, FAISS, Sentence-BERT, Docker, GitHub Actions | \[GitHub link\]

- Built a hybrid retrieval system (BM25 + dense with rank fusion, plus a cross-encoder reranker) over about 2,000 pages of open-license math textbooks, raising nDCG@10 from \[X\] to \[Y\] against a BM25 baseline on a \[40\]-query held-out set (95% CI \[a, b\]).
- Evaluated on a 100-query hand-labeled benchmark (\[Recall@10\], MRR, P95 latency \[Z\] ms); found that \[one specific finding, for example that structure-aware chunking accounted for most of the gain\].
- Shipped as a FastAPI service with tests, CI and Docker, with a deployed demo.

Do not write "state-of-the-art," do not round numbers up, and do not claim anything the README cannot back.
