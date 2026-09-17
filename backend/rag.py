import re
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE = BASE_DIR / "knowledge_base"
MIN_SCORE = 0.2

_model = None
_doc_cache: tuple[list[dict[str, str]], np.ndarray] | None = None


def _tokens(text: str) -> list[str]:
	return re.findall(r"[a-z0-9]+", text.lower())


def _hashed_embedding(text: str, size: int = 256) -> np.ndarray:
	vector = np.zeros(size, dtype=float)
	for token in _tokens(text):
		vector[hash(token) % size] += 1
	norm = np.linalg.norm(vector)
	return vector / norm if norm else vector


def _load_documents() -> list[dict[str, str]]:
	return [{"source": path.name, "text": path.read_text(encoding="utf-8")} for path in sorted(KNOWLEDGE_BASE.glob("*.md"))]


def _get_model():
	global _model
	if _model is None:
		from sentence_transformers import SentenceTransformer

		_model = SentenceTransformer("all-MiniLM-L6-v2")
	return _model


def _document_vectors(documents: list[dict[str, str]]) -> np.ndarray:
	global _doc_cache
	if _doc_cache is not None and [item["source"] for item in _doc_cache[0]] == [item["source"] for item in documents]:
		return _doc_cache[1]
	vectors = _get_model().encode([item["text"] for item in documents], normalize_embeddings=True)
	_doc_cache = (documents, np.asarray(vectors))
	return _doc_cache[1]


def retrieve_context(query: str, top_k: int = 3) -> list[dict[str, str | float]]:
	documents = _load_documents()
	if not documents:
		return []
	try:
		query_vector = np.asarray(_get_model().encode([query], normalize_embeddings=True)[0])
		doc_vectors = _document_vectors(documents)
	except Exception:
		query_vector = _hashed_embedding(query)
		doc_vectors = np.array([_hashed_embedding(item["text"]) for item in documents])
	scores = doc_vectors @ query_vector
	ranked = np.argsort(scores)[::-1][:top_k]
	return [{**documents[index], "score": float(scores[index])} for index in ranked if scores[index] >= MIN_SCORE]
