import faiss
import numpy as np

class VectorDB:
    """FAISS-based vector database for fast semantic search."""
    def __init__(self, dim=384):
        self.index = faiss.IndexFlatIP(dim)  # cosine similarity
        self.metadata = []

    def add_vectors(self, embeddings, metadata):
        """Add embeddings and their metadata to the database."""
        self.index.add(np.array(embeddings).astype('float32'))
        self.metadata.extend(metadata)

    def search(self, query_vec, top_k=5):
        """Return top-k results for a query vector."""
        D, I = self.index.search(np.array([query_vec]).astype('float32'), top_k)
        results = []
        for idx, score in zip(I[0], D[0]):
            results.append((self.metadata[idx], score))
        return results
