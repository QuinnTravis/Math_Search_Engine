"""Assign every query to dev (60%) or held-out test (40%), stratified by category, keeping
queries that share an answer in the same split. Run once, after all queries are labeled.

Usage:  python -m mathsearch.split_queries [--seed 0]      (or: make split SEED=0)

Why groups: if two queries have overlapping grade-2 spans (the same answer passage), and one
is in dev and the other in test, then tuning on the dev query is partly tuning on the test
query. So queries connected by shared grade-2 spans (directly or through a chain) form a
group, and a group is always assigned as a whole.

Method:
1. Targets. Each category's dev target is the whole-number part of 60% of its size; the few
   leftover dev slots go to the categories with the largest fractional parts (the "largest
   remainder" method). The targets add up to exactly 60% of all queries.
2. Order. Groups are shuffled with the seed, then sorted largest first (the sort is stable, so
   groups of equal size keep their shuffled order). Big groups are hardest to fit, so they go
   first while there is still room; single queries come last and fill the remaining slots.
3. Placement. Each group goes to the split where it overshoots the remaining slots of its
   categories the least. If both are equally good, it goes to dev with probability
   (free dev slots) / (free slots) in its categories, like drawing without replacement.

With no shared answers this hits every category target exactly. Groups can force a category
off target (a group of 3 cannot be split 60/40); the targets and the actual counts are both
written to benchmark/split.json, together with the seed and the groups, and every evaluation
run records the seed.
"""
import argparse
import json
import random
from collections import Counter
from datetime import datetime, timezone

from mathsearch.paths import QUERIES_PATH
from mathsearch.queries import CATEGORIES, load_queries, save_queries, share_answer

DEV_PERCENT = 60
DEFAULT_SEED = 0
SPLITS = ("dev", "test")


def dev_counts(group_sizes, dev_percent=DEV_PERCENT):
    """{category: dev target}, using whole-number arithmetic only."""
    total = sum(group_sizes.values())
    total_dev = (total * dev_percent + 50) // 100  # 60% of the total, rounded
    counts = {c: n * dev_percent // 100 for c, n in group_sizes.items()}
    remainders = {c: n * dev_percent % 100 for c, n in group_sizes.items()}
    leftover = total_dev - sum(counts.values())
    # Largest remainder first; ties go to the category listed first in CATEGORIES.
    for category in sorted(group_sizes, key=lambda c: -remainders[c])[:leftover]:
        counts[category] += 1
    return counts


def answer_groups(queries):
    """Split queries into groups connected by shared grade-2 spans (transitively).
    Every query is in exactly one group; most groups have one query."""
    groups, seen = [], set()
    for start in queries:
        if start["id"] in seen:
            continue
        seen.add(start["id"])
        group, to_visit = [], [start]
        while to_visit:
            query = to_visit.pop()
            group.append(query)
            for other in queries:
                if other["id"] not in seen and share_answer(query, other):
                    seen.add(other["id"])
                    to_visit.append(other)
        groups.append(sorted(group, key=lambda q: q["id"]))
    return groups


def overshoot(category_counts, free_slots):
    """How many queries would land beyond the free slots of their category."""
    return sum(max(0, n - free_slots[c]) for c, n in category_counts.items())


def choose_split(category_counts, free, rng):
    over = {split: overshoot(category_counts, free[split]) for split in SPLITS}
    if over["dev"] != over["test"]:
        return min(SPLITS, key=lambda split: over[split])
    dev_slots = sum(max(free["dev"][c], 0) for c in category_counts)
    all_slots = dev_slots + sum(max(free["test"][c], 0) for c in category_counts)
    p_dev = dev_slots / all_slots if all_slots else DEV_PERCENT / 100
    return "dev" if rng.random() < p_dev else "test"


def assign_splits(queries, seed=DEFAULT_SEED):
    """Return (queries with "split" set, {category: dev target}, groups)."""
    rng = random.Random(seed)
    ordered = sorted(queries, key=lambda q: q["id"])  # independent of file order
    sizes = Counter(q["category"] for q in ordered)
    sizes = {c: sizes[c] for c in CATEGORIES if sizes[c]}
    targets = dev_counts(sizes)
    free = {"dev": dict(targets), "test": {c: sizes[c] - targets[c] for c in sizes}}

    groups = answer_groups(ordered)
    rng.shuffle(groups)
    groups.sort(key=len, reverse=True)

    split_by_id = {}
    for group in groups:
        category_counts = Counter(q["category"] for q in group)
        split = choose_split(category_counts, free, rng)
        for category, n in category_counts.items():
            free[split][category] -= n
        for query in group:
            split_by_id[query["id"]] = split
    return [{**q, "split": split_by_id[q["id"]]} for q in queries], targets, groups


def split_record(queries, targets, groups, seed):
    """What gets written to benchmark/split.json."""
    per_category = {}
    for category, target in targets.items():
        group = [q for q in queries if q["category"] == category]
        dev = sum(q["split"] == "dev" for q in group)
        per_category[category] = {"dev": dev, "test": len(group) - dev, "dev_target": target}
    return {
        "seed": seed,
        "dev_percent": DEV_PERCENT,
        "method": ("stratified by category with largest-remainder dev targets; queries sharing a "
                   "grade-2 span are grouped and placed together, largest groups first; "
                   "random.Random(seed) for group order and tie-breaks"),
        "assigned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dev_total": sum(q["split"] == "dev" for q in queries),
        "dev_target_total": sum(targets.values()),
        "per_category": per_category,
        "shared_answer_groups": [[q["id"] for q in group] for group in groups if len(group) > 1],
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
    unlabeled = [q["id"] for q in queries if not any(label["grade"] == 2 for label in q["labels"])]
    if unlabeled:
        raise SystemExit(f"Label every query before splitting (grouping needs the answers). No grade-2 span: {unlabeled}")

    queries, targets, groups = assign_splits(queries, args.seed)
    record = split_record(queries, targets, groups, args.seed)
    save_queries(queries, QUERIES_PATH)
    split_file.write_text(json.dumps(record, indent=2) + "\n")

    print(f"Seed {args.seed}: {record['dev_total']} dev (target {record['dev_target_total']}), "
          f"{len(record['test_ids'])} test")
    for category, counts in record["per_category"].items():
        print(f"  {category}: {counts['dev']} dev / {counts['test']} test (dev target {counts['dev_target']})")
    print(f"{len(record['shared_answer_groups'])} groups of queries sharing an answer kept together")
    print(f"Recorded in {split_file}")


if __name__ == "__main__":
    main()
