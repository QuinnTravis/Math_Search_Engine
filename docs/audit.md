# Audit of the original project (2026-11-09)

This is the state of the repo before any upgrade work (commit `04f00bb`). Numbers marked *(new corpus)*
were re-measured on the open-license corpus with the baseline pipeline unchanged.

## What existed

| Part | Implementation |
| --- | --- |
| Layout | Everything under `Project Search/` (a folder name with a space). A CLI loop (`main.py`), a Streamlit app (`web_app/app.py`) and `src/` modules. |
| Extraction | PyMuPDF `page.get_text()`. Tesseract OCR at 150 dpi if a page has fewer than 50 characters. Then lowercase and collapse all whitespace, newlines included. |
| Chunking | 400-word windows, no overlap, cut inside each page. |
| Embedding | Sentence-BERT `all-MiniLM-L6-v2` (384 dimensions, maximum input 256 tokens, output L2-normalised). |
| Index | FAISS `IndexFlatIP`: exact search, which equals cosine similarity because the vectors are unit length. |
| UI | Streamlit text box and slider. It shows score, file path, page and the first 400 characters. |
| Missing | Evaluation, tests, CI, Docker, `.gitignore`, index persistence, logging, error handling. |

## Problems found

### Retrieval quality
1. **Most chunks are cut off before embedding.** *(new corpus)* 69% of chunks are longer than the model's 256-token limit (median 458 tokens). Only **55% of the corpus text is ever embedded**, and the rest of each chunk is silently dropped.
2. **Ligatures break keyword matching.** "deﬁned" uses the single character `ﬁ` (U+FB01), so it never matches "defined". There were 5,377 of these in the original corpus.
3. **Math loses its structure.** Superscripts flatten (`x²ₙ` becomes `x2 n`), `i ≠ j` becomes `i̸ = j`, and Levin's book uses Unicode math-italic letters (`𝑎`, `𝑑`) that a plain-text query will never match. Running headers and page numbers end up inside the chunks.
4. **Removing newlines before chunking** means theorem and definition headings can no longer be detected. Because chunks never cross pages, there are *(new corpus)* 341 tiny chunks under 50 words.
5. **OCR almost never matters.** *(new corpus)* 22 of 1,882 pages trigger it, and they are mostly blank, figure or part-title pages. A missing `tesseract` binary crashes the whole run.
6. **Page numbers are PDF page indexes, not printed numbers** (for example, PDF page 101 of the number theory book is printed page 78). The benchmark therefore uses PDF page numbers throughout.
7. `vector_db.search` with `top_k` larger than the number of chunks gets id `-1` from FAISS and silently returns the last chunk.

### Operability
8. **The Streamlit app rebuilt everything on every click.** Streamlit reruns the whole script on each interaction, and the app re-extracted about 2,000 pages and re-embedded about 2,900 chunks each time.
9. **`requirements.txt` could not be installed.** The committed `.pyc` files show Python 3.14 was used, but `numpy==1.26.0` requires Python below 3.13 and `faiss-cpu==1.7.4` has no wheels for it. `scikit-learn` was listed but never used.
10. `main.py` used a relative `pdfs` path, so it only worked when run from inside `Project Search/`.
11. Compiled `.pyc` files and all PDFs (about 17 MB) were committed.
12. The README stopped partway through the install instructions and made claims ("high accuracy", "near real-time") with no measurements.

### Licensing
13. `final.pdf` (Sagan, *Combinatorics*, AMS) is a copyrighted prepublication copy stamped "may not be posted electronically", and it is in the public repo. Two more books are licensed "no derivatives". See `benchmark/CORPUS.md`.

### Found while upgrading
14. On macOS, **importing `faiss` before `torch` makes `model.encode()` segfault**, because both bundle their own OpenMP runtime. `mathsearch/dense.py` is now the only module that imports faiss, and it imports torch first.
