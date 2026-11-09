"""The benchmark file (benchmark/queries.jsonl): loading, saving and validation.

One JSON object per line:
{"id": "q001", "query": "...", "category": "definition", "split": "dev", "notes": "",
 "labels": [{"book": "levin-discrete-math", "start": 120, "end": 121, "grade": 2, "found_via": "search"}]}

Labels are page spans (PDF page numbers, 1-based, inclusive), never chunk IDs, so they
survive any change to chunking. Grades: 2 = directly answers, 1 = related background,
0 = looked at and judged not relevant (kept so the labeling tool does not ask again).
"""
import json

from mathsearch.paths import QUERIES_PATH

CATEGORIES = ["definition", "theorem", "proof-technique", "paraphrase", "notation", "multi-concept"]
SPLITS = ["dev", "test"]
GRADES = [0, 1, 2]


def load_queries(path=QUERIES_PATH):
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def save_queries(queries, path=QUERIES_PATH):
    with open(path, "w") as f:
        for query in queries:
            f.write(json.dumps(query, ensure_ascii=False) + "\n")


def next_query_id(queries):
    numbers = [int(q["id"][1:]) for q in queries]
    return f"q{max(numbers, default=0) + 1:03d}"


def spans_overlap(a, b):
    return a["book"] == b["book"] and a["start"] <= b["end"] and b["start"] <= a["end"]


def share_answer(a, b):
    """True if two queries have overlapping grade-2 spans, i.e. the same answer passage."""
    answers_a = [label for label in a["labels"] if label["grade"] == 2]
    answers_b = [label for label in b["labels"] if label["grade"] == 2]
    return any(spans_overlap(x, y) for x in answers_a for y in answers_b)


def label_problems(label, pages_by_book):
    """Problems with one label, checked against the page count of each book."""
    if label["book"] not in pages_by_book:
        return [f"unknown book {label['book']!r}"]
    problems = []
    if not 1 <= label["start"] <= label["end"] <= pages_by_book[label["book"]]:
        problems.append(f"bad page range {label['start']}-{label['end']} in {label['book']}")
    if label["grade"] not in GRADES:
        problems.append(f"grade must be one of {GRADES}")
    return problems


def query_problems(query, pages_by_book):
    """Everything that would make a query unusable for evaluation."""
    problems = []
    if not query["query"].strip():
        problems.append("empty query text")
    if query["category"] not in CATEGORIES:
        problems.append(f"unknown category {query['category']!r}")
    if query.get("split") not in SPLITS:
        problems.append("no split assigned (run `make split` once all queries are written)")
    labels = query["labels"]
    for label in labels:
        problems.extend(label_problems(label, pages_by_book))
    if not any(label["grade"] == 2 for label in labels):
        problems.append("needs at least one grade-2 span")
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            if spans_overlap(a, b):
                problems.append(f"overlapping spans {a['book']} {a['start']}-{a['end']} and {b['start']}-{b['end']}")
    return problems


def all_problems(queries, pages_by_book):
    """Return {query_id: [problems]} for every query that has any, plus duplicate checks."""
    problems = {}
    for query in queries:
        found = query_problems(query, pages_by_book)
        if found:
            problems[query["id"]] = found
    seen_ids, seen_texts = set(), set()
    for query in queries:
        text = query["query"].strip().lower()
        if query["id"] in seen_ids:
            problems.setdefault(query["id"], []).append("duplicate id")
        if text in seen_texts:
            problems.setdefault(query["id"], []).append("duplicate query text")
        seen_ids.add(query["id"])
        seen_texts.add(text)
    # A dev query and a test query with the same answer would leak the test set into tuning
    # (`make split` keeps them together; this catches labels edited after the split).
    for i, a in enumerate(queries):
        for b in queries[i + 1:]:
            in_both_splits = {a.get("split"), b.get("split")} == set(SPLITS)
            if in_both_splits and share_answer(a, b):
                problems.setdefault(b["id"], []).append(
                    f"shares a grade-2 span with {a['id']}, which is in the other split")
    return problems
