"""Where everything lives on disk. All paths are relative to the repo root."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CORPUS_MANIFEST = REPO_ROOT / "corpus" / "books.json"

DATA_DIR = REPO_ROOT / "data"  # generated, git-ignored
PAGES_DIR = DATA_DIR / "pages"  # cached text extraction, one JSONL file per book
INDEX_DIR = DATA_DIR / "index"  # one sub-folder per index configuration

QUERIES_PATH = REPO_ROOT / "benchmark" / "queries.jsonl"
RESULTS_DIR = REPO_ROOT / "results"
