"""Benchmark labeling tool.   Run:  make label   (= streamlit run benchmark/label_app.py)

Per query (full rules in benchmark/README.md):
  1. Write the query and choose its category.
  2. Find every passage that answers it, using the keyword search or by browsing pages
     (tables of contents and back-of-book indexes help).
  3. Add each passage as a page span: grade 2 = directly answers, 1 = related background.
  4. Optional, after 2-3: review the systems' top results to catch passages you missed.

Everything is saved straight to benchmark/queries.jsonl.
"""
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymupdf  # noqa: E402
import streamlit as st  # noqa: E402

from mathsearch.corpus import load_books  # noqa: E402
from mathsearch.extract import load_pages  # noqa: E402
from mathsearch.queries import (  # noqa: E402
    CATEGORIES, load_queries, next_query_id, query_problems, save_queries, spans_overlap,
)
from mathsearch.retrievers import BASELINE_RUNS, index_is_built, load_run, parse_run  # noqa: E402

NEW = "NEW"
GRADE_NAMES = {2: "2 · directly answers", 1: "1 · related background", 0: "0 · not relevant"}

st.set_page_config(page_title="Benchmark labeling", layout="wide")


# ---------- cached data ----------

@st.cache_resource
def get_books():
    return {book["id"]: book for book in load_books()}


def normalize(text):
    """NFKC turns ligatures like 'ﬁ' into 'fi', so searching for 'defined' finds 'deﬁned'."""
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


@st.cache_resource(show_spinner="Extracting page text (first run only, about a minute)...")
def get_page_texts():
    """{(book_id, page_number): normalized page text}"""
    texts = {}
    for book_id, book in get_books().items():
        for page in load_pages(book):
            texts[(book_id, page["page"])] = normalize(page["text"])
    return texts


@st.cache_data(max_entries=50)
def render_page(book_id, page_number):
    with pymupdf.open(get_books()[book_id]["path"]) as doc:
        return doc[page_number - 1].get_pixmap(dpi=110).tobytes("png")


@st.cache_resource(show_spinner="Loading the retrieval systems...")
def get_systems():
    """[(chunks, retriever)] for every baseline run. Pooling from all of them catches more missed answers."""
    systems = []
    for spec in BASELINE_RUNS:
        _, chunks, retriever = load_run(spec)
        systems.append((chunks, retriever))
    return systems


def baselines_built():
    return all(index_is_built(parse_run(spec)[0]) for spec in BASELINE_RUNS)


# ---------- search helpers ----------

def keyword_search(phrase, limit=40):
    """Pages containing every word of the phrase (as substrings), most occurrences first."""
    words = normalize(phrase).split()
    hits = []
    for (book_id, page), text in get_page_texts().items():
        if all(word in text for word in words):
            hits.append((sum(text.count(word) for word in words), book_id, page))
    hits.sort(key=lambda hit: (-hit[0], hit[1], hit[2]))
    return hits[:limit]


def snippet(text, word, width=160):
    position = max(text.find(word), 0)
    start = max(position - width // 2, 0)
    return "…" + text[start:start + width] + "…"


def pool_pages(query_text):
    """Pages in the top 10 of any baseline run, sorted by book and page so rank and system stay hidden."""
    pages = set()
    for chunks, retriever in get_systems():
        for chunk_id in retriever.search(query_text, 10):
            chunk = chunks[chunk_id]
            for page in range(chunk["page_start"], chunk["page_end"] + 1):
                pages.add((chunk["book"], page))
    return sorted(pages)


# ---------- saving (all run as button callbacks, before the page redraws) ----------

def find_query(queries, query_id):
    return next((q for q in queries if q["id"] == query_id), None)


def save_query_form(form_id):
    """Save the query form. `form_id` is the query's id, or NEW for a query not yet saved."""
    text = st.session_state[f"text_{form_id}"].strip()
    category = st.session_state[f"category_{form_id}"]
    notes = st.session_state[f"notes_{form_id}"].strip()
    if not text:
        st.session_state.flash = "The query text is empty."
        return

    queries = load_queries()
    if form_id == NEW:
        query = {"id": next_query_id(queries), "query": "", "category": "", "split": "", "notes": "", "labels": []}
        queries.append(query)
        for field in ("text", "category", "notes"):  # clear the "new query" form for next time
            st.session_state.pop(f"{field}_{NEW}", None)
    else:
        query = find_query(queries, form_id)
    query["query"], query["category"], query["notes"] = text, category, notes
    save_queries(queries)
    st.session_state.current = query["id"]


def add_label(query_id, label):
    queries = load_queries()
    query = find_query(queries, query_id)
    for existing in query["labels"]:
        if spans_overlap(existing, label):
            st.session_state.flash = (
                f"Overlaps the existing span {existing['book']} p.{existing['start']}-{existing['end']}. "
                "Delete that span first if you want to change it."
            )
            return
    query["labels"].append(label)
    save_queries(queries)


def add_span_from_form(query_id, book_id, start_key, end_key, grade_key):
    start, end = st.session_state[start_key], st.session_state[end_key]
    if start > end:
        st.session_state.flash = "The first page must not be after the last page."
        return
    add_label(query_id, {"book": book_id, "start": start, "end": end,
                         "grade": st.session_state[grade_key], "found_via": "manual"})


def delete_label(query_id, index):
    queries = load_queries()
    del find_query(queries, query_id)["labels"][index]
    save_queries(queries)


def view(book_id, page):
    st.session_state.view_book = book_id
    st.session_state.view_page = page


def step_page(delta):
    pages = get_books()[st.session_state.view_book]["pages"]
    st.session_state.view_page = min(max(st.session_state.view_page + delta, 1), pages)


def clamp_page():
    pages = get_books()[st.session_state.view_book]["pages"]
    st.session_state.view_page = min(st.session_state.view_page, pages)


# ---------- page layout ----------

books = get_books()
queries = load_queries()
pages_by_book = {book_id: book["pages"] for book_id, book in books.items()}
st.session_state.setdefault("current", NEW)
st.session_state.setdefault("view_book", next(iter(books)))
st.session_state.setdefault("view_page", 1)

# Sidebar: choose a query, see progress.
with st.sidebar:
    st.header("Queries")
    options = [NEW] + [q["id"] for q in queries]
    labels = {NEW: "➕ New query", **{q["id"]: f"{q['id']} · {q['query'][:45]}" for q in queries}}
    st.selectbox("Query", options, key="current", format_func=labels.get)

    with_answer = sum(any(label["grade"] == 2 for label in q["labels"]) for q in queries)
    st.metric("Written", f"{len(queries)} / 100")
    st.caption(f"{with_answer} have at least one grade-2 span")
    st.caption(" · ".join(f"{c}: {sum(q['category'] == c for q in queries)}" for c in CATEGORIES))

if "flash" in st.session_state:
    st.error(st.session_state.pop("flash"))

current = find_query(queries, st.session_state.current)
form_id = current["id"] if current else NEW

# The query itself.
st.subheader("New query" if current is None else f"Query {current['id']}")
with st.form(f"query_form_{form_id}"):
    st.text_area("Query, written the way a student would ask it", value=current["query"] if current else "",
                 key=f"text_{form_id}", height=70)
    category_index = CATEGORIES.index(current["category"]) if current and current["category"] in CATEGORIES else 0
    st.selectbox("Category", CATEGORIES, index=category_index, key=f"category_{form_id}")
    st.text_input("Notes (optional: ambiguity, why a span is grade 1, ...)",
                  value=current["notes"] if current else "", key=f"notes_{form_id}")
    st.form_submit_button("Save query", on_click=save_query_form, args=(form_id,))

if current is None:
    st.info("Save the query to start adding labels.")
    st.stop()

# Labels so far.
st.markdown("**Labeled spans**")
if not current["labels"]:
    st.caption("None yet.")
for index, label in enumerate(current["labels"]):
    cols = st.columns([5, 2, 1, 1])
    cols[0].write(f"{label['book']}, pages {label['start']}–{label['end']}")
    cols[1].write(GRADE_NAMES[label["grade"]] + (" (from review)" if label.get("found_via") == "pool" else ""))
    cols[2].button("View", key=f"view_label_{index}", on_click=view, args=(label["book"], label["start"]))
    cols[3].button("Delete", key=f"delete_label_{index}", on_click=delete_label, args=(current["id"], index))
remaining = [p for p in query_problems(current, pages_by_book) if not p.startswith("no split")]
for problem in remaining:
    st.warning(problem)

st.divider()
left, right = st.columns(2)

# Left: find candidate pages.
with left:
    st.markdown("**Keyword search over page text**")
    st.caption("Matches pages containing every word. Try the book's own terms *and* synonyms; "
               "check tables of contents and indexes too.")
    phrase = st.text_input("Words", key=f"search_{current['id']}")
    if phrase:
        hits = keyword_search(phrase)
        st.caption(f"{len(hits)} pages (top 40 shown)")
        first_word = normalize(phrase).split()[0]
        page_texts = get_page_texts()
        for count, book_id, page in hits:
            cols = st.columns([5, 1])
            cols[0].markdown(f"**{book_id} p.{page}** ({count}×) {snippet(page_texts[(book_id, page)], first_word)}")
            cols[1].button("View", key=f"view_hit_{book_id}_{page}", on_click=view, args=(book_id, page))

    with st.expander("Review system results (only after your own search)"):
        st.caption("Pages from the top 10 of each system being evaluated, minus pages you have already judged. "
                   "Judge each one so missed answers are caught. System and rank are hidden on purpose.")
        if not baselines_built():
            st.info("Build the index first: `make index`")
        elif st.checkbox("Show candidates", key=f"pool_{current['id']}"):
            judged = current["labels"]
            candidates = [(b, p) for b, p in pool_pages(current["query"])
                          if not any(spans_overlap({"book": b, "start": p, "end": p}, s) for s in judged)]
            if not candidates:
                st.success("Every candidate has been judged.")
            for book_id, page in candidates:
                st.markdown(f"**{book_id} p.{page}** {get_page_texts()[(book_id, page)][:220]}…")
                cols = st.columns(4)
                cols[0].button("View", key=f"pool_view_{book_id}_{page}", on_click=view, args=(book_id, page))
                for col, grade in zip(cols[1:], (2, 1, 0)):
                    col.button(GRADE_NAMES[grade], key=f"pool_{grade}_{book_id}_{page}", on_click=add_label,
                               args=(current["id"], {"book": book_id, "start": page, "end": page,
                                                     "grade": grade, "found_via": "pool"}))

# Right: page viewer and "add span".
with right:
    cols = st.columns([3, 2, 1, 1])
    cols[0].selectbox("Book", list(books), key="view_book", on_change=clamp_page)
    book = books[st.session_state.view_book]
    cols[1].number_input("PDF page", min_value=1, max_value=book["pages"], key="view_page")
    cols[2].button("◀", on_click=step_page, args=(-1,))
    cols[3].button("▶", on_click=step_page, args=(1,))

    book_id, page = book["id"], st.session_state.view_page
    form_key = f"{current['id']}_{book_id}_{page}"
    with st.form(f"span_form_{form_key}"):
        st.caption(f"Add a span in {book_id}. Page numbers are PDF pages (the box above), not printed page numbers.")
        c1, c2 = st.columns(2)
        c1.number_input("From page", 1, book["pages"], value=page, key=f"start_{form_key}")
        c2.number_input("To page", 1, book["pages"], value=page, key=f"end_{form_key}")
        st.radio("Grade", [2, 1], format_func=GRADE_NAMES.get, horizontal=True, key=f"grade_{form_key}")
        st.form_submit_button("Add span", on_click=add_span_from_form,
                              args=(current["id"], book_id, f"start_{form_key}", f"end_{form_key}", f"grade_{form_key}"))
    st.image(render_page(book_id, page), width="stretch")
