from mathsearch.chunking import chunk_text, clean_text, fixed_size_chunks, token_capped_chunks


def test_clean_text_lowercases_and_collapses_whitespace():
    assert clean_text("Theorem 2.1\n  Let  G") == "theorem 2.1 let g"


def test_chunk_text_fixed_windows_without_overlap():
    text = " ".join(str(i) for i in range(10))
    assert chunk_text(text, chunk_size=4) == ["0 1 2 3", "4 5 6 7", "8 9"]


def test_chunks_stay_inside_their_page_and_record_word_counts():
    pages = [{"page": 1, "text": "a b c"}, {"page": 2, "text": "d e"}]
    chunks = fixed_size_chunks("book", pages, chunk_size=2)
    assert [(c["page_start"], c["text"]) for c in chunks] == [(1, "a b"), (1, "c"), (2, "d e")]
    assert [c["page_words"] for c in chunks] == [[[1, 2]], [[1, 1]], [[2, 2]]]


def fake_token_counts(words):
    """Pretend each word costs as many tokens as it has letters."""
    return [len(word) for word in words]


def test_token_capped_chunks_never_exceed_the_budget():
    pages = [{"page": 3, "text": "aa bb c ddd e"}, {"page": 4, "text": "ffffff g"}]
    chunks = token_capped_chunks("book", pages, fake_token_counts, max_tokens=5)
    # page 3: aa+bb+c = 5 fits; ddd would make 8, so a new chunk starts. Page 4 starts fresh.
    # "ffffff" alone is over budget; it still becomes its own chunk rather than being dropped.
    assert [c["text"] for c in chunks] == ["aa bb c", "ddd e", "ffffff", "g"]
    assert [c["page_words"] for c in chunks] == [[[3, 3]], [[3, 2]], [[4, 1]], [[4, 1]]]


def test_token_capped_chunks_keep_every_word():
    pages = [{"page": 1, "text": "one two three four five six seven"}]
    chunks = token_capped_chunks("book", pages, fake_token_counts, max_tokens=8)
    assert " ".join(c["text"] for c in chunks) == clean_text(pages[0]["text"])
