"""Metric values checked against hand-computed examples.

Toy labels for one query:
  A: book x, pages 10-11, grade 2
  B: book x, page 20,     grade 1
  C: book y, page 5,      grade 2
Ranking (top 5, one-page chunks): x p30 (miss), x p11 (A), x p10 (A again), y p5 (C), x p20 (B)
"""
import math

import pytest

from mathsearch.metrics import (
    MIN_OVERLAP, dcg, gains, hits, ideal_ranking, ndcg_at_k, overlap_fraction, reciprocal_rank,
    span_recall_at_k,
)


def chunk(book, *page_words):
    """chunk("x", (10, 100), (11, 50)) = 100 words from page 10 and 50 from page 11."""
    if all(isinstance(p, int) for p in page_words):  # chunk("x", 11) = one page, 100 words
        page_words = [(p, 100) for p in page_words]
    return {"book": book, "page_words": [list(pw) for pw in page_words]}


SPANS = [
    {"book": "x", "start": 10, "end": 11, "grade": 2},
    {"book": "x", "start": 20, "end": 20, "grade": 1},
    {"book": "y", "start": 5, "end": 5, "grade": 2},
]
RANKING = [chunk("x", 30), chunk("x", 11), chunk("x", 10), chunk("y", 5), chunk("x", 20)]


# ---- when does a chunk hit a span? ----

def test_overlap_fraction_counts_words_by_page():
    span = SPANS[0]  # x, pages 10-11
    assert overlap_fraction(chunk("x", 11), span) == 1.0
    assert overlap_fraction(chunk("x", (9, 300), (10, 100)), span) == 0.25
    assert overlap_fraction(chunk("y", 10), span) == 0.0  # other book


def test_minimum_overlap_rule():
    assert MIN_OVERLAP == 0.5
    span = SPANS[0]
    assert hits(chunk("x", (9, 100), (10, 100)), span)  # exactly half: counts
    assert not hits(chunk("x", (9, 101), (10, 100)), span)  # just under half: does not
    assert not hits(chunk("x", 7, 8, 9, 10), span)  # a big chunk touching one labeled page


# ---- span recall and MRR ----

def test_span_recall_is_fraction_of_grade_2_spans_found():
    assert span_recall_at_k(RANKING, SPANS, 1) == 0.0  # x p30 hits nothing
    assert span_recall_at_k(RANKING, SPANS, 2) == 0.5  # A found, C not yet
    assert span_recall_at_k(RANKING, SPANS, 5) == 1.0  # A and C; B is grade 1 so not counted


def test_span_recall_is_not_hit_rate():
    # One of two answers found: a hit rate would say 1.0, span recall says 0.5.
    assert span_recall_at_k([chunk("x", 10)], SPANS, 10) == 0.5


def test_reciprocal_rank_is_first_grade_2_hit():
    assert reciprocal_rank(RANKING, SPANS) == 0.5  # first answer at rank 2
    assert reciprocal_rank([chunk("x", 20)], SPANS) == 0.0  # grade-1 hit does not count


# ---- nDCG ----

def test_each_span_earns_gain_once():
    assert gains(RANKING, SPANS, 5) == [0, 2, 0, 2, 1]  # rank 3 hits A again, so earns nothing


def test_ideal_ranking_uses_the_same_rule():
    ideal = ideal_ranking(SPANS)
    assert gains(ideal, SPANS, 10) == [2, 2, 1]  # each span once, best grade first
    assert gains(ideal + ideal, SPANS, 10) == [2, 2, 1, 0, 0, 0]  # repeats earn nothing


def test_dcg_by_hand():
    assert dcg([2, 1]) == pytest.approx(2 / 1 + 1 / math.log2(3))


def test_ndcg_by_hand():
    actual = 2 / math.log2(3) + 2 / math.log2(5) + 1 / math.log2(6)  # ranks 2, 4, 5
    ideal = 2 / 1 + 2 / math.log2(3) + 1 / math.log2(4)  # grades 2, 2, 1 at ranks 1-3
    assert ndcg_at_k(RANKING, SPANS, 10) == pytest.approx(actual / ideal)  # about 0.667


def test_ideal_is_cut_at_k():
    # k=1: ideal is a single grade-2 span; the ranking's best in the top 1 is a miss.
    assert ndcg_at_k(RANKING, SPANS, 1) == 0.0
    assert ndcg_at_k([chunk("y", 5)], SPANS, 1) == pytest.approx(1.0)


def test_perfect_ranking_scores_one():
    perfect = [chunk("x", 10), chunk("y", 5), chunk("x", 20)]
    assert ndcg_at_k(perfect, SPANS, 10) == pytest.approx(1.0)
    assert span_recall_at_k(perfect, SPANS, 5) == 1.0
    assert reciprocal_rank(perfect, SPANS) == 1.0


def test_grade_0_judgements_are_ignored():
    spans = SPANS + [{"book": "x", "start": 30, "end": 30, "grade": 0}]
    assert ndcg_at_k(RANKING, spans, 10) == ndcg_at_k(RANKING, SPANS, 10)
