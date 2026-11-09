"""The book manifest (corpus/books.json): which PDFs are indexed, and checks that they are the right files."""
import hashlib
import json
from pathlib import Path

import pymupdf

from mathsearch.paths import CORPUS_MANIFEST


def load_books(manifest=CORPUS_MANIFEST):
    """Read the manifest. Each book gets a "path" pointing at its PDF next to the manifest."""
    manifest = Path(manifest)
    books = json.loads(manifest.read_text())
    for book in books:
        book["path"] = manifest.parent / "pdfs" / book["file"]
    return books


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_books(books):
    """Return a list of problems (empty if every PDF exists, matches its hash and page count).

    The hash matters because benchmark labels point at page numbers: a different
    edition of a book would silently shift every label.
    """
    problems = []
    for book in books:
        path = book["path"]
        if not path.exists():
            problems.append(f"{book['id']}: missing file {path}")
            continue
        if sha256_of(path) != book["sha256"]:
            problems.append(f"{book['id']}: sha256 does not match the manifest")
        with pymupdf.open(path) as doc:
            if len(doc) != book["pages"]:
                problems.append(f"{book['id']}: has {len(doc)} pages, manifest says {book['pages']}")
    return problems
