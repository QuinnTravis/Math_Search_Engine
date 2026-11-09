# The benchmark: method and labeling rules

100 queries, written and labeled by one person (the project author), used to measure every retrieval
change in this project. This file records the rules so the method can be reproduced and criticised.

## Files

- `queries.jsonl` holds the queries and their labels. It is written by the labeling tool (`make label`).
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

Chunk IDs change every time the chunking changes. Page spans don't. A retrieved chunk counts as a hit
if it comes from the same book and its pages overlap a labeled span. This means one set of labels
can score fixed-size chunks, structure-aware chunks and anything else.

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
3. Avoid near-duplicates. Two queries should not have the same answer passage.
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

- Write all 100 queries first, then run `make split` **once**. It sorts queries by category, shuffles them within each category (fixed seed 0), and assigns dev, dev, dev, test, test in a repeating pattern. That gives exactly 60/40, stratified by category. The script refuses to run a second time.
- All tuning (chunk sizes, the fusion constant, which changes to keep) uses `dev` only.
- `test` numbers are reported once at the end of each phase.

## Changing labels later

Fix genuine mistakes, but never change a label because of how one particular system scored on it.
Every run in `results/` records the SHA-256 of `queries.jsonl`. If labels change, every configuration
has to be re-run, and `make report` warns when the runs it compares used different benchmark versions.
