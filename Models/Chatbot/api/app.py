"""
api/app.py — FastAPI server for AgriAI v8.

Endpoints:
  POST /query          — full pipeline, JSON response
  POST /query/stream   — streaming SSE response
  GET  /health         — health check
  GET  /metrics        — basic metrics
  GET  /memory/{sid}   — session memory stats
  DELETE /memory/{sid} — clear session memory
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import pickle
import faiss
import networkx as nx

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.config import CONFIG
from agents.workflow import run_graph
from memory.memory_system import ConversationMemory
from retrieval.hybrid_retriever import HybridRetriever
from graph.graph_reasoner import GraphReasoner
from confidence.confidence_evaluator import ConfidenceEvaluator
from utils.ollama import health_check, list_models
from utils.cache import cache_get, cache_set, SEMANTIC_CACHE

logger = logging.getLogger('agri_ai.api')

# ── Global resources ──────────────────────────────────────
_retriever: Optional[HybridRetriever] = None
_reasoner:  Optional[GraphReasoner]   = None
_evaluator  = ConfidenceEvaluator()
_memories:  dict = {}
_metrics    = {'queries': 0, 'errors': 0, 'avg_latency_ms': 0.0}


def _load_retriever():
    global _retriever
    try:
        index  = faiss.read_index(CONFIG.index_file)
        with open(CONFIG.chunks_file, 'rb') as f:
            chunks = pickle.load(f)
        parent_chunks = []
        try:
            with open(CONFIG.parent_chunks_file, 'rb') as f:
                parent_chunks = pickle.load(f)
        except FileNotFoundError:
            pass
        _retriever = HybridRetriever(index, chunks, parent_chunks)
        logger.info('Retriever loaded: %d chunks', len(chunks))
    except Exception as e:
        logger.warning('Could not load index: %s — using empty retriever', e)
        _retriever = HybridRetriever(None, [], [])


def _load_reasoner():
    global _reasoner
    try:
        import os
        if os.path.exists(CONFIG.graph_file):
            with open(CONFIG.graph_file, encoding='utf-8') as f:
                data = json.load(f)
            G = nx.node_link_graph(data)
        else:
            G = nx.DiGraph()
        _reasoner = GraphReasoner(G)
        logger.info('GraphReasoner loaded: %d nodes', G.number_of_nodes())
    except Exception as e:
        logger.warning('Graph load failed: %s', e)
        _reasoner = GraphReasoner(nx.DiGraph())


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_retriever()
    _load_reasoner()
    logger.info('AgriAI v8 API ready')
    yield


app = FastAPI(
    title='AgriAI v8 — Egyptian Agricultural Assistant',
    version='8.0.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ── Models ────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query:      str
    session_id: str = 'default'

class QueryResponse(BaseModel):
    answer:      str
    confidence:  float
    explanation: str
    agent_path:  list
    latency_ms:  float


# ── Helpers ───────────────────────────────────────────────

def _get_memory(session_id: str) -> ConversationMemory:
    if session_id not in _memories:
        _memories[session_id] = ConversationMemory(session_id)
    return _memories[session_id]


def _run_pipeline(query: str, session_id: str) -> dict:
    # Cache check
    cached = SEMANTIC_CACHE.get(query) or cache_get(query)
    if cached:
        cached['from_cache'] = True
        return cached

    memory   = _get_memory(session_id)
    t0       = time.perf_counter()
    state    = run_graph(query, _retriever, _reasoner, memory, _evaluator, session_id)
    latency  = (time.perf_counter() - t0) * 1000

    result = {
        'answer':      state.get('final_answer', ''),
        'confidence':  state.get('confidence', 0.0),
        'explanation': state.get('confidence_explanation', ''),
        'agent_path':  state.get('agent_path', []),
        'latency_ms':  round(latency, 1),
        'from_cache':  False,
    }

    cache_set(query, result)
    SEMANTIC_CACHE.set(query, result)
    return result


# ── Endpoints ──────────────────────────────────────────────

@app.post('/query', response_model=QueryResponse)
async def query(req: QueryRequest):
    _metrics['queries'] += 1
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, _run_pipeline, req.query, req.session_id
        )
        _metrics['avg_latency_ms'] = (
            (_metrics['avg_latency_ms'] * (_metrics['queries'] - 1) + result['latency_ms'])
            / _metrics['queries']
        )
        return result
    except Exception as e:
        _metrics['errors'] += 1
        logger.exception('Query error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/query/stream')
async def query_stream(req: QueryRequest):
    async def generate() -> AsyncIterator[str]:
        from utils.ollama import ollama_stream
        from agents.workflow import run_graph as _rg
        try:
            # Run pipeline up to synthesis, then stream final answer
            result = await asyncio.get_event_loop().run_in_executor(
                None, _run_pipeline, req.query, req.session_id
            )
            answer = result.get('answer', '')
            # Stream word by word for UX
            words = answer.split(' ')
            for i in range(0, len(words), CONFIG.stream_chunk_size):
                chunk = ' '.join(words[i:i + CONFIG.stream_chunk_size]) + ' '
                yield f'data: {json.dumps({"text": chunk}, ensure_ascii=False)}\n\n'
                await asyncio.sleep(0.02)
            yield 'data: [DONE]\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

    return StreamingResponse(generate(), media_type='text/event-stream')


@app.get('/health')
async def health():
    ollama_ok = health_check()
    models    = list_models() if ollama_ok else []
    return {
        'status':          'ok' if ollama_ok else 'degraded',
        'ollama':          ollama_ok,
        'models_loaded':   models,
        'index_loaded':    _retriever is not None and bool(_retriever.chunks),
        'graph_loaded':    _reasoner is not None and _reasoner.G.number_of_nodes() > 0,
    }


@app.get('/metrics')
async def metrics():
    return {**_metrics, 'active_sessions': len(_memories)}


@app.get('/memory/{session_id}')
async def memory_stats(session_id: str):
    return _get_memory(session_id).stats()


@app.delete('/memory/{session_id}')
async def clear_memory(session_id: str):
    mem = _get_memory(session_id)
    mem.clear_session()
    return {'cleared': True, 'session_id': session_id}
