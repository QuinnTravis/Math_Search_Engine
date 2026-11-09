import math

import pytest

from mathsearch.bm25 import BM25, tokenize

DOCS = [
    "a group is a set with an operation",
    "a ring has two operations",
    "every cyclic group is abelian group",
]


def test_tokenize_lowercases_and_splits_on_punctuation():
    assert tokenize("Euler's Theorem, (mod n)") == ["euler", "s", "theorem", "mod", "n"]


def test_ligatures_are_not_normalised():
    # Documents the baseline's known weakness: 'ﬁ' (one character) is not 'fi'.
    assert tokenize("deﬁned") != tokenize("defined")


def test_idf_by_hand():
    bm25 = BM25(DOCS)
    # "group" appears in 2 of 3 docs: ln(1 + (3 - 2 + 0.5) / (2 + 0.5))
    assert bm25.idf("group") == pytest.approx(math.log(1 + 1.5 / 2.5))
    assert bm25.idf("ring") > bm25.idf("group")  # rarer term, higher weight


def test_score_by_hand():
    bm25 = BM25(DOCS, k1=1.2, b=0.75)
    avg = (8 + 5 + 6) / 3
    tf, length = 2, 6  # "group" twice in doc 2, which has 6 tokens
    expected = bm25.idf("group") * tf * 2.2 / (tf + 1.2 * (1 - 0.75 + 0.75 * length / avg))
    assert bm25.scores("group")[2] == pytest.approx(expected)


def test_search_ranks_and_ignores_unknown_words():
    bm25 = BM25(DOCS)
    assert [doc for doc, _ in bm25.search("cyclic group")] == [2, 0]
    assert bm25.search("banach") == []
