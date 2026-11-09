"""Assign every query to the dev (60%) or held-out test (40%) split. Run once, after all queries are written.

Usage:  python -m mathsearch.split_queries

Method: sort queries by category, shuffle within each category with a fixed seed, then
walk the list assigning dev, dev, dev, test, test, dev, dev, dev, test, test, ...
That gives exactly 60/40 for 100 queries and keeps each category close to 60/40 too.
The split is random rather than hand-picked so I cannot (even unconsciously) put the
easy queries in the set I tune on.
"""
import argparse
import random

from mathsearch.paths import QUERIES_PATH
from mathsearch.queries import CATEGORIES, load_queries, save_queries

PATTERN = ["dev", "dev", "dev", "test", "test"]
SEED = 0


def assign_splits(queries, seed=SEED):
    """Return a copy of `queries` with "split" set on every query."""
    rng = random.Random(seed)
    ordered = []
    for category in CATEGORIES:
        group = sorted((q for q in queries if q["category"] == category), key=lambda q: q["id"])
        rng.shuffle(group)
        ordered.extend(group)
    split_by_id = {q["id"]: PATTERN[i % len(PATTERN)] for i, q in enumerate(ordered)}
    return [{**q, "split": split_by_id[q["id"]]} for q in queries]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args()
    queries = load_queries(QUERIES_PATH)
    if any(q.get("split") for q in queries):
        raise SystemExit("Splits are already assigned. Changing them now would leak held-out queries into tuning.")
    unknown = [q["id"] for q in queries if q["category"] not in CATEGORIES]
    if unknown:
        raise SystemExit(f"Queries with an unknown category: {unknown}")
    queries = assign_splits(queries)
    save_queries(queries, QUERIES_PATH)
    dev = sum(q["split"] == "dev" for q in queries)
    print(f"Assigned {dev} dev and {len(queries) - dev} test queries.")


if __name__ == "__main__":
    main()
