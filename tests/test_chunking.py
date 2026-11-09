from mathsearch.chunking import chunk_text, clean_text, fixed_size_chunks


def test_clean_text_lowercases_and_collapses_whitespace():
    assert clean_text("Theorem 2.1\n  Let  G") == "theorem 2.1 let g"


def test_chunk_text_fixed_windows_without_overlap():
    text = " ".join(str(i) for i in range(10))
    assert chunk_text(text, chunk_size=4) == ["0 1 2 3", "4 5 6 7", "8 9"]


def test_chunks_stay_inside_their_page():
    pages = [{"page": 1, "text": "a b c"}, {"page": 2, "text": "d e"}]
    chunks = fixed_size_chunks("book", pages, chunk_size=2)
    assert [(c["page_start"], c["text"]) for c in chunks] == [(1, "a b"), (1, "c"), (2, "d e")]
    assert all(c["page_start"] == c["page_end"] and c["book"] == "book" for c in chunks)
