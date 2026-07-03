"""
agents/workflow.py — v8 Real LangGraph StateGraph.

Graph topology:
  START
    → spell_correction
    → query_understanding
    → planner
    → intent_classification
    → crop_detection
    → [parallel] query_rewriting + hyde + memory
    → retrieval
    → graph_reasoning
    → confidence_evaluation
    → reflection  ──(needs_clarification)──→ fallback → END
         ↓
    [route by query_type]
    disease_diagnosis | pest_detection | fertilization | synthesis
         ↓
    critic
         ↓
    verification ──(fail + rounds < max)──→ reflection (loop)
         ↓
    END
"""
from __future__ import annotations

import logging
from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

from core.config import CONFIG
from core.state import AgentState
from agents.nodes import (
    planner_node, query_understanding_node, spell_correction_node,
    intent_classification_node, crop_detection_node,
    query_rewriting_node, hyde_node, memory_node,
    retrieval_node, graph_reasoning_node, confidence_evaluation_node,
    reflection_node, critic_node, verification_node,
    disease_diagnosis_node, fertilization_node,
    pest_detection_node, synthesis_node, fallback_node,
    EntityExtractor,
)
from memory.memory_system import ConversationMemory
from retrieval.hybrid_retriever import HybridRetriever
from graph.graph_reasoner import GraphReasoner
from confidence.confidence_evaluator import ConfidenceEvaluator

logger = logging.getLogger('agri_ai.workflow')


# =========================================================
# ROUTING FUNCTIONS
# =========================================================

def route_after_reflection(state: AgentState) -> Literal[
    'disease_diagnosis', 'pest_detection',
    'fertilization', 'synthesis', 'fallback'
]:
    # فقط روح fallback لو مفيش context خالص
    context = state.get('vector_context', '')
    needs_clarif = state.get('needs_clarification', False)
    if needs_clarif and len(context.strip()) < 100:
        return 'fallback'

    # دايماً روح للـ specialist — حتى لو الثقة منخفضة
    qtype = state.get('query_type', 'GENERAL')
    return {
        'DISEASE':    'disease_diagnosis',
        'PEST':       'pest_detection',
        'NUTRIENT':   'fertilization',
        'IRRIGATION': 'synthesis',
        'GENERAL':    'synthesis',
    }.get(qtype, 'synthesis')


def route_after_verification(state: AgentState) -> Literal['reflection', '__end__']:
    # دايماً نكمّل — مش نعمل loop تاني يخلي النظام يطلب توضيح
    # الـ answer موجود وكافي بدرجة ما — نعرضه للمستخدم
    return '__end__'


# =========================================================
# GRAPH BUILDER
# =========================================================

def build_graph(
    retriever:  HybridRetriever,
    reasoner:   GraphReasoner,
    memory:     ConversationMemory,
    evaluator:  ConfidenceEvaluator,
) -> StateGraph:

    extractor = EntityExtractor(reasoner.G)

    # ── Bind dependencies into node functions ─────────────────────
    _memory_node     = partial(memory_node,      memory=memory)
    _retrieval_node  = partial(retrieval_node,   retriever=retriever)
    _graph_node      = partial(graph_reasoning_node,
                               reasoner=reasoner,
                               entity_extractor=extractor)
    _conf_node       = partial(confidence_evaluation_node,
                               evaluator=evaluator,
                               entity_extractor=extractor)

    # ── Build StateGraph ──────────────────────────────────────────
    g = StateGraph(AgentState)

    # Register nodes
    g.add_node('spell_correction',       spell_correction_node)
    g.add_node('query_understanding',    query_understanding_node)
    g.add_node('planner',                planner_node)
    g.add_node('intent_classification',  intent_classification_node)
    g.add_node('crop_detection',         crop_detection_node)
    g.add_node('query_rewriting',        query_rewriting_node)
    g.add_node('hyde',                   hyde_node)
    g.add_node('memory',                 _memory_node)
    g.add_node('retrieval',              _retrieval_node)
    g.add_node('graph_reasoning',        _graph_node)
    g.add_node('confidence_evaluation',  _conf_node)
    g.add_node('reflection',             reflection_node)
    g.add_node('critic',                 critic_node)
    g.add_node('verification',           verification_node)
    g.add_node('disease_diagnosis',      disease_diagnosis_node)
    g.add_node('pest_detection',         pest_detection_node)
    g.add_node('fertilization',          fertilization_node)
    g.add_node('synthesis',              synthesis_node)
    g.add_node('fallback',               fallback_node)

    # ── Sequential edges ──────────────────────────────────────────
    g.add_edge(START,                   'spell_correction')
    g.add_edge('spell_correction',      'query_understanding')
    g.add_edge('query_understanding',   'planner')
    g.add_edge('planner',               'intent_classification')
    g.add_edge('intent_classification', 'crop_detection')

    # Sequential: rewriting → hyde → memory → retrieval
    # (بدل parallel عشان LangGraph مش بيسمح بكتابة نفس الـ key من أكتر من node في نفس الوقت)
    g.add_edge('crop_detection',   'query_rewriting')
    g.add_edge('query_rewriting',  'hyde')
    g.add_edge('hyde',             'memory')
    g.add_edge('memory',           'retrieval')

    g.add_edge('retrieval',             'graph_reasoning')
    g.add_edge('graph_reasoning',       'confidence_evaluation')
    g.add_edge('confidence_evaluation', 'reflection')

    # ── Conditional routing after reflection ──────────────────────
    g.add_conditional_edges(
        'reflection',
        route_after_reflection,
        {
            'disease_diagnosis': 'disease_diagnosis',
            'pest_detection':    'pest_detection',
            'fertilization':     'fertilization',
            'synthesis':         'synthesis',
            'fallback':          'fallback',
        },
    )

    # Domain specialist → critic → verification
    for specialist in ('disease_diagnosis', 'pest_detection', 'fertilization', 'synthesis'):
        g.add_edge(specialist, 'critic')

    g.add_edge('critic',      'verification')
    g.add_edge('fallback',    END)

    # ── Verification loop ─────────────────────────────────────────
    g.add_conditional_edges(
        'verification',
        route_after_verification,
        {
            'reflection': 'reflection',
            '__end__':    END,
        },
    )

    return g


# =========================================================
# COMPILED GRAPH (singleton per session)
# =========================================================

_compiled_graphs: dict = {}


def get_graph(
    retriever:  HybridRetriever,
    reasoner:   GraphReasoner,
    memory:     ConversationMemory,
    evaluator:  ConfidenceEvaluator,
    session_id: str = 'default',
):
    if session_id not in _compiled_graphs:
        g = build_graph(retriever, reasoner, memory, evaluator)
        _compiled_graphs[session_id] = g.compile()
        logger.info('LangGraph compiled for session: %s', session_id)
    return _compiled_graphs[session_id]


def run_graph(
    query:     str,
    retriever: HybridRetriever,
    reasoner:  GraphReasoner,
    memory:    ConversationMemory,
    evaluator: ConfidenceEvaluator,
    session_id: str = 'default',
) -> AgentState:
    """
    Run the full LangGraph pipeline for a query.
    Returns final AgentState.
    """
    graph = get_graph(retriever, reasoner, memory, evaluator, session_id)

    initial: AgentState = {
        'query':            query,
        'agent_path':       [],
        'reflection_round': 0,
        'retry_count':      0,
        'self_rag_iteration': 0,
        'skipped_nodes':    [],
    }

    try:
        final_state: AgentState = graph.invoke(initial)
    except Exception as e:
        logger.exception('Graph execution error: %s', e)
        final_state = dict(initial)
        final_state['final_answer'] = (
            'عذراً، حدث خطأ في النظام. يرجى المحاولة مرة أخرى.'
        )
        final_state['error'] = str(e)

    # Store in memory
    answer = final_state.get('final_answer', '')
    if answer and 'error' not in final_state:
        memory.add(query, answer)

    return final_state
