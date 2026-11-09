"""Metric values checked against hand-computed examples.

Toy labels for one query:
  A: book x, pages 10-11, grade 2
  B: book x, page 20,     grade 1
  C: book y, page 5,      grade 2
Ranking (top 5): x p30 (miss), x p11 (A), x p10 (A again), y p5 (C), x p20 (B)
"""
import math

import pytest

from mathsearch.metrics import dcg, gains, ndcg_at_k, overlaps, recall_at_k, reciprocal_rank


def chunk(book, start, end=None):
    return {"book": book, "page_start": start, "page_end": end or start}


SPANS = [
    {"book": "x", "start": 10, "end": 11, "grade": 2},
    {"book": "x", "start": 20, "end": 20, "grade": 1},
    {"book": "y", "start": 5, "end": 5, "grade": 2},
]
RANKING = [chunk("x", 30), chunk("x", 11), chunk("x", 10), chunk("y", 5), chunk("x", 20)]


def test_overlap_needs_same_book_and_shared_page():
    span = SPANS[0]
    assert overlaps(chunk("x", 11), span)
    assert overlaps(chunk("x", 8, 10), span)  # chunk spanning into the label
    assert not overlaps(chunk("x", 12), span)
    assert not overlaps(chunk("y", 10), span)


def test_recall_counts_grade_2_spans_found():
    assert recall_at_k(RANKING, SPANS, 1) == 0.0  # x p30 hits nothing
    assert recall_at_k(RANKING, SPANS, 2) == 0.5  # A found, C not yet
    assert recall_at_k(RANKING, SPANS, 5) == 1.0  # A and C found; B is grade 1 so not counted


def test_reciprocal_rank_is_first_grade_2_hit():
    assert reciprocal_rank(RANKING, SPANS) == 0.5  # first answer at rank 2
    assert reciprocal_rank([chunk("x", 20)], SPANS) == 0.0  # grade-1 hit does not count


def test_each_span_earns_gain_once():
    # rank 3 hits A again, so it earns nothing
    assert gains(RANKING, SPANS, 5) == [0, 2, 0, 2, 1]


def test_dcg_by_hand():
    assert dcg([2, 1]) == pytest.approx(2 / 1 + 1 / math.log2(3))


def test_ndcg_by_hand():
    actual = 2 / math.log2(3) + 2 / math.log2(5) + 1 / math.log2(6)  # ranks 2, 4, 5
    ideal = 2 / 1 + 2 / math.log2(3) + 1 / math.log2(4)  # grades 2, 2, 1 at ranks 1-3
    assert ndcg_at_k(RANKING, SPANS, 10) == pytest.approx(actual / ideal)  # about 0.667


def test_perfect_ranking_scores_one():
    perfect = [chunk("x", 10), chunk("y", 5), chunk("x", 20)]
    assert ndcg_at_k(perfect, SPANS, 10) == pytest.approx(1.0)
    assert recall_at_k(perfect, SPANS, 5) == 1.0
    assert reciprocal_rank(perfect, SPANS) == 1.0


def test_grade_0_judgements_are_ignored():
    spans = SPANS + [{"book": "x", "start": 30, "end": 30, "grade": 0}]
    assert ndcg_at_k(RANKING, spans, 10) == ndcg_at_k(RANKING, SPANS, 10)
