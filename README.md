# Math PDF Semantic Search Engine

A multi-modal search engine for math textbooks and PDFs, designed to handle both **digital text PDFs** and **scanned images**. Built with Python, FAISS, and sentence embeddings, it allows **semantic search across thousands of pages**, surfacing relevant content with high accuracy.

---

## Features
- **Semantic Search:** Uses Sentence-BERT embeddings for context-aware search.
- **Multi-modal PDF Support:** Handles standard text PDFs and scanned PDFs using OCR.
- **Chunking:** Splits pages into manageable chunks for better retrieval.
- **Fast Retrieval:** FAISS vector index for near real-time search.
- **Interactive UI:** Streamlit app for easy queries and results browsing.
- **Extensible:** Easily add new PDFs or scale to larger libraries.

---

## Tech Stack
- Python 3.10+
- PyMuPDF (fitz) for PDF parsing
- PIL + pytesseract for OCR
- Sentence-Transformers (`all-MiniLM-L6-v2`) for embeddings
- FAISS for vector search
- Streamlit for web-based UI

---

## Installation
1. Clone the repository:
```bash
git clone <repo-url>
cd math-pdf-search
