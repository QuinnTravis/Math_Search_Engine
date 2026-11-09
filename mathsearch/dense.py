"""Dense retrieval: Sentence-BERT embeddings in an exact (flat) FAISS index.

Same model and index type as the original project. Two deliberate differences:
- The model runs on CPU, so latency numbers match what a CPU server would see.
- `normalize_embeddings=True` is explicit. all-MiniLM-L6-v2 already ends with a
  normalisation layer, so this changes nothing for this model; it just makes the
  "inner product == cosine similarity" assumption hold for any other model too.

This is the only module that imports faiss, and the import order below matters. On macOS,
torch and faiss each ship their own copy of the OpenMP library. If faiss is imported first,
model.encode() crashes with a segmentation fault; importing torch (via sentence_transformers)
first works. Keeping faiss behind this module means nothing else can get the order wrong.
"""
from sentence_transformers import SentenceTransformer  # must come before faiss, see above
import faiss  # noqa: E402  (isort: skip)
import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"


def load_model(name=MODEL_NAME):
    return SentenceTransformer(name, device="cpu")


def embed(model, texts, show_progress=False):
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=show_progress)
    return np.asarray(vectors, dtype="float32")


def token_counts(model, words):
    """Number of WordPiece tokens in each word, without [CLS]/[SEP]."""
    if not words:
        return []
    ids = model.tokenizer(words, add_special_tokens=False, verbose=False)["input_ids"]
    return [len(word_ids) for word_ids in ids]


def token_lengths(model, texts):
    """Length of each text as the model sees it before truncation, including [CLS] and [SEP]."""
    ids = model.tokenizer(texts, add_special_tokens=True, verbose=False)["input_ids"]
    return [len(text_ids) for text_ids in ids]


def build_flat_index(vectors):
    """Exact inner-product search over every vector. With unit vectors, inner product is cosine similarity."""
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def save_index(index, path):
    faiss.write_index(index, str(path))


def load_index(path):
    return faiss.read_index(str(path))


def search(index, model, query, top_k=10):
    """Return [(row_id, score)] best first."""
    query_vector = embed(model, [query])
    top_k = min(top_k, index.ntotal)  # FAISS pads with id -1 if asked for more rows than exist
    scores, ids = index.search(query_vector, top_k)
    return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i != -1]
