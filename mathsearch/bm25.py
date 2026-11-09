"""BM25 keyword retrieval, written out in full so every step can be explained.

score(doc, query) = sum over unique query terms t of
    idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_length / avg_doc_length))

idf(t) = ln(1 + (N - df + 0.5) / (df + 0.5))   (the Lucene form, which is never negative)

tf = how often t occurs in the doc, df = how many docs contain t, N = number of docs.
k1 controls how quickly repeated terms stop adding score; b controls how much long
documents are penalised. k1=1.2, b=0.75 are the common defaults and are not tuned here.
"""
import math
import re
from collections import Counter, defaultdict

TOKEN_PATTERN = re.compile(r"\w+")


def tokenize(text):
    """Lowercase and split into runs of letters/digits. No stemming, no stop words."""
    return TOKEN_PATTERN.findall(text.lower())


class BM25:
    def __init__(self, texts, k1=1.2, b=0.75):
        self.k1 = k1
        self.b = b
        self.doc_lengths = []
        self.postings = defaultdict(list)  # term -> list of (doc_id, term count in that doc)
        for doc_id, text in enumerate(texts):
            counts = Counter(tokenize(text))
            self.doc_lengths.append(sum(counts.values()))
            for term, count in counts.items():
                self.postings[term].append((doc_id, count))
        self.num_docs = len(texts)
        self.avg_length = sum(self.doc_lengths) / max(self.num_docs, 1)

    def idf(self, term):
        df = len(self.postings.get(term, []))
        return math.log(1 + (self.num_docs - df + 0.5) / (df + 0.5))

    def scores(self, query):
        """Return {doc_id: score} for every doc that contains at least one query term."""
        scores = defaultdict(float)
        for term in set(tokenize(query)):
            idf = self.idf(term)
            for doc_id, tf in self.postings.get(term, []):
                length_norm = 1 - self.b + self.b * self.doc_lengths[doc_id] / self.avg_length
                scores[doc_id] += idf * tf * (self.k1 + 1) / (tf + self.k1 * length_norm)
        return scores

    def search(self, query, top_k=10):
        """Return [(doc_id, score)] best first. Ties are broken by doc_id so results are deterministic."""
        ranked = sorted(self.scores(query).items(), key=lambda item: (-item[1], item[0]))
        return ranked[:top_k]
