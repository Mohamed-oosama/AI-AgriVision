"""
utils/models.py — v8 Ollama-based embeddings (No torch required).

بدل SentenceTransformers بنستخدم Ollama API مباشرةً:
  - bge-m3:latest مثبّت في Ollama ✅
  - مش محتاج torch أو transformers
  - يشتغل على Python 3.14 ✅
  - dim = 1024 (نفس rag_index.faiss) ✅

Reranker: BM25 score fallback (مش محتاج CrossEncoder)
  - لو مفيش torch، بنعتمد على hybrid_score من BM25+FAISS
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional

import numpy as np
import requests

from core.config import CONFIG

logger = logging.getLogger('agri_ai.models')


# =========================================================
# OLLAMA EMBEDDING CLIENT
# =========================================================

def _ollama_embed(texts: List[str], model: str = "bge-m3:latest") -> np.ndarray:
    """
    Call Ollama /api/embed endpoint.
    Returns numpy array shape (len(texts), dim).
    """
    url = f"{CONFIG.ollama_url}/api/embed"
    payload = {"model": model, "input": texts}

    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        embeddings = data.get("embeddings", [])
        if not embeddings:
            raise ValueError("Ollama returned empty embeddings")
        arr = np.array(embeddings, dtype=np.float32)
        # L2 normalize
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return arr / norms
    except Exception as e:
        logger.error("Ollama embed error: %s", e)
        raise


class _Models:
    _embed_model: str = "bge-m3:latest"
    _embed_dim: Optional[int] = None
    _use_ollama: bool = True

    # ── Embedding ────────────────────────────────────────────────────

    @classmethod
    def _check_ollama_embed(cls) -> bool:
        """تحقق إن bge-m3 شغّال في Ollama."""
        try:
            test = _ollama_embed(["test"], model=cls._embed_model)
            cls._embed_dim = test.shape[1]
            logger.info("Ollama embed ready: model=%s dim=%d",
                        cls._embed_model, cls._embed_dim)
            return True
        except Exception as e:
            logger.warning("Ollama embed not available: %s", e)
            return False

    @classmethod
    def embed_query(cls, text: str) -> np.ndarray:
        """Encode single query → shape (1, dim)."""
        return _ollama_embed([text], model=cls._embed_model)

    @classmethod
    def embed_docs(cls, texts: List[str]) -> np.ndarray:
        """
        Encode list of texts in batches → shape (N, dim).
        Ollama /api/embed قادر يأخذ batch مباشرةً.
        """
        if not texts:
            return np.zeros((0, 1024), dtype=np.float32)

        all_embs = []
        batch_size = CONFIG.embed_batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                embs = _ollama_embed(batch, model=cls._embed_model)
                all_embs.append(embs)
            except Exception as e:
                logger.error("Embed batch %d failed: %s", i, e)
                # fallback: zeros
                dim = cls._embed_dim or 1024
                all_embs.append(np.zeros((len(batch), dim), dtype=np.float32))

        return np.vstack(all_embs).astype(np.float32)

    @classmethod
    def embed(cls):
        """Compatibility shim — returns cls itself (not a model object)."""
        return cls

    @classmethod
    def reranker(cls):
        """
        No torch → reranker disabled.
        hybrid_retriever سيستخدم hybrid_score مباشرةً.
        """
        return None

    @classmethod
    def unload(cls) -> None:
        """No-op — Ollama manages its own memory."""
        pass

    @classmethod
    def vram_usage(cls) -> Optional[float]:
        return None

    @classmethod
    def warmup(cls) -> bool:
        """Test embed connection at startup."""
        return cls._check_ollama_embed()


Models = _Models()
