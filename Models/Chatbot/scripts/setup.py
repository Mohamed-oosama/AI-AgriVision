"""
scripts/setup.py — AgriAI v8 Setup Script
==========================================

يعمل كل حاجة في خطوة واحدة:

  1. يتأكد إن ملفاتك الأصلية موجودة:
       rag_index.faiss / rag_chunks.pkl / s5_final.json
       knowledge_graph.json / graph_data.json

  2. يعمل merge لـ knowledge_graph.json + graph_data.json
       → knowledge_graph_merged.json  (ده اللي v8 هيشتغل عليه)

  3. يتحقق من الـ FAISS index سليم ومتوافق

  4. يطبع ملخص كامل وأوامر التشغيل

Usage:
  python scripts/setup.py
  python scripts/setup.py --data-dir /path/to/data
  python scripts/setup.py --skip-merge   # لو عايز تتخطى الـ merge
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("setup")

# ── إضافة مسار المشروع ────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.config import CONFIG


# =========================================================
# STEP 1 — FILE VALIDATION
# =========================================================

def check_files(data_dir: str) -> Dict[str, bool]:
    """تحقق من وجود كل الملفات المطلوبة."""
    files = {
        "rag_index.faiss":       CONFIG.index_file,
        "rag_chunks.pkl":        CONFIG.chunks_file,
        "s5_final.json":         CONFIG.raw_data_file,
        "knowledge_graph.json":  CONFIG.graph_file,
        "graph_data.json":       CONFIG.graph_extra_file,
        "all_embeddings.npy":    CONFIG.embeddings_file,
    }

    print("\n📁 فحص الملفات:")
    print("─" * 50)
    status = {}
    for label, filename in files.items():
        path    = os.path.join(data_dir, filename)
        exists  = os.path.exists(path)
        size    = f"{os.path.getsize(path)/1e6:.1f} MB" if exists else "—"
        icon    = "✅" if exists else "❌"
        required = label not in ("all_embeddings.npy",)   # embeddings اختياري
        status[filename] = exists

        print(f"  {icon} {label:<28} {size:>10}  {'(مطلوب)' if required and not exists else ''}")

    return status


# =========================================================
# STEP 2 — GRAPH MERGE
# =========================================================

def _load_graph(path: str) -> Optional[Dict]:
    """Load any graph format and normalize it."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Cannot load %s: %s", path, e)
        return None

    # Detect format and normalize
    if "nodes" in data and "links" in data:
        # Already networkx node_link format
        return data

    if "nodes" in data and isinstance(data["nodes"], list):
        nodes = data["nodes"]
        edges = data.get("edges", data.get("links", []))

        # Format: nodes = [["name", {attrs}], ...]
        if nodes and isinstance(nodes[0], (list, tuple)):
            return _normalize_graph(nodes, edges)

        # Format: nodes = [{"id": ..., ...}]
        if nodes and isinstance(nodes[0], dict) and "id" in nodes[0]:
            return data   # already ok

    # Format: {"entities": [...], "relations": [...]}
    if isinstance(data, dict) and ("entities" in data or "relations" in data):
        return _from_entities_relations(data)

    # Format: list of [{entities, relations, chunk_id}, ...] — graph_data.json
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and ("entities" in first or "relations" in first):
            return _from_entities_relations(data)

    logger.warning("Unknown graph format in %s", path)
    return None


def _normalize_graph(raw_nodes: list, raw_edges: list) -> Dict:
    """Convert [name, attrs] node format to networkx node_link."""
    nodes = []
    seen: Set[str] = set()

    for item in raw_nodes:
        if isinstance(item, (list, tuple)):
            name  = str(item[0]).strip()
            attrs = item[1] if len(item) > 1 and isinstance(item[1], dict) else {}
        elif isinstance(item, dict):
            name  = item.get("id", item.get("name", "")).strip()
            attrs = {k: v for k, v in item.items() if k not in ("id", "name")}
        else:
            continue

        if not name or name in seen:
            continue
        seen.add(name)
        nodes.append({
            "id":        name,
            "original":  name,
            "community": attrs.get("community", 0),
        })

    links = []
    seen_links: Set[Tuple] = set()

    for item in raw_edges:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            src   = str(item[0]).strip()
            tgt   = str(item[1]).strip()
            attrs = item[2] if len(item) > 2 and isinstance(item[2], dict) else {}
        elif isinstance(item, dict):
            src   = str(item.get("source", "")).strip()
            tgt   = str(item.get("target", "")).strip()
            attrs = {k: v for k, v in item.items() if k not in ("source", "target")}
        else:
            continue

        if not src or not tgt:
            continue

        # Auto-add missing nodes
        for n in (src, tgt):
            if n not in seen:
                seen.add(n)
                nodes.append({"id": n, "original": n, "community": 0})

        rel    = str(attrs.get("relation", "RELATED"))
        weight = float(attrs.get("weight", 1.0))
        key    = (src, tgt, rel)
        if key not in seen_links:
            seen_links.add(key)
            links.append({"source": src, "target": tgt, "relation": rel, "weight": weight})

    return {"directed": True, "multigraph": False, "graph": {}, "nodes": nodes, "links": links}


def _from_entities_relations(data) -> Dict:
    """Convert entities/relations format to networkx node_link.
    Accepts: dict with entities/relations keys, OR list of such dicts.
    """
    records = data if isinstance(data, list) else [data]
    nodes   = []
    links   = []
    seen_nodes: Set[str] = set()
    seen_links: Set[Tuple] = set()

    for record in records:
        if not isinstance(record, dict):
            continue
        for ent in record.get("entities", []):
            name = str(ent.get("name", "")).strip()
            if name and name not in seen_nodes:
                seen_nodes.add(name)
                nodes.append({"id": name, "original": name,
                              "type": ent.get("type", ""), "community": 0})

        for rel in record.get("relations", []):
            src = str(rel.get("source", "")).strip()
            tgt = str(rel.get("target", "")).strip()
            r   = str(rel.get("relation", "RELATED"))
            if not src or not tgt:
                continue
            for n in (src, tgt):
                if n not in seen_nodes:
                    seen_nodes.add(n)
                    nodes.append({"id": n, "original": n, "community": 0})
            key = (src, tgt, r)
            if key not in seen_links:
                seen_links.add(key)
                links.append({"source": src, "target": tgt, "relation": r, "weight": 1.0})

    logger.info("  entities/relations → %d nodes, %d edges from %d records",
                len(nodes), len(links), len(records))
    return {"directed": True, "multigraph": False, "graph": {}, "nodes": nodes, "links": links}


def merge_graphs(graph1: Dict, graph2: Dict) -> Dict:
    """
    Merge two networkx node_link graphs.
    - Nodes: union (no duplicates by id)
    - Links: union (no duplicates by source+target+relation)
    """
    merged_nodes: Dict[str, Dict] = {n["id"]: n for n in graph1.get("nodes", [])}
    merged_links: Dict[Tuple, Dict] = {
        (l["source"], l["target"], l.get("relation", "RELATED")): l
        for l in graph1.get("links", [])
    }

    # Add nodes from graph2
    for n in graph2.get("nodes", []):
        nid = n.get("id", "")
        if nid and nid not in merged_nodes:
            merged_nodes[nid] = n

    # Add links from graph2
    for l in graph2.get("links", []):
        key = (l.get("source", ""), l.get("target", ""), l.get("relation", "RELATED"))
        if key[0] and key[1] and key not in merged_links:
            merged_links[key] = l

    return {
        "directed":   True,
        "multigraph": False,
        "graph":      {},
        "nodes":      list(merged_nodes.values()),
        "links":      list(merged_links.values()),
    }


def run_merge(data_dir: str, output_path: str) -> bool:
    """Merge knowledge_graph.json + graph_data.json → knowledge_graph_merged.json"""
    print("\n🔀 دمج الجرافين:")
    print("─" * 50)

    g1_path = os.path.join(data_dir, CONFIG.graph_file)
    g2_path = os.path.join(data_dir, CONFIG.graph_extra_file)

    g1 = _load_graph(g1_path)
    g2 = _load_graph(g2_path)

    if g1 is None and g2 is None:
        logger.error("❌ لا يوجد أي graph للدمج")
        return False

    if g1 is None:
        logger.warning("knowledge_graph.json مش موجود — هستخدم graph_data.json بس")
        merged = g2
    elif g2 is None:
        logger.warning("graph_data.json مش موجود — هستخدم knowledge_graph.json بس")
        merged = g1
    else:
        merged = merge_graphs(g1, g2)
        print(f"  knowledge_graph.json: {len(g1.get('nodes',[]))} nodes, {len(g1.get('links',[]))} edges")
        print(f"  graph_data.json:      {len(g2.get('nodes',[]))} nodes, {len(g2.get('links',[]))} edges")

    n_nodes = len(merged.get("nodes", []))
    n_links = len(merged.get("links", []))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n  ✅ knowledge_graph_merged.json")
    print(f"     Nodes: {n_nodes:,}  |  Edges: {n_links:,}")
    return True


# =========================================================
# STEP 3 — VALIDATE FAISS INDEX
# =========================================================

def validate_index(data_dir: str) -> bool:
    """تحقق إن الـ FAISS index سليم ومتوافق مع chunks."""
    print("\n🔍 فحص FAISS Index:")
    print("─" * 50)

    index_path  = os.path.join(data_dir, CONFIG.index_file)
    chunks_path = os.path.join(data_dir, CONFIG.chunks_file)

    if not os.path.exists(index_path):
        print("  ❌ rag_index.faiss مش موجود")
        return False
    if not os.path.exists(chunks_path):
        print("  ❌ rag_chunks.pkl مش موجود")
        return False

    try:
        import faiss
        import numpy as np

        index  = faiss.read_index(index_path)
        n_vecs = index.ntotal
        dim    = index.d

        with open(chunks_path, "rb") as f:
            chunks = pickle.load(f)
        n_chunks = len(chunks)

        match = n_vecs == n_chunks
        print(f"  FAISS vectors: {n_vecs:,}  |  dim: {dim}")
        print(f"  Chunks:        {n_chunks:,}")
        print(f"  Match:         {'✅ متوافقان' if match else '⚠️  عدد مختلف'}")

        if not match:
            print(f"  ⚠️  الـ index فيه {n_vecs} vector لكن الـ chunks فيه {n_chunks}")
            print(f"     النظام هيشتغل بس ممكن يطلع نتائج ناقصة.")

        # Sample chunk
        sample = chunks[0] if chunks else {}
        print(f"  Sample chunk keys: {list(sample.keys())}")
        return True

    except ImportError:
        print("  ⚠️  faiss مش مثبّت — pip install faiss-gpu أو faiss-cpu")
        return False
    except Exception as e:
        print(f"  ❌ خطأ: {e}")
        return False


# =========================================================
# STEP 4 — UPDATE CONFIG GRAPH PATH
# =========================================================

def update_env_file(merged_path: str) -> None:
    """اكتب .env file يخلي v8 يشتغل على الـ merged graph."""
    env_content = f"""# AgriAI v8 — Auto-generated by setup.py
# الملفات الأصلية
INDEX_FILE=rag_index.faiss
CHUNKS_FILE=rag_chunks.pkl
RAW_DATA_FILE=s5_final.json
EMBEDDINGS_FILE=all_embeddings.npy

# الـ graph المدموج (ناتج setup.py)
GRAPH_FILE={os.path.basename(merged_path)}
GRAPH_EXTRA_FILE=graph_data.json
GRAPH_MERGED_FILE={os.path.basename(merged_path)}

# النماذج
MODEL_MAIN=qwen3:8b
MODEL_FAST=qwen3:4b
EMBED_MODEL=intfloat/multilingual-e5-large
RERANKER_MODEL=BAAI/bge-reranker-base
"""
    env_path = os.path.join(ROOT, ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"\n  ✅ .env محدّث: GRAPH_FILE={os.path.basename(merged_path)}")


# =========================================================
# MAIN
# =========================================================

def main():
    parser = argparse.ArgumentParser(description="AgriAI v8 Setup")
    parser.add_argument("--data-dir",    default=".",      help="فولدر الداتا")
    parser.add_argument("--output-dir",  default=".",      help="فولدر الإخراج")
    parser.add_argument("--skip-merge",  action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    args = parser.parse_args()

    print("=" * 55)
    print("🌾 AgriAI v8 — Setup")
    print("=" * 55)

    data_dir   = args.data_dir
    output_dir = args.output_dir
    merged_path = os.path.join(output_dir, CONFIG.graph_merged_file)

    # Step 1 — Check files
    status = check_files(data_dir)

    missing_critical = [
        f for f in ["rag_index.faiss", "rag_chunks.pkl"]
        if not status.get(f, False)
    ]
    if missing_critical:
        print(f"\n❌ ملفات أساسية ناقصة: {missing_critical}")
        print("   مش هينفع تشغّل النظام بدونها.")
        sys.exit(1)

    # Step 2 — Merge graphs
    merge_ok = True
    if not args.skip_merge:
        merge_ok = run_merge(data_dir, merged_path)
        if merge_ok:
            update_env_file(merged_path)
    else:
        print("\n⏭️  تخطي الـ merge (--skip-merge)")
        merged_path = os.path.join(data_dir, CONFIG.graph_file)

    # Step 3 — Validate index
    if not args.skip_validate:
        validate_index(data_dir)

    # Step 4 — Print run commands
    graph_arg = os.path.basename(merged_path) if merge_ok else CONFIG.graph_file
    print("\n" + "=" * 55)
    print("🚀 كل حاجة جاهزة! شغّل:")
    print("─" * 55)
    print(f"  # محادثة تفاعلية")
    print(f"  python main.py --chat")
    print(f"")
    print(f"  # سؤال واحد")
    print(f"  python main.py --query \"سؤالك هنا\"")
    print(f"")
    print(f"  # API Server")
    print(f"  python main.py --api --port 8000")
    print(f"")
    print(f"  # فحص الصحة")
    print(f"  python main.py --health")
    print("=" * 55)


if __name__ == "__main__":
    main()
