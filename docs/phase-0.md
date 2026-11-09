# Phase 0: corpus, benchmark tooling and baselines

**Status:** tooling done. The baseline numbers are still waiting on the 100 hand-written queries
(`make label` for all 100, then `make split`, then `make baseline`). Phase 1 does not start until
`results/baseline.json` is committed.

## What changed

- **Corpus.** Three books were removed from the public version: one copyrighted, two licensed "no derivatives". They are kept in the git-ignored `private_corpus/`. Two open books were added (Judson, Levin), and Lebl's book was updated to the author's current version. That gives four books and 1,882 pages, each pinned by SHA-256 in `corpus/books.json`. Details are in `benchmark/CORPUS.md`.
- **Layout.** `Project Search/` became a `mathsearch/` package plus `app/`, `benchmark/`, `results/`, `docs/` and `tests/`. There is a `Makefile` for one-command tasks and pinned requirements for Python 3.13.
- **Indexing is separate from serving.** `make index` builds every index configuration once and saves it to `data/index/<config>/`, together with chunk-length statistics. The apps and the harness load the saved indexes.
- **Three baseline runs.** A run is an index plus a retrieval system, written `index:system`.
  - `fixed400-minilm:bm25`: keyword search (`mathsearch/bm25.py`, written out in about 40 lines).
  - `fixed400-minilm:dense`: the original pipeline, unchanged.
  - `fixedtok256-minilm:dense`: the original pipeline, except each chunk holds only as many whole words as fit in the model's 256-token input. Nothing is truncated. Everything else (cleaning, per-page cutting, model, index) is identical, so this run isolates the cost of truncation.
- **Labeling tool** (`benchmark/label_app.py`). It provides keyword search over pages, a viewer showing the real rendered page, span entry, and a blind review of the pooled top-10 results from all three baseline runs.
- **Evaluation harness** (`mathsearch/evaluate.py`). It computes SpanRecall@5/10, MRR, nDCG@10 and P50/P95 latency, overall and per category. Each record holds the git commit, machine, benchmark hash, split seed, evaluation settings, and for each run the index configuration with its chunk-length statistics.
- **Stratified split** (`make split`). Queries that share a grade-2 span are kept in the same split, and the seed is recorded. The harness refuses to run if later label edits put a shared answer on both sides. See `benchmark/README.md`.
- **Tests** check the metrics against hand-computed values (including the overlap rule and the ideal ranking), BM25 against hand-computed scores, both chunkers, label validation, split quotas and reproducibility, and an end-to-end harness run on generated PDFs.
- **Bug fixes the baseline needed.** The FAISS `-1` padding, the macOS OpenMP segfault, and the Streamlit app rebuilding on every click.

## Why, and the alternatives considered

| Decision | Chosen | Alternatives and why not |
| --- | --- | --- |
| Label unit | Page spans | **Chunk IDs** change every time chunking changes. **Character offsets** are more precise, but they break when extraction changes, and Phase 1 changes extraction. |
| Hit rule | Same book, and at least 50% of the chunk's words on labeled pages | **Any shared page** lets a 10-page chunk count as finding a 1-page answer, so recall would rise just by making chunks longer. **Measuring by pages instead of words** would treat a chunk with one line on page 10 and 300 words on page 11 as "half on page 10". **Measuring the share of the span that the chunk covers** would penalise small, precise chunks instead. |
| Recall definition | SpanRecall: the fraction of grade-2 spans found | **Hit rate** (did any answer appear?) can't tell a system that finds one of three answer passages from one that finds all three. The name says which one it is. |
| Binary relevance (SpanRecall, MRR) | Grade 2 only | Counting grade 1 as well would reward finding background material rather than the answer. nDCG still gives grade 1 partial credit. |
| Duplicate hits in nDCG | Each labeled span earns its grade once; each chunk earns credit for at most one span | Crediting every overlapping chunk lets a chunker that slices pages finer score higher for no real gain. |
| Ideal DCG | A perfect ranking (one exact chunk per span, best grade first) scored by the same `gains()` function | Before, the ideal was computed as "the span grades, sorted". That gave the same numbers, but through separate code that could drift from the scoring rule. Sharing one function guarantees that nDCG = 1 means exactly "every labeled span found, in the best order". |
| nDCG gain | Linear (`grade / log2(rank+1)`) | Exponential gain (`2^grade − 1`) weights grade 2 three times grade 1 instead of twice. Linear is easier to explain, and with only two grades the choice matters little. |
| Token-capped baseline | Greedily fill each page window with whole words up to 254 WordPiece tokens | **Shrinking to a fixed word count** (for example 180 words) would still truncate math-heavy chunks, which tokenize into many more pieces per word. **Overlapping windows** would change two things at once. The builder checks after embedding that 0% of these chunks exceed the limit. |
| BM25 | Own implementation, Lucene IDF, k1=1.2, b=0.75 (untuned) | The `rank_bm25` library would work. Writing it out makes every number explainable and testable. The parameters are deliberately left untuned so the baseline stays honest. |
| Baseline text processing | Unchanged, ligatures included | Normalising text inside BM25 only would mix two changes into one comparison. Normalisation is its own Phase 1 step, applied to all systems. |
| Dev/test split | Per-category targets by largest remainder. Queries with overlapping grade-2 spans are grouped (following chains) and placed as a unit, largest groups first, each where it overshoots least, with seeded tie-breaks. Recorded in `split.json`. | The first version ran one dev/test pattern over all queries sorted by category. That was only roughly stratified, because the pattern crosses category boundaries. **Rounding each category separately** can make the total 59 or 61 instead of 60. A **hand-picked** split risks putting easy queries in the tuning set. **Ignoring shared answers** lets a test query's answer be tuned on through its dev twin. **Grouping only identical spans** would miss queries whose answer spans differ by a page. **An exact solver** (integer programming) would guarantee the closest fit to the targets, but greedy hits them exactly whenever groups are small, which is the expected case, and it is easy to explain. |
| Corpus distribution | Commit the PDFs | A download script with checksums keeps the repo smaller, but some URLs (Lebl's `realanal.pdf`) are replaced in place by new versions, which would break the checksum and shift labels. |
| Book count | 4 books, 1,882 pages | Adding Beezer (5 books, 2,528 pages) means more places for relevant passages to go unlabeled. |
| Labeling UI | Streamlit (already a dependency) | Label Studio is heavier to run, and a spreadsheet has no page viewer or search. |
| Python | 3.13 | Installed locally, with wheels for every dependency. 3.14 works for most packages, but 3.13 is more widely supported. |

## Caveats to remember for Phase 1

- **Labels are page-level.** Two chunks from the same labeled page both count as hits, even if only one contains the passage. The hit rule limits how much large chunks benefit; it can't make labels finer than a page.
- **The token-capped baseline changes two things, not one.** Removing truncation also roughly halves the chunks (mean 142 words versus 261; 4,865 chunks versus 2,641). The difference between the two dense runs is the effect of "no truncation *and* shorter chunks". The Phase 1 plan (step 2 in `docs/UPGRADE_SPEC.md`) separates them with a chunk-size sweep at 128, 192 and 254 tokens, none of which is truncated. Each index now logs `mean_embedded_tokens`, the tokens each vector actually sees. Measured: 207.6 for `fixed400-minilm` and 207.3 for `fixedtok256-minilm`. Per vector, both embed almost the same amount of text. What differs is that the original never embeds the 45% of text past the limit, while the capped index embeds all of it across about 1.8× as many vectors.
- **Always read chunk length next to the metrics.** Every run logs the index's mean chunk words and the mean words of the chunks it retrieved. A chunker that wins only by producing longer chunks is visible there.
- **MRR is truncated at rank 10**, like everything else here (`EVAL_DEPTH = 10`).
- **Latency is measured on an Apple M4 Pro CPU**, single process, after a warm-up pass. It includes query embedding. It is not a server benchmark.
- **The labels are incomplete by construction** (one labeler, pooled from three runs). The `found_via` counts estimate how incomplete.

## Five interview questions

**1. Why label page spans instead of the chunks your system returns?**
Because the labels must outlive the system. Chunk IDs change every time I change chunking, which is one of the main experiments, so chunk labels would have to be redone for every comparison. Page spans describe where the answer is in the book. A chunk counts as a hit when at least half of its words come from a labeled span's pages. I didn't use character offsets because they depend on the text extraction, which I also plan to change.

**2. Couldn't a system game your metrics by returning bigger chunks, or several chunks from the same answer?**
I closed both routes. For size: a chunk only hits a span if at least half of its words come from the span's pages, so a long chunk that brushes an answer page doesn't count, and every run logs average chunk length so a length effect is visible. For repetition: in nDCG each labeled span earns its grade once, so five chunks from one answer page earn the gain once. The ideal ranking is scored by the same function, so the denominator follows the same rule as the numerator.

**3. You wrote and labeled the queries yourself. How do you know the labels aren't biased toward one system?**
I don't fully, so I limit the bias and measure it. I write each query before looking at the books, so it doesn't copy the book's wording, which would favour keyword search. I find answers with keyword search and also with the tables of contents and indexes. Only after that do I review the pooled top results of all three baseline runs, with system and rank hidden. Every label records whether I found it myself or in that review. If many answers were only found in the review, my own search was missing things, and that goes in the README next to the other limitations: one labeler, 100 queries.

**4. How did you split 100 queries into dev and test, and why does the method matter?**
60/40, stratified by category, with two constraints. First, queries whose answer spans overlap are grouped, following chains, and each group goes entirely to one side. Otherwise tuning on a dev query would quietly tune on its held-out twin, which is test leakage. Second, each category's dev target is the whole-number part of 60% of its size, with leftover slots going to the largest fractional parts, so the targets total exactly 60. Groups are placed largest first, each where it overshoots least, and single queries fill the remaining room, so targets are hit exactly unless a big group makes that impossible. The seed, targets, actual counts and groups are saved to `split.json`, and the harness refuses to run if a later label edit puts a shared answer on both sides. Stratifying matters because categories differ in difficulty: if notation queries piled up in the test set, held-out scores would drop for reasons unrelated to the system.

**5. What was the biggest problem you found in the original pipeline, and how did you measure it?**
Most of the text was never embedded. Chunks were 400 words, but the embedding model reads at most 256 tokens and silently drops the rest. Measured with the model's own tokenizer, 69% of chunks were over the limit and only 55% of the corpus text made it into an embedding. Instead of just asserting that this hurts, I added a third baseline that differs only in chunk size: each chunk fits within 256 tokens, with the same cleaning, the same model and the same index. The difference between those two runs is the measured cost of truncation, separate from any later chunking improvement.
