"""
main.py — AgriAI v8 CLI

Commands:
  python main.py --chat                    # interactive chat
  python main.py --query "الطماطم بتصفر"  # single query
  python main.py --bench data/test.jsonl   # run benchmark
  python main.py --api                     # start FastAPI server
  python main.py --health                  # check Ollama + models
  python main.py --index data/docs.jsonl  # build index

Example session:
  ollama serve &
  ollama pull qwen3:8b
  python main.py --index data/docs.jsonl
  python main.py --chat
"""
from __future__ import annotations

import os
# Force offline mode for HuggingFace Transformers
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import argparse
import json
import logging
import os
import pickle
import sys
from pathlib import Path

import faiss
import networkx as nx

from core.config import CONFIG
from utils.ollama import health_check, list_models
from memory.memory_system import ConversationMemory
from retrieval.hybrid_retriever import HybridRetriever
from graph.graph_reasoner import GraphReasoner
from confidence.confidence_evaluator import ConfidenceEvaluator
from agents.workflow import run_graph
from utils.text import detect_language

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(CONFIG.log_file, encoding='utf-8'),
    ],
)
logger = logging.getLogger('agri_ai.main')

BANNER = """
╔══════════════════════════════════════════════════════╗
║      🌾  AgriAI v8 — المساعد الزراعي المصري          ║
║      نموذج: Qwen3:8B + bge-m3 + LangGraph            ║
║      اكتب سؤالك أو (خروج) للإنهاء                   ║
╚══════════════════════════════════════════════════════╝
"""


def _load_components():
    """
    Load retriever, reasoner, evaluator.

    ملفات الداتا المتوقعة (بأسمائها الأصلية):
      rag_index.faiss           ← FAISS index
      rag_chunks.pkl            ← النصوص المقسّمة
      knowledge_graph_merged.json ← الجراف المدموج (ناتج setup.py)
      knowledge_graph.json      ← fallback لو المدموج مش موجود
      graph_data.json           ← fallback ثاني
    """
    # ── Embedding warmup ──────────────────────────────────
    print('🔌 اختبار bge-m3 عبر Ollama...')
    from utils.models import Models
    if Models.warmup():
        print(f'✅ Embed:  bge-m3:latest via Ollama (dim={Models._embed_dim})')
    else:
        print('⚠️  bge-m3 غير متاح — تأكد إن ollama serve شغّال و bge-m3:latest مثبّت')

    # ── Retriever ─────────────────────────────────────────
    try:
        index = faiss.read_index(CONFIG.index_file)
        with open(CONFIG.chunks_file, 'rb') as f:
            chunks = pickle.load(f)
        parent_chunks = []
        if os.path.exists(CONFIG.parent_chunks_file):
            with open(CONFIG.parent_chunks_file, 'rb') as f:
                parent_chunks = pickle.load(f)
        retriever = HybridRetriever(index, chunks, parent_chunks)
        print(f'✅ Index:  {len(chunks):,} chunks | dim={index.d} | parents={len(parent_chunks):,}')
    except FileNotFoundError:
        print('⚠️  rag_index.faiss / rag_chunks.pkl مش موجودين')
        print('   شغّل أولاً: python scripts/setup.py')
        retriever = HybridRetriever(None, [], [])

    # ── Graph Reasoner ────────────────────────────────────
    G = _load_best_graph()
    reasoner  = GraphReasoner(G)
    evaluator = ConfidenceEvaluator()
    return retriever, reasoner, evaluator


def _parse_graph_data(data, path: str) -> nx.DiGraph:
    """
    Parse any graph format into a networkx DiGraph.
    Handles all known formats robustly.
    """
    G = nx.DiGraph()

    # ── FORMAT A: networkx node_link (nodes + links/edges keys) ──
    if isinstance(data, dict) and "nodes" in data:
        nodes = data["nodes"]
        links = data.get("links", data.get("edges", []))

        # nodes = [["name", {attrs}], ...]  ← community graph format
        if nodes and isinstance(nodes[0], (list, tuple)):
            for item in nodes:
                name  = str(item[0]).strip()
                attrs = item[1] if len(item) > 1 and isinstance(item[1], dict) else {}
                if name:
                    G.add_node(name, original=name, **attrs)
            for item in links:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    src, tgt = str(item[0]).strip(), str(item[1]).strip()
                    attrs = item[2] if len(item) > 2 and isinstance(item[2], dict) else {}
                    if src and tgt:
                        G.add_edge(src, tgt, relation=attrs.get("relation","RELATED"),
                                   weight=float(attrs.get("weight", 1.0)))
                elif isinstance(item, dict):
                    src = str(item.get("source","")).strip()
                    tgt = str(item.get("target","")).strip()
                    if src and tgt:
                        G.add_edge(src, tgt,
                                   relation=item.get("relation","RELATED"),
                                   weight=float(item.get("weight", 1.0)))
            return G

        # nodes = [{"id": ..., ...}]  ← standard networkx node_link
        if nodes and isinstance(nodes[0], dict):
            # rename edges → links if needed
            if "edges" in data and "links" not in data:
                data["links"] = data.pop("edges")
            try:
                return nx.node_link_graph(data)
            except Exception:
                pass
            # fallback: manual parse
            for n in nodes:
                nid = n.get("id", n.get("name", ""))
                if nid:
                    G.add_node(str(nid), **{k: v for k, v in n.items() if k != "id"})
            for l in links:
                if isinstance(l, dict):
                    src = str(l.get("source","")).strip()
                    tgt = str(l.get("target","")).strip()
                    if src and tgt:
                        G.add_edge(src, tgt,
                                   relation=l.get("relation","RELATED"),
                                   weight=float(l.get("weight", 1.0)))
            return G

    # ── FORMAT B: list of {entities, relations, chunk_id} ──────────
    records = data if isinstance(data, list) else []
    if not records and isinstance(data, dict):
        if "entities" in data or "relations" in data:
            records = [data]

    if records and isinstance(records[0], dict) and (
        "entities" in records[0] or "relations" in records[0]
    ):
        seen_nodes: set = set()
        for rec in records:
            for ent in rec.get("entities", []):
                name = str(ent.get("name", "")).strip()
                if name and name not in seen_nodes:
                    seen_nodes.add(name)
                    G.add_node(name, original=name,
                               entity_type=ent.get("type", ""))
            for rel in rec.get("relations", []):
                src = str(rel.get("source", "")).strip()
                tgt = str(rel.get("target", "")).strip()
                r   = str(rel.get("relation", "RELATED"))
                if src and tgt:
                    if src not in seen_nodes:
                        seen_nodes.add(src); G.add_node(src, original=src)
                    if tgt not in seen_nodes:
                        seen_nodes.add(tgt); G.add_node(tgt, original=tgt)
                    G.add_edge(src, tgt, relation=r, weight=1.0)
        return G

    return G   # empty fallback


def _load_best_graph() -> nx.DiGraph:
    """
    Try all graph files, parse each, merge into one DiGraph.
    Never crashes — always returns a valid (possibly empty) graph.
    """
    candidates = [
        CONFIG.graph_merged_file,   # knowledge_graph_merged.json
        CONFIG.graph_file,          # knowledge_graph.json
        CONFIG.graph_extra_file,    # graph_data.json
    ]

    merged = nx.DiGraph()

    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            G = _parse_graph_data(data, path)
            n, e = G.number_of_nodes(), G.number_of_edges()
            if n == 0:
                print(f'⚠️  {path}: قُرئ لكن لا يحتوي nodes')
                continue
            # merge into main graph
            merged.add_nodes_from(G.nodes(data=True))
            merged.add_edges_from(G.edges(data=True))
            print(f'✅ Graph:  {n:,} nodes | {e:,} edges ({path})')
        except Exception as ex:
            print(f'⚠️  خطأ في {path}: {ex}')
            continue

    total_n = merged.number_of_nodes()
    total_e = merged.number_of_edges()
    if total_n == 0:
        print('⚠️  لم يُحمَّل أي graph — graph reasoning معطّل')
    else:
        print(f'📊 Graph الكلي: {total_n:,} nodes | {total_e:,} edges')
    return merged


# =========================================================
# CHAT HISTORY MANAGER — TXT FORMAT
# =========================================================

import datetime

class ChatHistoryManager:
    """
    يحفظ كل سؤال وإجابة في ملف TXT مقروء.

    chat_history/
    ├── session_2026-06-08_19-30.txt
    └── session_2026-06-09_09-00.txt
    """

    def __init__(self, history_dir: str = 'chat_history') -> None:
        self.history_dir  = history_dir
        self.session_file = ''
        self.turn_count   = 0
        os.makedirs(history_dir, exist_ok=True)

    def start_session(self) -> str:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
        self.session_file = os.path.join(
            self.history_dir, f'session_{timestamp}.txt'
        )
        header = (
            f'╔══════════════════════════════════════════════════╗\n'
            f'║  AgriAI v8 — جلسة محادثة                        ║\n'
            f'║  التاريخ: {timestamp}                    ║\n'
            f'╚══════════════════════════════════════════════════╝\n\n'
        )
        self._write_raw(header)
        print(f'💾 حفظ المحادثة في: {self.session_file}')
        return self.session_file

    def save_turn(
        self,
        query:      str,
        answer:     str,
        confidence: float,
        agent_path: list,
        query_type: str = '',
    ) -> None:
        self.turn_count += 1
        now = datetime.datetime.now().strftime('%H:%M:%S')

        block = (
            f'{'─'*60}\n'
            f'[{self.turn_count}] {now}  |  نوع: {query_type}  |  ثقة: {confidence:.0%}\n'
            f'\n'
            f'❓ السؤال:\n{query}\n'
            f'\n'
            f'✅ الإجابة:\n{answer}\n'
            f'\n'
            f'📍 المسار: {" → ".join(agent_path[-6:])}\n'
            f'\n'
        )
        self._write_raw(block)

    def end_session(self) -> None:
        footer = (
            f'{'═'*60}\n'
            f'نهاية الجلسة — {self.turn_count} سؤال\n'
            f'{'═'*60}\n'
        )
        self._write_raw(footer)
        print(f'\n💾 المحادثة اتحفظت: {self.turn_count} سؤال ← {self.session_file}')

    def _write_raw(self, text: str) -> None:
        if not self.session_file:
            return
        try:
            with open(self.session_file, 'a', encoding='utf-8') as f:
                f.write(text)
        except Exception as e:
            logger.warning('History write error: %s', e)

    @staticmethod
    def list_sessions(history_dir: str = 'chat_history') -> list:
        if not os.path.exists(history_dir):
            return []
        files   = sorted(Path(history_dir).glob('session_*.txt'), reverse=True)
        sessions = []
        for f in files:
            lines = open(f, encoding='utf-8').readlines()
            turns = sum(1 for l in lines if l.startswith('❓ السؤال:'))
            size  = f.stat().st_size / 1024
            sessions.append({
                'file':     str(f),
                'turns':    turns,
                'size_kb':  round(size, 1),
            })
        return sessions


# =========================================================
# CMD_CHAT
# =========================================================

def cmd_chat(args):
    print(BANNER)

    if not health_check():
        print('❌ Ollama غير متاح. شغّل: ollama serve')
        sys.exit(1)

    models = list_models()
    print(f'✅ Ollama متصل | النماذج: {", ".join(models) or "لا يوجد"}')

    retriever, reasoner, evaluator = _load_components()
    memory  = ConversationMemory(session_id='chat')

    # ── Chat History ──────────────────────────────────────
    history = ChatHistoryManager()
    save_history = getattr(args, 'save_history', True)   # افتراضي: يحفظ دايماً
    if save_history:
        history.start_session()

    print('\nاكتب سؤالك (خروج | exit | quit للإنهاء)')
    print('أوامر خاصة: /memory | /clear | /history\n')

    while True:
        try:
            query = input('🌾 سؤالك: ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nمع السلامة! 👋')
            if save_history:
                history.end_session()
            break

        if not query:
            continue

        # ── أوامر خاصة ───────────────────────────────────
        if query.lower() in ('خروج', 'exit', 'quit', 'q'):
            print('مع السلامة! 👋')
            if save_history:
                history.end_session()
            break

        if query == '/memory':
            print(json.dumps(memory.stats(), ensure_ascii=False, indent=2))
            continue

        if query == '/clear':
            memory.clear_session()
            print('✅ تم مسح ذاكرة الجلسة.')
            continue

        if query == '/history':
            sessions = ChatHistoryManager.list_sessions()
            if not sessions:
                print('لا توجد محادثات محفوظة بعد.')
            else:
                print(f'\n📂 المحادثات المحفوظة ({len(sessions)}):')
                for s in sessions[:10]:
                    print(f"  {s['file']}  —  {s['turns']} سؤال  ({s['size_kb']} KB)")
            continue

        # ── تشغيل الـ pipeline ────────────────────────────
        state = run_graph(
            query     = query,
            retriever = retriever,
            reasoner  = reasoner,
            memory    = memory,
            evaluator = evaluator,
        )

        answer     = state.get('final_answer', 'لم أتمكن من الإجابة.')
        conf       = state.get('confidence', 0.0)
        path       = ' → '.join(state.get('agent_path', [])[-6:])
        flags      = state.get('hallucination_flags', [])
        query_type = state.get('query_type', '')

        # ── عرض النتيجة ──────────────────────────────────
        print(f'\n{"─"*60}')
        print(f'📋 الإجابة:\n{answer}')
        print(f'\n📊 الثقة: {conf:.0%} | النوع: {query_type} | المسار: {path}')
        if flags:
            print(f'⚠️  تحذيرات: {" | ".join(flags[:2])}')
        if state.get('needs_clarification'):
            print(f'❓ {state.get("clarifying_question", "")}')
        print(f'{"─"*60}\n')

        # ── حفظ في الـ history ────────────────────────────
        if save_history:
            history.save_turn(
                query      = query,
                answer     = answer,
                confidence = conf,
                agent_path = state.get('agent_path', []),
                query_type = query_type,
            )


def cmd_query(args):
    if not health_check():
        print('❌ Ollama غير متاح.')
        sys.exit(1)

    retriever, reasoner, evaluator = _load_components()
    memory = ConversationMemory(session_id='cli')

    state = run_graph(
        query     = args.query,
        retriever = retriever,
        reasoner  = reasoner,
        memory    = memory,
        evaluator = evaluator,
    )

    result = {
        'query':      args.query,
        'answer':     state.get('final_answer', ''),
        'confidence': state.get('confidence', 0.0),
        'path':       state.get('agent_path', []),
        'explanation':state.get('confidence_explanation', ''),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_bench(args):
    from evaluation.evaluator import run_benchmark

    retriever, reasoner, evaluator = _load_components()
    memory = ConversationMemory(session_id='bench')

    def run_fn(q: str):
        return run_graph(q, retriever, reasoner, memory, evaluator)

    with open(args.bench, encoding='utf-8') as f:
        test_cases = [json.loads(l) for l in f if l.strip()]

    print(f'🔬 Running benchmark on {len(test_cases)} test cases…')
    result = run_benchmark(test_cases, run_fn)
    print(result.summary())

    out_path = args.bench.replace('.jsonl', '_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    print(f'\n💾 Results saved to {out_path}')


def cmd_api(args):
    import uvicorn
    uvicorn.run(
        'api.app:app',
        host=args.host,
        port=args.port,
        reload=False,
        log_level='info',
    )


def cmd_health(args):
    ok = health_check()
    print(f'Ollama: {"✅ متصل" if ok else "❌ غير متاح"}')
    if ok:
        models = list_models()
        print(f'النماذج المثبّتة: {", ".join(models) or "لا يوجد"}')
        needed = [CONFIG.model_main, CONFIG.model_fast]
        for m in needed:
            found = any(m in ml for ml in models)
            print(f'  {m}: {"✅" if found else "❌ غير مثبّت — ollama pull " + m}')

    print(f'\nملفات الداتا:')
    all_files = [
        ('rag_index.faiss',             CONFIG.index_file,         True),
        ('rag_chunks.pkl',              CONFIG.chunks_file,        True),
        ('s5_final.json',               CONFIG.raw_data_file,      False),
        ('knowledge_graph.json',        CONFIG.graph_file,         False),
        ('graph_data.json',             CONFIG.graph_extra_file,   False),
        ('knowledge_graph_merged.json', CONFIG.graph_merged_file,  True),
        ('all_embeddings.npy',          CONFIG.embeddings_file,    False),
    ]
    for label, path, required in all_files:
        exists = os.path.exists(path)
        size   = f'{os.path.getsize(path)/1e6:.1f} MB' if exists else '-'
        icon   = '✅' if exists else ('❌' if required else '—')
        print(f'  {icon} {label:<32} {size:>10}')

    # Suggest setup if merged graph missing
    if not os.path.exists(CONFIG.graph_merged_file):
        print('\n⚠️  knowledge_graph_merged.json مش موجود.')
        print('   شغّل: python scripts/setup.py')


def cmd_index(args):
    from scripts.index_builder import build_index
    build_index(
        docs_path   = args.index,
        output_dir  = args.output,
        child_size  = args.child_size,
        parent_size = args.parent_size,
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AgriAI v8')
    parser.add_argument('--chat',         action='store_true',  help='محادثة تفاعلية')
    parser.add_argument('--query',        type=str,             help='سؤال واحد')
    parser.add_argument('--bench',        type=str,             help='Path to test.jsonl')
    parser.add_argument('--api',          action='store_true',  help='تشغيل API Server')
    parser.add_argument('--health',       action='store_true',  help='فحص النظام')
    parser.add_argument('--index',        type=str,             help='Path to docs for indexing')
    parser.add_argument('--show-history', action='store_true',  help='عرض المحادثات المحفوظة')
    parser.add_argument('--no-history',   action='store_true',  help='لا تحفظ المحادثة')
    parser.add_argument('--history-dir',  default='chat_history', help='فولدر حفظ المحادثات')
    parser.add_argument('--output',       default='.')
    parser.add_argument('--host',         default='0.0.0.0')
    parser.add_argument('--port',         type=int, default=8000)
    parser.add_argument('--child-size',   type=int, default=CONFIG.child_chunk_size)
    parser.add_argument('--parent-size',  type=int, default=CONFIG.parent_chunk_size)
    args = parser.parse_args()

    # ── save_history flag ─────────────────────────────────
    args.save_history = not args.no_history

    if args.show_history:
        sessions = ChatHistoryManager.list_sessions(args.history_dir)
        if not sessions:
            print('📂 لا توجد محادثات محفوظة في chat_history/')
        else:
            print(f'\n📂 المحادثات المحفوظة ({len(sessions)}):')
            for s in sessions:
                print(f"  📄 {s['file']}  —  {s['turns']} سؤال  ({s['size_kb']} KB)")
    elif args.chat:
        cmd_chat(args)
    elif args.query:
        cmd_query(args)
    elif args.bench:
        cmd_bench(args)
    elif args.api:
        cmd_api(args)
    elif args.health:
        cmd_health(args)
    elif args.index:
        cmd_index(args)
    else:
        parser.print_help()
