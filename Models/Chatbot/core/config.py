"""
core/config.py — v8 Configuration.

Hardware target: RTX 4050 Laptop 6GB VRAM, 16-32GB RAM.

النماذج المثبتة فعلاً على الجهاز:
  model_main  = qwen3:8b      (الاجابات الرئيسية - 5.2 GB)
  model_fast  = qwen2.5:3b   (spell/rewrite/hyde/json - 1.9 GB سريع)
  model_deep  = qwen3.5:9b   (reflection/critic - 6.6 GB اعمق)
  embed_model = BAAI/bge-m3  (dim=1024 يتوافق مع rag_index.faiss)
  reranker    = BAAI/bge-reranker-v2-m3
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    # ── Ollama ──────────────────────────────────────────────────────────
    ollama_url: str              = os.getenv("OLLAMA_URL",   "http://localhost:11434")
    model_main: str              = os.getenv("MODEL_MAIN",   "qwen3:8b")    # الاجابات الرئيسية
    model_fast: str              = os.getenv("MODEL_FAST",   "qwen2.5:3b")  # سريع للمهام الصغيرة
    model_deep: str              = os.getenv("MODEL_DEEP",   "qwen3.5:9b")  # reflection/critic
    ollama_timeout: int          = int(os.getenv("OLLAMA_TIMEOUT",  "300"))
    ollama_temperature: float    = float(os.getenv("OLLAMA_TEMP",   "0.1"))
    ollama_top_p: float          = float(os.getenv("OLLAMA_TOP_P",  "0.9"))
    ollama_repeat_penalty: float = float(os.getenv("OLLAMA_REP_PEN","1.1"))
    ollama_num_ctx: int          = int(os.getenv("OLLAMA_CTX",      "4096"))

    # ── Embedding — BAAI/bge-m3 ─────────────────────────────────────────
    # dim=1024 — يتوافق مع rag_index.faiss الموجود (28,613 vectors)
    embed_model: str             = os.getenv("EMBED_MODEL",  "BAAI/bge-m3")
    embed_batch_size: int        = int(os.getenv("EMBED_BATCH", "16"))
    embed_device: str            = os.getenv("EMBED_DEVICE",    "cuda")

    # ── Reranker — bge-reranker-v2-m3 ───────────────────────────────────
    reranker_model: str          = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    reranker_batch_size: int     = int(os.getenv("RERANKER_BATCH",    "4"))
    reranker_timeout: float      = float(os.getenv("RERANKER_TIMEOUT", "15.0"))
    reranker_device: str         = os.getenv("RERANKER_DEVICE", "cuda")

    # ── Files (اسماء الملفات الفعلية) ───────────────────────────────────
    index_file: str              = os.getenv("INDEX_FILE",        "rag_index.faiss")
    chunks_file: str             = os.getenv("CHUNKS_FILE",       "rag_chunks.pkl")
    parent_chunks_file: str      = os.getenv("PARENT_FILE",       "rag_parent_chunks.pkl")
    raw_data_file: str           = os.getenv("RAW_DATA_FILE",     "s5_final.json")
    graph_file: str              = os.getenv("GRAPH_FILE",        "knowledge_graph.json")
    graph_extra_file: str        = os.getenv("GRAPH_EXTRA_FILE",  "graph_data.json")
    graph_merged_file: str       = os.getenv("GRAPH_MERGED_FILE", "knowledge_graph_merged.json")
    embeddings_file: str         = os.getenv("EMBEDDINGS_FILE",   "all_embeddings.npy")
    cache_dir: str               = os.getenv("CACHE_DIR",         ".cache")
    log_file: str                = os.getenv("LOG_FILE",          "agri_ai.log")

    # ── Retrieval ────────────────────────────────────────────────────────
    top_k_fetch: int             = int(os.getenv("TOP_K_FETCH",    "40"))
    top_k_rerank: int            = int(os.getenv("TOP_K_RERANK",   "20"))
    top_k_final: int             = int(os.getenv("TOP_K_FINAL",    "6"))
    top_k_parent: int            = int(os.getenv("TOP_K_PARENT",   "3"))
    dense_weight: float          = float(os.getenv("DENSE_WEIGHT", "0.65"))
    sparse_weight: float         = float(os.getenv("SPARSE_WEIGHT","0.35"))
    bm25_norm: float             = float(os.getenv("BM25_NORM",    "15.0"))
    rrf_k: int                   = int(os.getenv("RRF_K",          "60"))
    parent_chunk_size: int       = int(os.getenv("PARENT_CHUNK",   "1024"))
    child_chunk_size: int        = int(os.getenv("CHILD_CHUNK",    "256"))
    self_rag_threshold: float    = float(os.getenv("SELF_RAG_THRESH","0.35"))
    max_context_chars: int       = int(os.getenv("MAX_CTX_CHARS",  "3000"))
    min_line_length: int         = 20
    max_context_lines: int       = 18

    # ── Confidence ───────────────────────────────────────────────────────
    min_confidence: float        = float(os.getenv("MIN_CONFIDENCE","0.25"))  # كان 0.40
    completeness_threshold: float= float(os.getenv("COMPLETE_THRESH","0.30"))  # كان 0.55
    confidence_weights: dict     = field(default_factory=lambda: {
        "retrieval":   0.30,
        "reranker":    0.25,
        "graph":       0.20,
        "entity":      0.15,
        "consistency": 0.10,
    })

    # ── Graph ────────────────────────────────────────────────────────────
    graph_relevance_threshold: int  = int(os.getenv("GRAPH_RELEVANCE","50"))
    graph_max_hops: int             = int(os.getenv("GRAPH_MAX_HOPS", "4"))
    graph_max_facts: int            = int(os.getenv("GRAPH_MAX_FACTS","20"))
    graph_path_min_score: float     = float(os.getenv("GRAPH_MIN_SCORE","0.3"))

    # ── Memory ───────────────────────────────────────────────────────────
    memory_summarize_every: int  = int(os.getenv("MEM_SUMMARIZE_EVERY","4"))
    memory_max_raw: int          = int(os.getenv("MEM_MAX_RAW",        "8"))
    memory_max_summary_len: int  = int(os.getenv("MEM_MAX_SUMMARY",    "400"))
    semantic_cache_ttl: int      = int(os.getenv("SEMANTIC_CACHE_TTL", "3600"))

    # ── Agentic ──────────────────────────────────────────────────────────
    max_reflection_rounds: int   = int(os.getenv("MAX_REFLECTION", "2"))
    max_retries: int             = int(os.getenv("MAX_RETRIES",    "3"))
    max_self_rag_iterations: int = int(os.getenv("MAX_SELF_RAG",   "2"))

    # ── Caching ──────────────────────────────────────────────────────────
    redis_url: str               = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    use_redis: bool              = os.getenv("USE_REDIS", "false").lower() == "true"
    response_cache_ttl: int      = int(os.getenv("CACHE_TTL", "1800"))

    # ── Prompt injection guard ────────────────────────────────────────────
    injection_patterns: List[str] = field(default_factory=lambda: [
        r'ignore\s+(previous|all|prior)\s+instructions?',
        r'system\s+prompt',
        r'you\s+are\s+now',
        r'act\s+as\s+if',
        r'disregard\s+(your|all)',
        r'تجاهل\s+التعليمات',
        r'تصرف\s+كـ?أنك',
        r'<\|.*?\|>',
        r'\\n\\n###\s+New\s+instructions',
    ])

    # ── Streaming ────────────────────────────────────────────────────────
    stream_chunk_size: int       = int(os.getenv("STREAM_CHUNK", "20"))

    # ── Metrics ──────────────────────────────────────────────────────────
    metrics_port: int            = int(os.getenv("METRICS_PORT", "9090"))
    enable_metrics: bool         = os.getenv("ENABLE_METRICS", "false").lower() == "true"


CONFIG = Config()
