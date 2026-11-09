"""Retrieval metrics against page-span labels.

When does a retrieved chunk "hit" a labeled span?
  Same book, and at least MIN_OVERLAP (half) of the chunk's words come from pages inside
  the span. Chunks record how many words they took from each page ("page_words"), so this
  works for any chunker. Without a minimum, one huge chunk touching a labeled page by a
  single line would count as finding the answer, and bigger chunks would always score better.

Three more rules keep the numbers comparable across chunking strategies:
1. Binary metrics (SpanRecall@k, MRR) count only grade-2 spans ("directly answers").
2. SpanRecall@k is the fraction of a query's grade-2 spans hit in the top k (not a hit
   rate, which would only ask whether any answer appeared).
3. In nDCG, each labeled span can earn its grade at most once, and each chunk can earn
   credit for at most one span. The ideal ranking is scored by the same function, so the
   actual and ideal DCG always follow the same rule.

`retrieved` is a ranked list of chunk dicts with "book" and "page_words" ([[page, words], ...]).
`spans` is a query's label list: dicts with "book", "start", "end", "grade".
"""
import math

ANSWER_GRADE = 2
MIN_OVERLAP = 0.5


def overlap_fraction(chunk, span):
    """Share of the chunk's words that come from pages inside the span (0 for another book)."""
    if chunk["book"] != span["book"]:
        return 0.0
    total = sum(words for _, words in chunk["page_words"])
    inside = sum(words for page, words in chunk["page_words"] if span["start"] <= page <= span["end"])
    return inside / total


def hits(chunk, span):
    return overlap_fraction(chunk, span) >= MIN_OVERLAP


def answer_spans(spans):
    return [span for span in spans if span["grade"] >= ANSWER_GRADE]


def span_recall_at_k(retrieved, spans, k):
    """Fraction of grade-2 spans hit by at least one of the top-k chunks."""
    answers = answer_spans(spans)
    found = [span for span in answers if any(hits(chunk, span) for chunk in retrieved[:k])]
    return len(found) / len(answers)


def reciprocal_rank(retrieved, spans, k=10):
    """1 / rank of the first chunk that hits a grade-2 span, or 0 if none in the top k."""
    answers = answer_spans(spans)
    for rank, chunk in enumerate(retrieved[:k], start=1):
        if any(hits(chunk, span) for span in answers):
            return 1 / rank
    return 0.0


def gains(retrieved, spans, k):
    """Gain of each of the top-k chunks: the grade of the best labeled span it hits that
    has not already been credited to a higher-ranked chunk (0 if none)."""
    credited = set()
    result = []
    for chunk in retrieved[:k]:
        best_grade, best_index = 0, None
        for index, span in enumerate(spans):
            if index not in credited and span["grade"] > best_grade and hits(chunk, span):
                best_grade, best_index = span["grade"], index
        if best_index is not None:
            credited.add(best_index)
        result.append(best_grade)
    return result


def dcg(gain_list):
    """Discounted cumulative gain with linear gains: sum of gain / log2(rank + 1)."""
    return sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gain_list, start=1))


def perfect_chunk(span):
    """A chunk lying exactly on the span's pages."""
    pages = range(span["start"], span["end"] + 1)
    return {"book": span["book"], "page_words": [[page, 1] for page in pages]}


def ideal_ranking(spans):
    """The best possible ranking: one perfect chunk per labeled span, highest grade first."""
    graded = sorted((span for span in spans if span["grade"] > 0), key=lambda span: -span["grade"])
    return [perfect_chunk(span) for span in graded]


def ndcg_at_k(retrieved, spans, k=10):
    """DCG of the ranking divided by the DCG of the ideal ranking, both scored by gains()."""
    ideal = dcg(gains(ideal_ranking(spans), spans, k))
    return dcg(gains(retrieved, spans, k)) / ideal


def query_metrics(retrieved, spans):
    return {
        "span_recall_at_5": span_recall_at_k(retrieved, spans, 5),
        "span_recall_at_10": span_recall_at_k(retrieved, spans, 10),
        "mrr": reciprocal_rank(retrieved, spans, 10),
        "ndcg_at_10": ndcg_at_k(retrieved, spans, 10),
    }
