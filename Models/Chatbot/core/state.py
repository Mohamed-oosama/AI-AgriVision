"""
core/state.py — v8 Unified AgentState (46 fields).

New in v8 vs v7:
  • planner_plan          — structured plan from Planner Node
  • verification_result   — structured output from Verifier Node
  • self_rag_iteration    — counter for Self-RAG loop
  • completeness_score    — did context cover the full question?
  • hallucination_flags   — list of flagged claims from Critic
  • query_complexity      — simple | moderate | complex
  • retrieval_strategy    — which strategy was used
  • parent_docs           — parent documents from Parent-Doc retrieval
  • metadata_filters      — active metadata filters
  • answer_verified       — bool: did Verifier approve?
  • critic_notes          — detailed notes from Critic Agent
  • llm_judge_score       — 0–1 score from LLM-as-judge
  • structured_diagnosis  — parsed diagnosis dict (disease/pest/nutrient)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # ── Input ────────────────────────────────────────────────────────
    query:              str
    corrected_query:    str
    rewritten_query:    str         # after query rewriting
    hyde_doc:           str         # HyDE hypothetical document
    query_complexity:   str         # simple | moderate | complex
    retrieval_strategy: str         # standard | self_rag | parent_doc

    # ── Planner ──────────────────────────────────────────────────────
    planner_plan:       Dict[str, Any]   # {steps: [...], priority_entity: str}

    # ── Classification ───────────────────────────────────────────────
    query_lang:         str         # english | arabic_formal | arabic_egyptian
    query_type:         str         # DISEASE | NUTRIENT | PEST | IRRIGATION | GENERAL
    detected_crops:     List[str]
    detected_symptoms:  List[str]
    detected_entities:  List[str]   # all graph-matched entities
    intent:             str         # diagnose | advise | explain | compare | clarify
    metadata_filters:   Dict[str, Any]  # {crop: ..., season: ...}

    # ── Retrieval ────────────────────────────────────────────────────
    retrieved_docs:     List[Dict[str, Any]]   # child docs with scores
    parent_docs:        List[Dict[str, Any]]   # expanded parent docs
    vector_context:     str
    graph_context:      str
    graph_paths:        List[str]              # multi-hop reasoning paths
    self_rag_iteration: int                    # 0, 1, 2 ...

    # ── Confidence ───────────────────────────────────────────────────
    confidence:              float
    confidence_breakdown:    Dict[str, float]
    confidence_explanation:  str
    completeness_score:      float   # 0–1: did context answer the full question?

    # ── Reflection / Verification ────────────────────────────────────
    reflection_notes:    str
    needs_clarification: bool
    clarifying_question: str
    reflection_round:    int
    answer_verified:     bool
    critic_notes:        str
    hallucination_flags: List[str]   # list of suspicious claims
    llm_judge_score:     float       # 0–1

    # ── Verification ─────────────────────────────────────────────────
    verification_result: Dict[str, Any]   # {passed: bool, issues: [...]}

    # ── Memory ───────────────────────────────────────────────────────
    memory_context:      str

    # ── Output ───────────────────────────────────────────────────────
    final_answer:        str
    answer_sources:      List[str]
    structured_diagnosis: Dict[str, Any]   # {disease, cause, treatment, prevention}
    answer_language:     str               # language of final answer

    # ── Routing / Control ────────────────────────────────────────────
    agent_path:          List[str]    # breadcrumb of visited nodes
    error:               Optional[str]
    retry_count:         int
    skipped_nodes:       List[str]    # nodes skipped due to confidence shortcuts
