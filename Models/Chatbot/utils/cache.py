"""
utils/cache.py — v8 Dual-layer semantic cache.

Layer 1: in-memory LRU dict (always available)
Layer 2: Redis (optional, activated by USE_REDIS=true)

Semantic cache avoids re-running the full pipeline for near-duplicate queries.
Similarity threshold: 0.92 cosine (tight — agricultural queries need precision).
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any, Optional

import numpy as np

from core.config import CONFIG

logger = logging.getLogger('agri_ai.cache')


# =========================================================
# IN-MEMORY LRU CACHE
# =========================================================

class LRUCache:
    def __init__(self, capacity: int = 256):
        self._cache: OrderedDict = OrderedDict()
        self._capacity = capacity

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._capacity:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


_LRU = LRUCache(capacity=512)


# =========================================================
# REDIS CACHE (optional)
# =========================================================

_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None and CONFIG.use_redis:
        try:
            import redis
            _redis_client = redis.from_url(CONFIG.redis_url, decode_responses=True)
            _redis_client.ping()
            logger.info('Redis connected: %s', CONFIG.redis_url)
        except Exception as e:
            logger.warning('Redis unavailable — using in-memory cache only: %s', e)
            _redis_client = None
    return _redis_client


# =========================================================
# EXACT CACHE (hash-based)
# =========================================================

def _query_key(query: str, model: str = '') -> str:
    s = f'{model}:{query.strip().lower()}'
    return hashlib.sha256(s.encode()).hexdigest()


def cache_get(query: str, model: str = '') -> Optional[dict]:
    """Retrieve cached response for exact query match."""
    key = _query_key(query, model)

    # L1: memory
    hit = _LRU.get(key)
    if hit is not None:
        logger.debug('Cache L1 hit: %s…', query[:40])
        return hit

    # L2: redis
    r = _get_redis()
    if r:
        try:
            raw = r.get(f'agri:{key}')
            if raw:
                data = json.loads(raw)
                _LRU.set(key, data)   # promote to L1
                logger.debug('Cache L2 hit: %s…', query[:40])
                return data
        except Exception as e:
            logger.warning('Redis get error: %s', e)

    return None


def cache_set(query: str, value: dict, model: str = '') -> None:
    """Store response in both cache layers."""
    key = _query_key(query, model)

    # L1
    _LRU.set(key, value)

    # L2
    r = _get_redis()
    if r:
        try:
            r.setex(
                f'agri:{key}',
                CONFIG.response_cache_ttl,
                json.dumps(value, ensure_ascii=False),
            )
        except Exception as e:
            logger.warning('Redis set error: %s', e)


# =========================================================
# SEMANTIC CACHE (embedding-based similarity)
# =========================================================

class SemanticCache:
    """
    Cache that matches queries by embedding similarity.
    Only activated when embedding model is already loaded.
    """

    def __init__(self, threshold: float = 0.92, capacity: int = 128):
        self._threshold = threshold
        self._capacity  = capacity
        self._entries: list = []   # [(embedding, query, value, timestamp)]

    def _evict_expired(self) -> None:
        now = time.time()
        self._entries = [
            e for e in self._entries
            if now - e[3] < CONFIG.semantic_cache_ttl
        ]

    def get(self, query: str) -> Optional[dict]:
        self._evict_expired()
        if not self._entries:
            return None
        try:
            from utils.models import Models
            emb = Models.embed_query(query)[0]
            stored_embs = np.array([e[0] for e in self._entries])
            sims = stored_embs @ emb
            best_idx = int(np.argmax(sims))
            if sims[best_idx] >= self._threshold:
                logger.debug('Semantic cache hit (sim=%.3f): %s…',
                             sims[best_idx], query[:40])
                return self._entries[best_idx][2]
        except Exception as e:
            logger.debug('Semantic cache lookup error: %s', e)
        return None

    def set(self, query: str, value: dict) -> None:
        try:
            from utils.models import Models
            emb = Models.embed_query(query)[0]
            self._entries.append((emb, query, value, time.time()))
            if len(self._entries) > self._capacity:
                self._entries.pop(0)
        except Exception:
            pass


SEMANTIC_CACHE = SemanticCache()
