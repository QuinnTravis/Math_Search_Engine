import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import pytesseract

def clean_text(text):
    """Standardizes text: lowercase, removes extra spaces."""
    return " ".join(text.lower().split())

def ocr_page(page):
    """Convert page image to text using OCR."""
    pix = page.get_pixmap(dpi=150)
    img = Image.open(BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img)

def extract_text(page):
    """Extracts text from a PDF page, uses OCR if page is scanned."""
    text = page.get_text()
    if len(text.strip()) < 50:
        text = ocr_page(page)
    return clean_text(text)

def chunk_text(text, chunk_size=400):
    """Split text into chunks of `chunk_size` words."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i+chunk_size]))
    return chunks
