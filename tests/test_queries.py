from mathsearch.queries import CATEGORIES, all_problems, next_query_id, query_problems, share_answer
from mathsearch.split_queries import answer_groups, assign_splits, dev_counts, split_record

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


# ---- shared answers ----

def answer(start, end=None, grade=2, book="book"):
    return {"book": book, "start": start, "end": end or start, "grade": grade}


def test_share_answer_needs_overlapping_grade_2_spans():
    a = make_query("q001", labels=[answer(40, 41)])
    assert share_answer(a, make_query("q002", labels=[answer(41, 42)]))  # overlap on page 41
    assert not share_answer(a, make_query("q003", labels=[answer(42, 43)]))  # adjacent only
    assert not share_answer(a, make_query("q004", labels=[answer(40, 41, grade=1)]))  # background
    assert not share_answer(a, make_query("q005", labels=[answer(40, 41, book="other")]))


def test_answer_groups_are_transitive():
    queries = [
        make_query("q001", labels=[answer(10)]),
        make_query("q002", labels=[answer(10), answer(20)]),  # links q001 and q003
        make_query("q003", labels=[answer(20)]),
        make_query("q004", labels=[answer(30)]),
    ]
    assert [[q["id"] for q in g] for g in answer_groups(queries)] == [["q001", "q002", "q003"], ["q004"]]


def test_cross_split_shared_answer_is_a_problem():
    queries = [make_query("q001", labels=[answer(10)], split="dev"),
               make_query("q002", labels=[answer(10)], split="test")]
    problems = all_problems(queries, PAGES)
    assert problems == {"q002": ["shares a grade-2 span with q001, which is in the other split"]}


# ---- split ----

def test_dev_counts_by_hand():
    # 60% of 17 = 10.2 and 60% of 16 = 9.6. Floors give 10+10+10+10+9+9 = 58; the 2 leftover
    # slots go to the largest remainders (.6, .6), so every category gets 10 and the total is 60.
    sizes = {"a": 17, "b": 17, "c": 17, "d": 17, "e": 16, "f": 16}
    assert dev_counts(sizes) == {"a": 10, "b": 10, "c": 10, "d": 10, "e": 10, "f": 10}
    # Uneven sizes: 60% of 30 = 18, of 7 = 4.2, of 3 = 1.8 -> floors 18+4+1 = 23, total 24.
    assert dev_counts({"a": 30, "b": 7, "c": 3}) == {"a": 18, "b": 4, "c": 2}


def hundred_queries(shared=()):
    """100 queries in uneven categories, each with its own answer page unless listed in
    `shared` as (query number, answer page) pairs."""
    sizes = [20, 18, 17, 16, 15, 14]
    answer_page = dict(shared)
    queries, n = [], 0
    for category, size in zip(CATEGORIES, sizes):
        for _ in range(size):
            n += 1
            page = answer_page.get(n, 100 + n)
            queries.append(make_query(f"q{n:03d}", category, split="", labels=[answer(page)]))
    return queries


def split_of(queries):
    return {q["id"]: q["split"] for q in queries}


def dev_by_category(queries):
    return {c: sum(q["split"] == "dev" for q in queries if q["category"] == c) for c in CATEGORIES}


def test_without_shared_answers_every_target_is_hit_exactly():
    queries, targets, _ = assign_splits(hundred_queries(), seed=0)
    assert sum(q["split"] == "dev" for q in queries) == 60
    assert dev_by_category(queries) == targets


def test_queries_sharing_an_answer_stay_together_and_targets_still_hold():
    # q001+q002 (definition), q021+q022+q040 (theorem / theorem / proof-technique), chained by page 1 and 2
    shared = [(1, 1), (2, 1), (21, 2), (22, 2), (40, 2)]
    for seed in range(20):
        queries, targets, groups = assign_splits(hundred_queries(shared), seed=seed)
        splits = split_of(queries)
        assert splits["q001"] == splits["q002"]
        assert splits["q021"] == splits["q022"] == splits["q040"]
        assert dev_by_category(queries) == targets  # small groups leave room to hit every target
        assert sorted(len(g) for g in groups if len(g) > 1) == [2, 3]


def test_a_group_that_cannot_fit_is_kept_whole_and_lands_as_close_as_possible():
    # One category of 3 queries with the same answer: target is 2 dev, but the group cannot split.
    queries = [make_query(f"q00{i}", "notation", split="", labels=[answer(5)]) for i in (1, 2, 3)]
    queries, targets, groups = assign_splits(queries, seed=0)
    assert targets == {"notation": 2}
    assert {q["split"] for q in queries} == {"dev"}  # 1 over the dev target beats 2 over the test target
    record = split_record(queries, targets, groups, seed=0)
    assert record["per_category"]["notation"] == {"dev": 3, "test": 0, "dev_target": 2}
    assert record["shared_answer_groups"] == [["q001", "q002", "q003"]]


def test_split_is_reproducible_from_the_seed():
    first = split_of(assign_splits(hundred_queries(), seed=0)[0])
    assert split_of(assign_splits(hundred_queries(), seed=0)[0]) == first
    assert split_of(assign_splits(hundred_queries(), seed=1)[0]) != first


def test_split_record_keeps_the_seed():
    queries, targets, groups = assign_splits(hundred_queries(), seed=7)
    record = split_record(queries, targets, groups, seed=7)
    assert record["seed"] == 7
    assert record["dev_total"] == record["dev_target_total"] == 60
    assert len(record["dev_ids"]) == 60 and len(record["test_ids"]) == 40
    assert record["per_category"]["definition"] == {"dev": 12, "test": 8, "dev_target": 12}
    assert record["shared_answer_groups"] == []
