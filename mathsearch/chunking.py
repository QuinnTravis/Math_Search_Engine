"""Splitting page text into chunks for indexing.

Two chunkers, both cutting inside each page after the original cleaning step:
- fixed_size_chunks: the original 400-word windows (`clean_text` and `chunk_text` are
  copied unchanged from the original project, so the baseline measures the original pipeline).
- token_capped_chunks: windows that fit the embedding model's token limit, so no text is
  truncated away. Everything else is identical, so comparing the two isolates truncation.

Known problems of both (see docs/audit.md): chunks never cross a page boundary, and
newlines are removed, so theorem and definition headings cannot be detected afterwards.

Every chunk records "page_words": [[page, number of words from that page], ...], which the
metrics use to decide whether a chunk overlaps a labeled span enough to count as a hit.
"""


def clean_text(text):
    """Lowercase and collapse all whitespace (including newlines) to single spaces."""
    return " ".join(text.lower().split())


def chunk_text(text, chunk_size=400):
    """Split text into consecutive pieces of `chunk_size` words, with no overlap."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks


def make_chunk(book_id, page_number, words):
    return {
        "book": book_id,
        "page_start": page_number,
        "page_end": page_number,
        "page_words": [[page_number, len(words)]],
        "text": " ".join(words),
    }


def fixed_size_chunks(book_id, pages, chunk_size=400):
    """The original chunking: clean each page, then cut it into fixed-size word windows."""
    chunks = []
    for page in pages:
        for piece in chunk_text(clean_text(page["text"]), chunk_size):
            chunks.append(make_chunk(book_id, page["page"], piece.split()))
    return chunks


def token_capped_chunks(book_id, pages, count_tokens, max_tokens):
    """Like fixed_size_chunks, but each window holds as many whole words as fit in
    `max_tokens` model tokens.

    `count_tokens(words)` returns the token count of each word. For a BERT tokenizer the
    counts of separate words add up exactly to the count of the joined text, because it
    splits on whitespace before applying WordPiece. The index builder double-checks this.
    """
    chunks = []
    for page in pages:
        words = clean_text(page["text"]).split()
        current, current_tokens = [], 0
        for word, tokens in zip(words, count_tokens(words)):
            if current and current_tokens + tokens > max_tokens:
                chunks.append(make_chunk(book_id, page["page"], current))
                current, current_tokens = [], 0
            current.append(word)
            current_tokens += tokens
        if current:
            chunks.append(make_chunk(book_id, page["page"], current))
    return chunks
