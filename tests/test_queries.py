from mathsearch.queries import CATEGORIES, all_problems, next_query_id, query_problems
from mathsearch.split_queries import assign_splits, dev_counts, split_record

PAGES = {"book": 50}


def make_query(qid="q001", category="definition", labels=None, split="dev", text=None):
    labels = labels if labels is not None else [{"book": "book", "start": 3, "end": 4, "grade": 2}]
    return {"id": qid, "query": text or f"toy query {qid}", "category": category, "split": split,
            "notes": "", "labels": labels}


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
    problems = all_problems([make_query("q001", text="toy"), make_query("q002", text="Toy ")], PAGES)
    assert problems == {"q002": ["duplicate query text"]}


def test_next_query_id():
    assert next_query_id([]) == "q001"
    assert next_query_id([make_query("q009"), make_query("q002")]) == "q010"


# ---- split ----

def test_dev_counts_by_hand():
    # 60% of 17 = 10.2 and 60% of 16 = 9.6. Floors give 10+10+10+10+9+9 = 58; the 2 leftover
    # slots go to the largest remainders (.6, .6), so every category gets 10 and the total is 60.
    sizes = {"a": 17, "b": 17, "c": 17, "d": 17, "e": 16, "f": 16}
    assert dev_counts(sizes) == {"a": 10, "b": 10, "c": 10, "d": 10, "e": 10, "f": 10}
    # Uneven sizes: 60% of 30 = 18, of 7 = 4.2, of 3 = 1.8 -> floors 18+4+1 = 23, total 24.
    assert dev_counts({"a": 30, "b": 7, "c": 3}) == {"a": 18, "b": 4, "c": 2}


def hundred_queries():
    sizes = [20, 18, 17, 16, 15, 14]  # deliberately uneven
    queries, n = [], 0
    for category, size in zip(CATEGORIES, sizes):
        for _ in range(size):
            n += 1
            queries.append(make_query(f"q{n:03d}", category, split=""))
    return queries


def test_split_is_exactly_60_40_and_stratified():
    queries, counts = assign_splits(hundred_queries(), seed=0)
    assert sum(q["split"] == "dev" for q in queries) == 60
    for category in CATEGORIES:
        group = [q for q in queries if q["category"] == category]
        dev = sum(q["split"] == "dev" for q in group)
        assert dev == counts[category]
        assert abs(dev - 0.6 * len(group)) < 1  # within one query of the exact share


def test_split_is_reproducible_from_the_seed():
    first, _ = assign_splits(hundred_queries(), seed=0)
    again, _ = assign_splits(hundred_queries(), seed=0)
    other, _ = assign_splits(hundred_queries(), seed=1)
    assert first == again
    assert first != other


def test_split_record_keeps_the_seed():
    queries, counts = assign_splits(hundred_queries(), seed=7)
    record = split_record(queries, counts, seed=7)
    assert record["seed"] == 7
    assert len(record["dev_ids"]) == 60 and len(record["test_ids"]) == 40
    assert record["per_category"]["definition"] == {"dev": 12, "test": 8}
