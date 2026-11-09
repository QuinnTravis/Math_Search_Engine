"""Assign every query to dev (60%) or held-out test (40%), stratified by category.
Run once, after all queries are written.

Usage:  python -m mathsearch.split_queries [--seed 0]      (or: make split SEED=0)

Method:
1. Decide how many dev queries each category gets. Each category first gets the whole-number
   part of 60% of its size; the few leftover dev slots go to the categories with the largest
   fractional parts (the "largest remainder" method). This makes the total exactly 60% of the
   queries, and each category within one query of its exact 60% share.
2. Within each category (sorted by id, then shuffled with the seed), the first queries are dev
   and the rest are test.

The seed, the method and the resulting ids are written to benchmark/split.json, and every
evaluation run records the seed. The split is random rather than hand-picked so I cannot
(even unconsciously) put the easy queries in the set I tune on.
"""
import argparse
import json
import random
from datetime import datetime, timezone

from mathsearch.paths import QUERIES_PATH
from mathsearch.queries import CATEGORIES, load_queries, save_queries

DEV_PERCENT = 60
DEFAULT_SEED = 0


def dev_counts(group_sizes, dev_percent=DEV_PERCENT):
    """{category: number of dev queries}, using whole-number arithmetic only."""
    total = sum(group_sizes.values())
    total_dev = (total * dev_percent + 50) // 100  # 60% of the total, rounded
    counts = {c: n * dev_percent // 100 for c, n in group_sizes.items()}
    remainders = {c: n * dev_percent % 100 for c, n in group_sizes.items()}
    leftover = total_dev - sum(counts.values())
    # Largest remainder first; ties go to the category listed first in CATEGORIES.
    for category in sorted(group_sizes, key=lambda c: -remainders[c])[:leftover]:
        counts[category] += 1
    return counts


def assign_splits(queries, seed=DEFAULT_SEED):
    """Return (queries with "split" set, {category: dev count})."""
    rng = random.Random(seed)
    groups = {}
    for category in CATEGORIES:
        group = sorted((q for q in queries if q["category"] == category), key=lambda q: q["id"])
        if group:
            groups[category] = group
    counts = dev_counts({c: len(group) for c, group in groups.items()})

    split_by_id = {}
    for category, group in groups.items():
        rng.shuffle(group)
        for position, query in enumerate(group):
            split_by_id[query["id"]] = "dev" if position < counts[category] else "test"
    return [{**q, "split": split_by_id[q["id"]]} for q in queries], counts


def split_record(queries, counts, seed):
    """What gets written to benchmark/split.json."""
    sizes = {c: sum(q["category"] == c for q in queries) for c in counts}
    return {
        "seed": seed,
        "dev_percent": DEV_PERCENT,
        "method": "stratified by category; largest-remainder dev quotas; random.Random(seed) shuffle per category",
        "assigned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "per_category": {c: {"dev": counts[c], "test": sizes[c] - counts[c]} for c in counts},
        "dev_ids": sorted(q["id"] for q in queries if q["split"] == "dev"),
        "test_ids": sorted(q["id"] for q in queries if q["split"] == "test"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    queries = load_queries(QUERIES_PATH)
    split_file = QUERIES_PATH.parent / "split.json"
    if split_file.exists() or any(q.get("split") for q in queries):
        raise SystemExit("Splits are already assigned. Changing them now would leak held-out queries into tuning.")
    unknown = [q["id"] for q in queries if q["category"] not in CATEGORIES]
    if unknown:
        raise SystemExit(f"Queries with an unknown category: {unknown}")

    queries, counts = assign_splits(queries, args.seed)
    record = split_record(queries, counts, args.seed)
    save_queries(queries, QUERIES_PATH)
    split_file.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Seed {args.seed}: {len(record['dev_ids'])} dev, {len(record['test_ids'])} test")
    for category, split_counts in record["per_category"].items():
        print(f"  {category}: {split_counts['dev']} dev / {split_counts['test']} test")
    print(f"Recorded in {split_file}")


if __name__ == "__main__":
    main()
