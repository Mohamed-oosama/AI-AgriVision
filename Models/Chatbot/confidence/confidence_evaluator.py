"""
confidence/confidence_evaluator.py — v8 Multi-component Confidence Scoring.

Components (5):
  1. retrieval_confidence  — reranker sigmoid score
  2. reranker_confidence   — normalized cross-encoder score
  3. graph_confidence      — evidence quality from graph
  4. entity_confidence     — entity coverage in context
  5. consistency_score     — retrieval ∩ graph agreement

New in v8:
  • completeness_score     — did context cover all question aspects?
  • llm_judge()            — optional LLM-as-judge for final answer
  • calibrated_weights     — adjusted for Arabic agricultural domain
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Tuple

from core.config import CONFIG
from utils.text import normalize_ar, sigmoid
from utils.ollama import ollama_json
from rapidfuzz import fuzz

logger = logging.getLogger('agri_ai.confidence')

# ── Thresholds ────────────────────────────────────────────
_LEVELS = {
    (0.85, 1.01): ('عالية جداً ✅', '✅'),
    (0.65, 0.85): ('عالية ✅',      '✅'),
    (0.45, 0.65): ('متوسطة ⚠️',    '⚠️'),
    (0.00, 0.45): ('منخفضة ❌',     '❌'),
}

_JUDGE_SYSTEM = """\
أنت محكّم زراعي متخصص. قيّم جودة الإجابة من 0.0 إلى 1.0 بناءً على:
1. هل الإجابة مستندة للسياق المُقدم؟
2. هل تُجيب فعلاً على السؤال؟
3. هل تخلو من ادعاءات غير مدعومة؟
أجب بـ JSON فقط: {"score": 0.0-1.0, "reason": "سبب قصير"}
""".strip()


def _entity_confidence(entities: List[str], context: str) -> float:
    if not entities:
        return 0.3
    norm_ctx = normalize_ar(context)
    found = sum(
        1 for e in entities
        if fuzz.partial_ratio(normalize_ar(e), norm_ctx) > 65
    )
    return min(found / len(entities), 1.0)


def _consistency_score(vector_context: str, graph_context: str) -> float:
    if not graph_context or not vector_context:
        return 0.5
    vec_words   = set(normalize_ar(vector_context).split())
    graph_words = set(normalize_ar(graph_context).split())
    sig_vec     = {w for w in vec_words   if len(w) > 3}
    sig_graph   = {w for w in graph_words if len(w) > 3}
    if not sig_graph:
        return 0.5
    overlap = len(sig_vec & sig_graph)
    return min(overlap / len(sig_graph), 1.0)


def _completeness_score(query: str, context: str) -> float:
    """
    Estimate how well the context covers the question aspects.
    Uses keyword overlap between query and context.
    """
    q_words   = set(normalize_ar(query).split())
    ctx_words = set(normalize_ar(context).split())
    sig_q     = {w for w in q_words if len(w) > 3}
    if not sig_q:
        return 0.5
    covered = len(sig_q & ctx_words)
    return min(covered / len(sig_q), 1.0)


class ConfidenceEvaluator:

    def evaluate(
        self,
        retrieval_conf: float,
        graph_conf: float,
        entities: List[str],
        vector_context: str,
        graph_context: str,
        query: str = '',
    ) -> Tuple[float, Dict[str, float], str]:
        w = CONFIG.confidence_weights

        entity_conf  = _entity_confidence(entities, vector_context)
        consistency  = _consistency_score(vector_context, graph_context)
        completeness = _completeness_score(query, vector_context) if query else 0.5

        # Reranker conf = same source as retrieval (normalized differently)
        reranker_conf = min(retrieval_conf * 1.1, 1.0)

        breakdown = {
            'retrieval':   round(retrieval_conf,  3),
            'reranker':    round(reranker_conf,   3),
            'graph':       round(graph_conf,      3),
            'entity':      round(entity_conf,     3),
            'consistency': round(consistency,     3),
            'completeness': round(completeness,   3),
        }

        final = (
            w['retrieval']   * retrieval_conf  +
            w['reranker']    * reranker_conf   +
            w['graph']       * graph_conf      +
            w['entity']      * entity_conf     +
            w['consistency'] * consistency
        )
        final = round(min(final, 1.0), 3)

        # Label
        label = 'منخفضة ❌'
        for (lo, hi), (lbl, _) in _LEVELS.items():
            if lo <= final < hi:
                label = lbl
                break

        explanation = (
            f'الثقة الكلية: {final:.0%} ({label}) | '
            f'استرجاع: {retrieval_conf:.0%} | '
            f'جراف: {graph_conf:.0%} | '
            f'كيانات: {entity_conf:.0%} | '
            f'اكتمال: {completeness:.0%} | '
            f'اتساق: {consistency:.0%}'
        )

        logger.debug('Confidence: %s', explanation)
        return final, breakdown, explanation

    def llm_judge(
        self,
        question: str,
        answer: str,
        context: str,
        model: str = CONFIG.model_fast,
    ) -> float:
        """
        Use small LLM as judge to score answer quality.
        Returns 0–1 float. Falls back to 0.5 on error.
        """
        prompt = (
            f'السؤال: {question}\n\n'
            f'السياق:\n{context[:800]}\n\n'
            f'الإجابة:\n{answer[:600]}'
        )
        try:
            result = ollama_json(prompt, system=_JUDGE_SYSTEM, model=model)
            score  = float(result.get('score', 0.5))
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.debug('LLM judge failed: %s', e)
            return 0.5
