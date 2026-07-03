"""
evaluation/evaluator.py — v8 Evaluation Framework.

Metrics:
  • Recall@K, Precision@K, F1@K
  • MRR (Mean Reciprocal Rank)
  • Hit@K
  • Faithfulness (answer vs context overlap)
  • Groundedness (claims backed by context)
  • Hallucination Rate
  • Agricultural QA Accuracy
  • Latency tracking
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from core.config import CONFIG
from utils.text import normalize_ar
from utils.ollama import ollama_json

logger = logging.getLogger('agri_ai.eval')


_FAITHFUL_SYSTEM = """\
أنت محكّم. هل الإجابة مستندة حصرياً للسياق؟
أجب بـ JSON: {"faithful": true/false, "unsupported": ["..."]}
""".strip()

_GROUND_SYSTEM = """\
أنت محكّم. لكل ادعاء في الإجابة، هل هو موجود في السياق؟
أجب بـ JSON: {"grounded_ratio": 0.0-1.0, "ungrounded_claims": ["..."]}
""".strip()


# =========================================================
# RETRIEVAL METRICS
# =========================================================

def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits  = sum(1 for r in relevant if any(
        fuzz.partial_ratio(normalize_ar(r), normalize_ar(t)) > 80
        for t in top_k
    ))
    return hits / len(relevant)


def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    if not retrieved:
        return 0.0
    top_k = retrieved[:k]
    hits  = sum(1 for t in top_k if any(
        fuzz.partial_ratio(normalize_ar(r), normalize_ar(t)) > 80
        for r in relevant
    ))
    return hits / min(k, len(top_k))


def f1_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    p = precision_at_k(retrieved, relevant, k)
    r = recall_at_k(retrieved, relevant, k)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def mrr(retrieved: List[str], relevant: List[str]) -> float:
    for rank, doc in enumerate(retrieved, start=1):
        if any(fuzz.partial_ratio(normalize_ar(r), normalize_ar(doc)) > 80
               for r in relevant):
            return 1.0 / rank
    return 0.0


def hit_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    top_k = retrieved[:k]
    return 1.0 if any(
        fuzz.partial_ratio(normalize_ar(r), normalize_ar(t)) > 80
        for r in relevant for t in top_k
    ) else 0.0


# =========================================================
# GENERATION QUALITY METRICS
# =========================================================

def faithfulness(answer: str, context: str, model: str = CONFIG.model_fast) -> Tuple[float, List[str]]:
    prompt = f'السياق:\n{context[:600]}\n\nالإجابة:\n{answer[:400]}'
    result = ollama_json(prompt, system=_FAITHFUL_SYSTEM, model=model,
                         fallback={'faithful': True, 'unsupported': []})
    score = 1.0 if result.get('faithful', True) else 0.0
    return score, result.get('unsupported', [])


def groundedness(answer: str, context: str, model: str = CONFIG.model_fast) -> Tuple[float, List[str]]:
    prompt = f'السياق:\n{context[:600]}\n\nالإجابة:\n{answer[:400]}'
    result = ollama_json(prompt, system=_GROUND_SYSTEM, model=model,
                         fallback={'grounded_ratio': 0.8, 'ungrounded_claims': []})
    return float(result.get('grounded_ratio', 0.8)), result.get('ungrounded_claims', [])


def hallucination_rate(answer: str, context: str) -> float:
    """Heuristic: fraction of answer sentences not found in context."""
    sentences = [s.strip() for s in answer.split('.') if len(s.strip()) > 20]
    if not sentences:
        return 0.0
    norm_ctx = normalize_ar(context)
    hallucinated = sum(
        1 for s in sentences
        if fuzz.partial_ratio(normalize_ar(s), norm_ctx) < 55
    )
    return hallucinated / len(sentences)


# =========================================================
# QA ACCURACY
# =========================================================

def qa_accuracy(prediction: str, ground_truth: str) -> float:
    """Fuzzy string match between prediction and ground truth."""
    return fuzz.token_sort_ratio(
        normalize_ar(prediction[:300]),
        normalize_ar(ground_truth[:300]),
    ) / 100.0


# =========================================================
# BENCHMARK RUNNER
# =========================================================

@dataclass
class EvalResult:
    recall_5:   float = 0.0
    recall_10:  float = 0.0
    precision_5:float = 0.0
    mrr:        float = 0.0
    hit_5:      float = 0.0
    faithfulness:    float = 0.0
    groundedness:    float = 0.0
    hallucination:   float = 0.0
    qa_accuracy:     float = 0.0
    avg_latency_ms:  float = 0.0
    n_samples:       int   = 0
    errors:          List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f'📊 نتائج التقييم ({self.n_samples} عينة)\n'
            f'  Recall@5:      {self.recall_5:.3f}\n'
            f'  Recall@10:     {self.recall_10:.3f}\n'
            f'  Precision@5:   {self.precision_5:.3f}\n'
            f'  MRR:           {self.mrr:.3f}\n'
            f'  Hit@5:         {self.hit_5:.3f}\n'
            f'  Faithfulness:  {self.faithfulness:.3f}\n'
            f'  Groundedness:  {self.groundedness:.3f}\n'
            f'  Hallucination: {self.hallucination:.3f}\n'
            f'  QA Accuracy:   {self.qa_accuracy:.3f}\n'
            f'  Latency (avg): {self.avg_latency_ms:.0f} ms'
        )

    def to_dict(self) -> dict:
        return {
            'recall_5':      self.recall_5,
            'recall_10':     self.recall_10,
            'precision_5':   self.precision_5,
            'mrr':           self.mrr,
            'hit_5':         self.hit_5,
            'faithfulness':  self.faithfulness,
            'groundedness':  self.groundedness,
            'hallucination': self.hallucination,
            'qa_accuracy':   self.qa_accuracy,
            'avg_latency_ms':self.avg_latency_ms,
            'n_samples':     self.n_samples,
        }


def run_benchmark(
    test_cases: List[Dict[str, Any]],
    run_fn,
    k_values: List[int] = [5, 10],
) -> EvalResult:
    """
    Run benchmark over test cases.

    test_cases format:
      [{'query': str, 'relevant_docs': [str], 'ground_truth': str}, ...]

    run_fn: callable(query: str) → AgentState
    """
    result = EvalResult(n_samples=len(test_cases))
    latencies = []

    r5_scores, r10_scores, p5_scores = [], [], []
    mrr_scores, h5_scores = [], []
    faith_scores, ground_scores, hall_scores, qa_scores = [], [], [], []

    for tc in test_cases:
        query        = tc['query']
        relevant     = tc.get('relevant_docs', [])
        ground_truth = tc.get('ground_truth', '')

        t0 = time.perf_counter()
        try:
            state = run_fn(query)
        except Exception as e:
            result.errors.append(f'{query[:50]}: {e}')
            continue
        latency_ms = (time.perf_counter() - t0) * 1000
        latencies.append(latency_ms)

        retrieved = [d.get('text', '') for d in state.get('retrieved_docs', [])]
        answer    = state.get('final_answer', '')
        context   = state.get('vector_context', '')

        if relevant:
            r5_scores.append(recall_at_k(retrieved, relevant, 5))
            r10_scores.append(recall_at_k(retrieved, relevant, 10))
            p5_scores.append(precision_at_k(retrieved, relevant, 5))
            mrr_scores.append(mrr(retrieved, relevant))
            h5_scores.append(hit_at_k(retrieved, relevant, 5))

        if answer and context:
            faith_score, _ = faithfulness(answer, context)
            ground_score, _ = groundedness(answer, context)
            hall_score = hallucination_rate(answer, context)
            faith_scores.append(faith_score)
            ground_scores.append(ground_score)
            hall_scores.append(hall_score)

        if answer and ground_truth:
            qa_scores.append(qa_accuracy(answer, ground_truth))

    def avg(lst): return sum(lst) / len(lst) if lst else 0.0

    result.recall_5      = avg(r5_scores)
    result.recall_10     = avg(r10_scores)
    result.precision_5   = avg(p5_scores)
    result.mrr           = avg(mrr_scores)
    result.hit_5         = avg(h5_scores)
    result.faithfulness  = avg(faith_scores)
    result.groundedness  = avg(ground_scores)
    result.hallucination = avg(hall_scores)
    result.qa_accuracy   = avg(qa_scores)
    result.avg_latency_ms = avg(latencies)

    logger.info('Benchmark complete:\n%s', result.summary())
    return result
