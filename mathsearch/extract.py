"""Text extraction from PDF pages, with a Tesseract OCR fallback for pages that have no text layer.

The extraction logic is unchanged from the original project (PyMuPDF first, OCR if a
page has fewer than 50 characters). What is new is that the raw text of every page is
cached to disk, so the index builder and the labeling tool do not re-extract each time.
"""
import json
from io import BytesIO

import pymupdf
import pytesseract
from PIL import Image

from mathsearch.paths import PAGES_DIR

OCR_THRESHOLD_CHARS = 50  # same threshold as the original code
OCR_DPI = 150


def ocr_page(page):
    """Render the page to an image and read it with Tesseract."""
    pix = page.get_pixmap(dpi=OCR_DPI)
    image = Image.open(BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(image)


def extract_page(page):
    """Return (text, used_ocr) for one page."""
    text = page.get_text()
    if len(text.strip()) < OCR_THRESHOLD_CHARS:
        return ocr_page(page), True
    return text, False


def extract_book(pdf_path):
    """Return a list of {"page", "text", "ocr"} dicts. Pages are numbered from 1 (PDF page index, not the printed number)."""
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            text, used_ocr = extract_page(page)
            pages.append({"page": index + 1, "text": text, "ocr": used_ocr})
    return pages


def load_pages(book, cache_dir=PAGES_DIR):
    """Extracted pages for a book, read from the cache if present.

    The cache file name includes the PDF hash, so a changed PDF is re-extracted.
    """
    cache_file = cache_dir / f"{book['id']}-{book['sha256'][:12]}.jsonl"
    if not cache_file.exists():
        pages = extract_book(book["path"])
        cache_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            for page in pages:
                f.write(json.dumps(page) + "\n")
    with open(cache_file) as f:
        return [json.loads(line) for line in f]
