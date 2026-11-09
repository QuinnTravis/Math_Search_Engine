from mathsearch.queries import all_problems, next_query_id, query_problems
from mathsearch.split_queries import assign_splits

PAGES = {"book": 50}


def make_query(qid="q001", category="definition", labels=None, split="dev", text="toy query"):
    labels = labels if labels is not None else [{"book": "book", "start": 3, "end": 4, "grade": 2}]
    return {"id": qid, "query": text, "category": category, "split": split, "notes": "", "labels": labels}


def test_valid_query_has_no_problems():
    assert query_problems(make_query(), PAGES) == []


def test_problems_are_reported():
    assert "needs at least one grade-2 span" in query_problems(
        make_query(labels=[{"book": "book", "start": 1, "end": 1, "grade": 1}]), PAGES)
    assert any("bad page range" in p for p in query_problems(
        make_query(labels=[{"book": "book", "start": 49, "end": 51, "grade": 2}]), PAGES))
    assert any("overlapping" in p for p in query_problems(
        make_query(labels=[{"book": "book", "start": 1, "end": 3, "grade": 2},
                           {"book": "book", "start": 3, "end": 5, "grade": 1}]), PAGES))
    assert any("no split" in p for p in query_problems(make_query(split=""), PAGES))


def test_duplicates_are_reported():
    problems = all_problems([make_query("q001"), make_query("q002", text="Toy query ")], PAGES)
    assert problems == {"q002": ["duplicate query text"]}


def test_next_query_id():
    assert next_query_id([]) == "q001"
    assert next_query_id([make_query("q009"), make_query("q002")]) == "q010"


def test_split_is_60_40_stratified_and_reproducible():
    categories = ["definition", "theorem", "proof-technique", "paraphrase", "notation", "multi-concept"]
    queries = [make_query(f"q{i:03d}", categories[i % 6], split="") for i in range(1, 101)]
    first = assign_splits(queries)
    assert sum(q["split"] == "dev" for q in first) == 60
    for category in categories:
        group = [q for q in first if q["category"] == category]
        dev_share = sum(q["split"] == "dev" for q in group) / len(group)
        assert 0.5 <= dev_share <= 0.7
    assert assign_splits(queries) == first  # same seed, same split
