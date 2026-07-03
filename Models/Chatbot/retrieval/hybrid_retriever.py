"""
retrieval/hybrid_retriever.py — v8 Full Hybrid Retrieval Pipeline.

Retrieval stack:
  1. BM25 (sparse)              — Arabic token matching
  2. FAISS + bge-m3 (dense)     — semantic vector search
  3. Reciprocal Rank Fusion      — merge ranked lists
  4. Multi-Query Retrieval       — multiple query variants
  5. Query Rewriting             — LLM-based query improvement
  6. HyDE                        — hypothetical document embeddings
  7. Parent Document Retrieval   — retrieve child, expand to parent
  8. Metadata Filtering          — crop/season/source filters
  9. Context Compression         — LLM-based relevance compression
  10. Self-RAG                   — adaptive re-retrieval if conf low
  11. CrossEncoder Reranking     — bge-reranker-v2-m3

New in v8 vs v7:
  • Parent-Document Retrieval  (new)
  • Metadata filtering         (new)
  • Self-RAG loop              (new)
  • Context compression via LLM (new)
  • bge-m3 query/passage prefixes (improved from e5-large)
  • Tiered fetch: 40 → rerank 20 → final 6 (wider funnel)
"""
from __future__ import annotations

import logging
import pickle
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import faiss
from rank_bm25 import BM25Okapi

from core.config import CONFIG
from utils.text import (
    clean_text, compress_context, normalize_ar,
    norm_dense, norm_sparse, sanitize_chunk, sigmoid,
    text_hash, chunk_list,
)
from utils.models import Models
from utils.ollama import ollama_call
from ontology.agri_ontology import expand_query

logger = logging.getLogger('agri_ai.retrieval')


# =========================================================
# REWRITE SYSTEM PROMPT
# =========================================================

_REWRITE_SYSTEM = """\
أنت متخصص في صياغة استعلامات البحث الزراعي.
أعد كتابة السؤال بصورة أكثر وضوحاً وتحديداً للبحث في قاعدة بيانات زراعية عربية.
ركّز على المحصول + المشكلة + المنطقة إن وُجدت.
أجب بجملة بحثية واحدة فقط بدون شرح أو نقطة في النهاية.
""".strip()

_HYDE_SYSTEM = """\
أنت خبير زراعي متخصص في الزراعة المصرية.
اكتب فقرة قصيرة (3-4 جمل) تصف الإجابة المحتملة للسؤال الزراعي التالي.
اكتب كأنها مقتطف من كتاب زراعي متخصص أو نشرة إرشادية مصرية.
لا تضف مقدمة أو تعليق.
""".strip()

_COMPRESS_SYSTEM = """\
أنت خبير زراعي. المهمة: فلترة النص التالي واحتفظ فقط بالجمل والمعلومات ذات الصلة بالسؤال.
احذف المعلومات غير المتعلقة بالسؤال.
لا تضف أي معلومات من عندك.
أجب بالعربية بنفس لغة النص.
""".strip()


# =========================================================
# QUERY REWRITING
# =========================================================

def rewrite_query(query: str) -> str:
    """Rewrite query for better agricultural search precision."""
    result = ollama_call(
        f'أعد صياغة هذا السؤال للبحث الزراعي:\n{query}',
        system=_REWRITE_SYSTEM,
        model=CONFIG.model_fast,
        timeout=20,
    )
    rewritten = result.strip()
    # Sanity check: if rewritten is too different or too short, use original
    if len(rewritten) < 5 or len(rewritten) > len(query) * 3:
        return query
    return rewritten


# =========================================================
# HyDE
# =========================================================

def generate_hyde(query: str) -> str:
    """Generate hypothetical document for dense retrieval."""
    result = ollama_call(
        query,
        system=_HYDE_SYSTEM,
        model=CONFIG.model_fast,
        timeout=25,
    )
    return result.strip()


# =========================================================
# RRF FUSION
# =========================================================

def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict]],
    k: int = CONFIG.rrf_k,
) -> List[Dict]:
    """
    Reciprocal Rank Fusion over multiple ranked lists.
    Identifies documents by text hash.
    Returns merged list sorted by RRF score desc.
    """
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict] = {}

    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked, start=1):
            h = text_hash(doc['text'])
            scores[h]  = scores.get(h, 0.0) + 1.0 / (k + rank)
            doc_map[h] = doc

    fused = sorted(doc_map.keys(), key=lambda h: scores[h], reverse=True)
    result = []
    for h in fused:
        d = dict(doc_map[h])
        d['rrf_score'] = scores[h]
        result.append(d)
    return result


# =========================================================
# HYBRID RETRIEVER
# =========================================================

class HybridRetriever:

    def __init__(
        self,
        index: Optional[faiss.Index],
        chunks: List[Dict[str, Any]],
        parent_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.index         = index
        self.chunks        = chunks
        self.parent_chunks = parent_chunks or []
        self.bm25          = self._build_bm25()
        # Build parent lookup: child_id → parent doc
        self._parent_map   = self._build_parent_map()
        logger.info(
            'HybridRetriever: %d chunks, %d parents, bm25=%s, faiss=%s',
            len(chunks), len(self.parent_chunks),
            'ok', 'ok' if index else 'none',
        )

    def _build_bm25(self) -> BM25Okapi:
        corpus = [normalize_ar(c.get('text', '')).split() for c in self.chunks]
        return BM25Okapi(corpus)

    def _build_parent_map(self) -> Dict[str, Dict]:
        """Build child_id → parent_doc mapping."""
        mapping = {}
        for parent in self.parent_chunks:
            for child_id in parent.get('child_ids', []):
                mapping[str(child_id)] = parent
        return mapping

    # ── Dense retrieval ───────────────────────────────────────────

    def _dense(self, query: str, top_k: int = CONFIG.top_k_fetch) -> List[Dict]:
        if self.index is None or not self.chunks:
            return []
        try:
            emb = Models.embed_query(query).astype(np.float32)
            # embed_query returns shape (1, dim) — FAISS expects (1, dim) ✅
            if emb.ndim == 1:
                emb = emb.reshape(1, -1)
            scores, indices = self.index.search(emb, min(top_k, len(self.chunks)))
        except Exception as e:
            logger.warning('Dense retrieval failed: %s — skipping', e)
            return []
        results = []
        for raw_s, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            text = sanitize_chunk(clean_text(self.chunks[idx]['text']))
            if not text:
                continue
            results.append({
                'text':         text,
                'dense_score':  norm_dense(float(raw_s)),
                'sparse_score': 0.0,
                'source':       self.chunks[idx].get('source', ''),
                'metadata':     self.chunks[idx].get('metadata', {}),
                'chunk_id':     str(idx),
            })
        return results

    # ── Sparse retrieval ──────────────────────────────────────────

    def _sparse(self, query: str, top_k: int = CONFIG.top_k_fetch) -> List[Dict]:
        if not self.chunks:
            return []
        tokens = normalize_ar(query).split()
        scores = self.bm25.get_scores(tokens)
        top_idx = np.argsort(scores)[::-1][:top_k]
        results = []
        for i in top_idx:
            if scores[i] <= 0:
                continue
            text = sanitize_chunk(clean_text(self.chunks[i]['text']))
            if not text:
                continue
            results.append({
                'text':         text,
                'dense_score':  0.0,
                'sparse_score': norm_sparse(float(scores[i])),
                'source':       self.chunks[i].get('source', ''),
                'metadata':     self.chunks[i].get('metadata', {}),
                'chunk_id':     str(i),
            })
        return results

    # ── Score fusion ──────────────────────────────────────────────

    @staticmethod
    def _fuse(dense_docs: List[Dict], sparse_docs: List[Dict]) -> List[Dict]:
        """Merge results, take max scores, compute hybrid_score."""
        merged: Dict[str, Dict] = {}
        for d in dense_docs + sparse_docs:
            h = text_hash(d['text'])
            if h in merged:
                merged[h]['dense_score']  = max(merged[h]['dense_score'],  d['dense_score'])
                merged[h]['sparse_score'] = max(merged[h]['sparse_score'], d['sparse_score'])
            else:
                merged[h] = dict(d)
        for d in merged.values():
            d['hybrid_score'] = (
                CONFIG.dense_weight  * d['dense_score'] +
                CONFIG.sparse_weight * d['sparse_score']
            )
        return sorted(merged.values(), key=lambda x: x['hybrid_score'], reverse=True)

    # ── Metadata filtering ────────────────────────────────────────

    def _apply_filters(
        self,
        docs: List[Dict],
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict]:
        """
        Filter docs by metadata. If fewer than 3 docs match,
        fall back to unfiltered (avoid empty results).
        """
        if not filters:
            return docs

        filtered = []
        for doc in docs:
            meta = doc.get('metadata', {})
            match = all(
                meta.get(k) == v
                for k, v in filters.items()
                if v is not None
            )
            if match:
                filtered.append(doc)

        # Safety fallback
        return filtered if len(filtered) >= 3 else docs

    # ── Multi-query retrieval ─────────────────────────────────────

    def _multi_query_retrieve(
        self,
        queries: List[str],
        filters: Optional[Dict] = None,
    ) -> List[Dict]:
        """Run dense+sparse per query, RRF-fuse across all lists."""
        all_ranked: List[List[Dict]] = []
        for q in queries[:8]:   # cap at 8 queries for speed
            dense  = self._dense(q)
            sparse = self._sparse(q)
            fused  = self._fuse(dense, sparse)
            fused  = self._apply_filters(fused, filters)
            if fused:
                all_ranked.append(fused)
        if not all_ranked:
            return []
        return reciprocal_rank_fusion(all_ranked)

    # ── Parent Document Retrieval ─────────────────────────────────

    def _expand_to_parents(self, docs: List[Dict]) -> List[Dict]:
        """
        For each retrieved child doc, try to find its parent document
        and append it to context (provides wider context).
        Returns additional parent docs (deduped).
        """
        parent_docs = []
        seen_parents = set()
        for doc in docs[:CONFIG.top_k_parent]:
            child_id = doc.get('chunk_id', '')
            parent   = self._parent_map.get(child_id)
            if parent and id(parent) not in seen_parents:
                seen_parents.add(id(parent))
                parent_text = sanitize_chunk(clean_text(parent.get('text', '')))
                if parent_text:
                    parent_docs.append({
                        'text':         parent_text,
                        'dense_score':  doc['dense_score'],
                        'sparse_score': doc['sparse_score'],
                        'hybrid_score': doc.get('hybrid_score', 0.0) * 0.9,
                        'source':       parent.get('source', doc.get('source', '')),
                        'metadata':     parent.get('metadata', {}),
                        'is_parent':    True,
                    })
        return parent_docs

    # ── Reranker ──────────────────────────────────────────────────

    def _rerank(self, query: str, docs: List[Dict]) -> List[Dict]:
        reranker   = Models.reranker()
        candidates = docs[:CONFIG.top_k_rerank]
        rest       = docs[CONFIG.top_k_rerank:]

        if reranker is None:
            for d in docs:
                d['rerank_score'] = d.get('hybrid_score', d.get('rrf_score', 0.0))
            return sorted(docs, key=lambda x: x['rerank_score'], reverse=True)

        pairs = [[query, d['text'][:512]] for d in candidates]
        try:
            t0 = time.perf_counter()
            scores: List[float] = []
            for batch in chunk_list(pairs, CONFIG.reranker_batch_size):
                scores.extend(reranker.predict(batch))
            elapsed = time.perf_counter() - t0

            if elapsed > CONFIG.reranker_timeout:
                logger.warning('Reranker soft timeout %.1fs — using hybrid_score', elapsed)
                for d in candidates:
                    d['rerank_score'] = d.get('hybrid_score', 0.0)
            else:
                for d, s in zip(candidates, scores):
                    d['rerank_score'] = float(s)

        except Exception as e:
            logger.warning('Reranker failed: %s — falling back to hybrid_score', e)
            for d in candidates:
                d['rerank_score'] = d.get('hybrid_score', 0.0)

        for d in rest:
            d['rerank_score'] = d.get('hybrid_score', d.get('rrf_score', 0.0))

        return sorted(candidates + rest, key=lambda x: x['rerank_score'], reverse=True)

    # ── LLM Context Compression ───────────────────────────────────

    def _compress_with_llm(self, query: str, context: str) -> str:
        """Use small LLM to compress context to most relevant sentences."""
        if len(context) < 800:
            return context   # no need to compress short contexts

        prompt = (
            f'السؤال:\n{query}\n\n'
            f'النص للفلترة:\n{context[:2000]}\n\n'
            'احذف الجمل غير ذات الصلة وأبقِ فقط المفيد.'
        )
        compressed = ollama_call(
            prompt,
            system=_COMPRESS_SYSTEM,
            model=CONFIG.model_fast,
            timeout=25,
        )
        # Fallback if LLM returns garbage
        if len(compressed.strip()) < 50:
            return context[:2000]
        return compressed.strip()

    # ── Self-RAG ──────────────────────────────────────────────────

    def _self_rag_retrieve(
        self,
        query: str,
        rewritten_query: str,
        hyde_doc: str,
        filters: Optional[Dict],
        iteration: int = 0,
    ) -> Tuple[List[Dict], float]:
        """
        Self-RAG: if first retrieval confidence is low,
        reformulate and retrieve again with a broader query.
        """
        queries = expand_query(query)
        if rewritten_query and rewritten_query != query:
            queries.insert(1, rewritten_query)
        if hyde_doc:
            queries.append(hyde_doc)

        docs = self._multi_query_retrieve(queries, filters)
        docs = self._rerank(query, docs)
        final = docs[:CONFIG.top_k_final]
        conf  = sigmoid(final[0]['rerank_score']) if final else 0.0

        if conf < CONFIG.self_rag_threshold and iteration < CONFIG.max_self_rag_iterations:
            logger.info('Self-RAG iter %d: conf=%.3f < %.3f — re-retrieving',
                        iteration + 1, conf, CONFIG.self_rag_threshold)
            # Broaden query: add crop/disease terms from ontology
            broader_query = rewritten_query or query
            return self._self_rag_retrieve(
                broader_query, '', '', None, iteration + 1
            )

        return final, conf

    # ── Public API ────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        rewritten_query: str = '',
        hyde_doc: str = '',
        metadata_filters: Optional[Dict[str, Any]] = None,
        use_parent_docs: bool = True,
        use_llm_compression: bool = False,
        self_rag: bool = True,
    ) -> Tuple[List[Dict], List[Dict], float]:
        """
        Full retrieval pipeline.

        Returns:
            (child_docs, parent_docs, retrieval_confidence)
        """
        if self_rag:
            final, conf = self._self_rag_retrieve(
                query, rewritten_query, hyde_doc, metadata_filters
            )
        else:
            queries = expand_query(query)
            if rewritten_query and rewritten_query != query:
                queries.insert(1, rewritten_query)
            if hyde_doc:
                queries.append(hyde_doc)
            docs  = self._multi_query_retrieve(queries, metadata_filters)
            docs  = self._rerank(query, docs)
            final = docs[:CONFIG.top_k_final]
            conf  = sigmoid(final[0]['rerank_score']) if final else 0.0

        # Parent document expansion
        parent_docs = []
        if use_parent_docs and self.parent_chunks:
            parent_docs = self._expand_to_parents(final)

        logger.debug(
            'Retrieval: conf=%.3f docs=%d parents=%d',
            conf, len(final), len(parent_docs),
        )
        return final, parent_docs, conf

    def build_context(
        self,
        query: str,
        docs: List[Dict],
        parent_docs: List[Dict],
        use_llm_compression: bool = False,
    ) -> str:
        """Build merged context string from child + parent docs."""
        all_docs = docs + parent_docs
        raw = '\n---\n'.join(d['text'] for d in all_docs)

        if use_llm_compression and len(raw) > 1500:
            return self._compress_with_llm(query, raw)

        return compress_context(raw)
