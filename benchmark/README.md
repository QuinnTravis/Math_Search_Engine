# The benchmark: method and labeling rules

100 queries, written and labeled by one person (the project author), used to measure every retrieval
change in this project. This file records the rules so the method can be reproduced and criticised.

## Files

- `queries.jsonl` holds the queries and their labels. It is written by the labeling tool (`make label`).
- `split.json` records the dev/test split and the seed that produced it (written once by `make split`).
- `label_app.py` is the labeling tool.
- `CORPUS.md` lists the books and their licenses.

One line per query:

```json
{"id": "q001", "query": "...", "category": "theorem", "split": "dev", "notes": "",
 "labels": [{"book": "levin-discrete-math", "start": 212, "end": 213, "grade": 2, "found_via": "manual"}]}
```

| Field | Meaning |
| --- | --- |
| `book`, `start`, `end` | A span of **PDF page numbers** (1-based, inclusive). These are not the numbers printed on the page, which differ because of front matter. |
| `grade` | `2` directly answers, `1` related background, `0` looked at and judged not relevant. |
| `found_via` | `manual` means found by my own search or browsing. `pool` means found while reviewing system results. |
| `split` | `dev` (60) or `test` (40). Assigned once by `make split`. |

## Why labels are page spans, not chunk IDs

Chunk IDs change every time the chunking changes. Page spans don't. This means one set of labels
can score fixed-size chunks, structure-aware chunks and anything else.

**Hit rule.** A retrieved chunk hits a labeled span if it comes from the same book and **at least half
of the chunk's words come from pages inside the span**. Every chunk records how many words it took
from each page, so this works for any chunker. The minimum is there so that a long chunk touching a
labeled page with one line doesn't count as finding the answer. Without it, bigger chunks would
always score better. A known limit: labels are page-level, so two chunks from the same labeled page
both count as hits even if only one contains the passage.

## How the metrics are defined

| Metric | Definition |
| --- | --- |
| SpanRecall@k | The fraction of a query's grade-2 spans hit by at least one of the top k chunks. It is **not** hit rate: with two answer spans and one found, SpanRecall is 0.5, not 1. |
| MRR | 1 / rank of the first chunk that hits a grade-2 span, or 0 if none appears in the top 10. |
| nDCG@10 | Linear gain (`grade / log2(rank+1)`). Each labeled span earns its grade at most once, and each chunk earns credit for at most one span. The ideal ranking (one perfect chunk per labeled span, best grade first) is scored by the same function, so the actual and ideal DCG follow identical rules. |
| P50 / P95 latency | The median and 95th percentile of per-query search time, after one untimed warm-up pass. Query embedding is included. |

Every run also logs the mean chunk length of its index and of the chunks it actually retrieved,
because span recall rises with chunk length.

## Query categories

The target is about 16 or 17 queries per category, spread roughly evenly over the four books (about 25 each).

| Category | What it tests |
| --- | --- |
| `definition` | Finding where a term is defined. |
| `theorem` | Finding the statement of a named or described result. |
| `proof-technique` | Finding where a method is explained or demonstrated (as opposed to a single fact). |
| `paraphrase` | The query deliberately avoids the book's own wording. This tests meaning rather than keyword overlap. |
| `notation` | The query depends on symbols or notation. |
| `multi-concept` | The query combines two or more ideas, and the answer needs the passage that connects them. |

## Writing queries

1. **Write the query before looking at the books.** Phrase it the way a student would ask. Looking at the page first makes queries copy the book's wording, which favours keyword search.
2. Every query must have **at least one grade-2 answer** in the corpus. Drop a query if no answer exists. (This means the benchmark does not test "no answer" behaviour, which is a known limitation.)
3. Avoid near-duplicates. Ideally no two queries share an answer passage. When they do (it is sometimes natural, such as a definition query and a paraphrase of it), `make split` keeps them in the same split.
4. Avoid queries whose only answer is a figure or a table, since text extraction cannot see figures.

## Labeling rules

**Grade 2: directly answers.** A reader could stop at this passage. Examples are the definition itself, the theorem statement, or the explanation or worked example of the technique asked about.

**Grade 1: related background.** The passage is clearly about the topic but is not the answer. Examples are a later result that uses the concept, a remark that restates it informally, or an exercise that is substantially about it.

**Not labeled:** passing mentions, the table of contents, the back-of-book index, and lists of symbols.

**Span size:** use the smallest page range that contains the passage, and at most 3 pages. If a proof runs longer, label the pages with the statement and the start of the argument.

**Several books:** label every book that answers the query. The same definition in two books gives two grade-2 spans.

**No overlap:** the spans of one query must not overlap. To change a span, delete it and add it again.

### Search procedure for each query (in this order)

1. **Keyword search** in the tool. Search the words you used, then synonyms and the book's likely terms.
2. **Tables of contents and back-of-book indexes** of every book whose subject fits. The page viewer shows the real page.
3. **Review of system results.** This is optional but recommended, and should be done last. It shows the pages from each system's top 10 that you haven't judged yet. Grade each one, including 0, so missed answers get caught.

## Known biases (and what is done about them)

- **One labeler.** There is no inter-annotator agreement, so grades reflect one person's judgment. This is stated as a limitation in the main README.
- **Keyword-search bias.** Step 1 finds pages that share words with the query, which may favour BM25. Step 2 (indexes and tables of contents) partly offsets this.
- **Pooling bias.** Step 3 only shows pages that the baseline systems found. A later system that finds a relevant page nobody labeled is scored as wrong for it. The `found_via` field measures the problem: if many grade-2 spans are `pool`, the manual search is missing answers and the labels are probably incomplete.

## Splits and the held-out set

- **Write and label all 100 queries first**, then run `make split` **once** (seed 0 by default; `make split SEED=n` to change it). The split needs the labels, and it refuses to run if any query has no grade-2 span.
- **Queries that share an answer stay together.** Two queries share an answer if their grade-2 spans overlap. Sharing is followed through chains: if A shares with B and B shares with C, all three form one group, even if A and C don't overlap. A group is always assigned as a whole. Otherwise, tuning on a dev query would partly tune on its test twin.
- **Stratified by category.** Each category's dev target is the whole-number part of 60% of its size. The few leftover dev slots go to the categories with the largest fractional parts (the "largest remainder" method), so the targets add up to exactly 60% of all queries.
- **Placement.**
  - Groups are shuffled with `random.Random(seed)`, then placed largest first. Big groups are hardest to fit, and single queries placed last can fill whatever room is left.
  - Each group goes to the split where it overshoots its categories' remaining slots the least.
  - On a tie, it goes to dev with probability (free dev slots) / (free slots), like drawing without replacement.
  - With no shared answers, every category target is hit exactly. A group can force a category off target (three queries with one answer cannot be split 60/40). In that case, the placement gets as close as the groups allow, using a greedy rule rather than a provably optimal one.
- `benchmark/split.json` records:
  - the seed and the method
  - each category's dev target and actual counts
  - the shared-answer groups
  - the dev and test ids

  Every evaluation run records the seed. The script refuses to run a second time.
- If labels are edited after the split so that a dev query and a test query come to share an answer, the evaluation harness reports it and refuses to run.
- All tuning (chunk sizes, the fusion constant, which changes to keep) uses `dev` only.
- `test` numbers are reported once at the end of each phase.

## Changing labels later

Fix genuine mistakes, but never change a label because of how one particular system scored on it.
Every run in `results/` records the SHA-256 of `queries.jsonl`. If labels change, every configuration
has to be re-run, and `make report` warns when the runs it compares used different benchmark versions.
