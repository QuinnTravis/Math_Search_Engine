from src.processor import extract_text, chunk_text
from src.embedder import Embedder
from src.vector_db import VectorDB
import fitz

class SearchEngine:
    """Combines ingestion, embeddings, vector DB, and query capabilities."""
    def __init__(self):
        self.embedder = Embedder()
        self.vector_db = VectorDB()
        self.chunks_metadata = []

    def ingest_pdf(self, pdf_path):
        """Ingest PDF, extract text + chunk, and store metadata."""
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            text = extract_text(page)
            for chunk in chunk_text(text):
                self.chunks_metadata.append({
                    "book": pdf_path,
                    "page": i+1,
                    "text": chunk
                })

    def build_index(self):
        """Embed all chunks and store in FAISS vector database."""
        texts = [d['text'] for d in self.chunks_metadata]
        embeddings = self.embedder.embed_texts(texts)
        self.vector_db.add_vectors(embeddings, self.chunks_metadata)

    def query(self, q, top_k=5):
        """Search for a query string and print top-k results."""
        vec = self.embedder.embed_texts([q])[0]
        results = self.vector_db.search(vec, top_k)
        print(f"\n--- Top {top_k} results for query: '{q}' ---\n")
        for meta, score in results:
            print(f"[Score: {score:.4f}] {meta['book']} Page {meta['page']}")
            print(f"Snippet: {meta['text'][:200]}...\n")
