"""Retrieval metrics against page-span labels.

A retrieved chunk "hits" a labeled span if they are in the same book and their page
ranges overlap. Two rules keep the numbers comparable across chunking strategies:

1. Binary metrics (Recall@k, MRR) count only grade-2 spans ("directly answers").
2. In nDCG, each labeled span can earn its grade at most once. Otherwise a system that
   returns three chunks from the same page would be rewarded three times, and a
   chunker that cuts pages finer would look better for no real reason.

`retrieved` is a ranked list of chunk dicts with "book", "page_start", "page_end".
`spans` is a query's label list: dicts with "book", "start", "end", "grade".
"""
import math

ANSWER_GRADE = 2


def overlaps(chunk, span):
    return (
        chunk["book"] == span["book"]
        and chunk["page_start"] <= span["end"]
        and span["start"] <= chunk["page_end"]
    )


def answer_spans(spans):
    return [span for span in spans if span["grade"] >= ANSWER_GRADE]


def recall_at_k(retrieved, spans, k):
    """Fraction of grade-2 spans that at least one of the top-k chunks overlaps."""
    answers = answer_spans(spans)
    found = [span for span in answers if any(overlaps(chunk, span) for chunk in retrieved[:k])]
    return len(found) / len(answers)


def reciprocal_rank(retrieved, spans, k=10):
    """1 / rank of the first chunk that overlaps a grade-2 span, or 0 if none in the top k."""
    answers = answer_spans(spans)
    for rank, chunk in enumerate(retrieved[:k], start=1):
        if any(overlaps(chunk, span) for span in answers):
            return 1 / rank
    return 0.0


def gains(retrieved, spans, k):
    """Gain of each of the top-k chunks: the grade of the best labeled span it overlaps
    that has not already been credited to a higher-ranked chunk (0 if none)."""
    credited = set()
    result = []
    for chunk in retrieved[:k]:
        best_grade, best_index = 0, None
        for index, span in enumerate(spans):
            if index not in credited and span["grade"] > best_grade and overlaps(chunk, span):
                best_grade, best_index = span["grade"], index
        if best_index is not None:
            credited.add(best_index)
        result.append(best_grade)
    return result


def dcg(gain_list):
    """Discounted cumulative gain with linear gains: sum of gain / log2(rank + 1)."""
    return sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gain_list, start=1))


def ndcg_at_k(retrieved, spans, k=10):
    """DCG of the ranking divided by the DCG of the best possible ranking (every labeled
    span retrieved once, highest grades first)."""
    ideal = sorted((span["grade"] for span in spans if span["grade"] > 0), reverse=True)[:k]
    return dcg(gains(retrieved, spans, k)) / dcg(ideal)


def query_metrics(retrieved, spans):
    return {
        "recall_at_5": recall_at_k(retrieved, spans, 5),
        "recall_at_10": recall_at_k(retrieved, spans, 10),
        "mrr": reciprocal_rank(retrieved, spans, 10),
        "ndcg_at_10": ndcg_at_k(retrieved, spans, 10),
    }
