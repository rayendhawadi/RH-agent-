"""
Étage 2 du scoring A4 : rapprochement sémantique via bge-m3 + pgvector.
Sert de feature de pré-classement (pas de décision finale — le juge LLM tranche).
"""
from __future__ import annotations

from functools import lru_cache

_MODEL_NAME = "BAAI/bge-m3"


@lru_cache
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


def embed_text(text: str) -> list[float]:
    model = _get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    import numpy as np

    va, vb = np.array(a), np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1e-9
    return float(np.dot(va, vb) / denom)


def semantic_prescore(profile_text: str, job_text: str) -> float:
    """Score 0-1 utilisé uniquement pour trier le lot avant le passage au juge."""
    return cosine_similarity(embed_text(profile_text), embed_text(job_text))
