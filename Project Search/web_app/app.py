import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.search_engine import SearchEngine
PDF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../pdfs"))

st.title("Math PDF Semantic Search Engine")

engine = SearchEngine()


pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
for f in pdf_files:
    engine.ingest_pdf(os.path.join(PDF_DIR, f))
engine.build_index()

query = st.text_input("Enter your search query:")
top_k = st.slider("Number of results", 1, 10, 5)

if st.button("Search") and query:
    results = engine.vector_db.search(engine.embedder.embed_texts([query])[0], top_k)
    for meta, score in results:
        st.write(f"**[Score: {score:.4f}] {meta['book']} Page {meta['page']}**")
        st.write(f"{meta['text'][:400]}...")
