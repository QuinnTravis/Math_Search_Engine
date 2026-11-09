"""Search the built index from the command line.

Usage:  python -m mathsearch.search "conditions for an Eulerian circuit" --system dense -k 5
"""
import argparse

from mathsearch.corpus import load_books
from mathsearch.retrievers import DEFAULT_INDEX, SYSTEMS, load_chunks, make_retriever


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query")
    parser.add_argument("--system", default="dense", choices=SYSTEMS)
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()

    titles = {book["id"]: book["title"] for book in load_books()}
    chunks = load_chunks(DEFAULT_INDEX)
    retriever = make_retriever(args.system, DEFAULT_INDEX, chunks)
    for rank, chunk_id in enumerate(retriever.search(args.query, args.k), start=1):
        chunk = chunks[chunk_id]
        print(f"{rank}. {titles[chunk['book']]}, page {chunk['page_start']}")
        print(f"   {chunk['text'][:200]}...\n")


if __name__ == "__main__":
    main()
