"""Search UI.   Run:  make app   (after `make index`)

Loads the prebuilt index once per server process (st.cache_resource). The original app
re-extracted and re-embedded every PDF on every click, because Streamlit reruns the
whole script on each interaction. Phase 2 moves this UI behind the FastAPI service.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from mathsearch.corpus import load_books  # noqa: E402
from mathsearch.retrievers import DEFAULT_INDEX, SYSTEMS, load_chunks, make_retriever  # noqa: E402

st.set_page_config(page_title="Math Search")


@st.cache_resource(show_spinner="Loading index...")
def get_chunks():
    return load_chunks(DEFAULT_INDEX)


@st.cache_resource(show_spinner="Loading retriever...")
def get_retriever(name):
    return make_retriever(name, DEFAULT_INDEX, get_chunks())


st.title("Math Textbook Search")
if not (DEFAULT_INDEX / "config.json").exists():
    st.error("No index found. Build it first with `make index`.")
    st.stop()

titles = {book["id"]: book["title"] for book in load_books()}
query = st.text_input("Search query")
system = st.radio("Retrieval mode", SYSTEMS, horizontal=True)
top_k = st.slider("Number of results", 1, 10, 5)

if query:
    chunks = get_chunks()
    for rank, chunk_id in enumerate(get_retriever(system).search(query, top_k), start=1):
        chunk = chunks[chunk_id]
        st.markdown(f"**{rank}. {titles[chunk['book']]}**, PDF page {chunk['page_start']}")
        st.write(chunk["text"][:400] + "…")
