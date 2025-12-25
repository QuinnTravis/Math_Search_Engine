from src.search_engine import SearchEngine
import os

PDF_DIR = "pdfs"

def main():
    engine = SearchEngine()

    # Ingest all PDFs in the folder
    for f in os.listdir(PDF_DIR):
        if f.lower().endswith(".pdf"):
            print(f"Ingesting {f}...")
            engine.ingest_pdf(os.path.join(PDF_DIR, f))

    
    print("Building embeddings and FAISS index...")
    engine.build_index()
    print(f"Index built with {len(engine.chunks_metadata)} chunks.\n")

    
    while True:
        q = input("Enter search query (or 'exit'): ").strip()
        if q.lower() == 'exit':
            break
        if q:
            engine.query(q)

if __name__ == "__main__":
    main()
