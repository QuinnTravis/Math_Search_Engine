from sentence_transformers import SentenceTransformer

class Embedder:
    """Handles converting text chunks into embeddings."""
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts):
        """Convert list of texts into embeddings."""
        return self.model.encode(texts, show_progress_bar=True)
