"""Splitting page text into chunks for indexing.

`clean_text` and `chunk_text` are copied unchanged from the original project, because the
baseline must measure the original pipeline. Known problems (see docs/phase-0.md):
- 400 words is longer than the embedding model's 256-token limit, so the end of most chunks is never embedded.
- Chunks never cross a page boundary, which leaves many tiny end-of-page chunks.
- Newlines are removed, so theorem and definition headings cannot be detected afterwards.
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


def fixed_size_chunks(book_id, pages, chunk_size=400):
    """The original chunking: clean each page, then cut it into fixed-size word windows.

    Every chunk records the pages it came from, so it can be matched to page-span labels.
    """
    chunks = []
    for page in pages:
        for piece in chunk_text(clean_text(page["text"]), chunk_size):
            chunks.append({
                "book": book_id,
                "page_start": page["page"],
                "page_end": page["page"],
                "text": piece,
            })
    return chunks
