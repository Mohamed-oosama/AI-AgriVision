"""
scripts/convert_data.py — Data Converter for AgriAI v8

يتعامل مع 3 فورمات موجودة في الداتا:

FORMAT 1 — Main chunks (docs.json / docs.jsonl):
  {"total": 28613, "data": [{
      "id": 1, "text": "...", "source": "file.pdf",
      "metadata": {"language": "english", ...}
  }]}

FORMAT 2 — Entities & Relations (entities.json / entities.jsonl):
  [{"entities": [...], "relations": [...], "chunk_id": 2}]

FORMAT 3 — Knowledge Graph (knowledge_graph.json):
  {"nodes": [["node_name", {"community": 5}], ...],
   "edges": [["src", "tgt", {"relation": "...", "weight": 1.0}], ...]}

Usage:
  # حوّل كل الداتا دفعة واحدة
  python scripts/convert_data.py --input data/ --output data/ready/

  # حوّل ملف واحد بس
  python scripts/convert_data.py --input data/docs.json --output data/ready/

  # حوّل الـ knowledge graph
  python scripts/convert_data.py --graph data/knowledge_graph.json --output .

  # حوّل كل حاجة في خطوة واحدة
  python scripts/convert_data.py --all --input data/ --output data/ready/ --graph data/graph.json
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("converter")


# =========================================================
# FORMAT DETECTION
# =========================================================

def detect_format(data: Any) -> str:
    """
    Detect which of the 3 formats this data is.
    Returns: 'main_chunks' | 'entities' | 'graph' | 'unknown'
    """
    # FORMAT 3 — Graph: has "nodes" key with list of [name, attrs]
    if isinstance(data, dict) and "nodes" in data:
        nodes = data["nodes"]
        if nodes and isinstance(nodes[0], (list, tuple)):
            return "graph"

    # FORMAT 1 — Main chunks: has "data" key with list of dicts with "text"
    if isinstance(data, dict) and "data" in data:
        items = data["data"]
        if items and isinstance(items[0], dict) and "text" in items[0]:
            return "main_chunks"

    # FORMAT 1 alt — direct list of dicts with "text"
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            # FORMAT 2 — Entities: has "entities" or "relations" key
            if "entities" in first or "relations" in first:
                return "entities"
            # FORMAT 1 alt — direct list of text chunks
            if "text" in first:
                return "main_chunks"

    return "unknown"


# =========================================================
# FORMAT 1 — MAIN CHUNKS CONVERTER
# =========================================================

def convert_main_chunks(data: Any) -> List[Dict]:
    """
    Convert FORMAT 1 to standard AgriAI JSONL format.
    Output: [{"text": "...", "source": "...", "metadata": {...}}]
    """
    # Unwrap {"total": N, "data": [...]}
    if isinstance(data, dict) and "data" in data:
        items = data["data"]
    elif isinstance(data, list):
        items = data
    else:
        logger.warning("Unexpected main_chunks format")
        return []

    results = []
    skipped = 0

    for item in items:
        if not isinstance(item, dict):
            continue

        text = item.get("text", "").strip()
        if not text or len(text) < 50:
            skipped += 1
            continue

        # Build metadata — keep all useful fields
        meta = dict(item.get("metadata", {}))
        meta["original_id"]     = item.get("id")
        meta["word_count"]      = item.get("word_count", len(text.split()))
        meta["repair_status"]   = item.get("repair_status", "unknown")
        meta["overlap_removed"] = item.get("overlap_removed", 0)

        # Add page range if available
        if "source_page_start" in meta:
            meta["pages"] = f"{meta['source_page_start']}-{meta.get('source_page_end', '?')}"

        results.append({
            "text":     text,
            "source":   item.get("source", "unknown"),
            "metadata": meta,
        })

    logger.info("  Main chunks: %d converted, %d skipped (too short)", len(results), skipped)
    return results


# =========================================================
# FORMAT 2 — ENTITIES/RELATIONS CONVERTER
# =========================================================

def convert_entities(data: Any) -> Tuple[List[Dict], List[Dict]]:
    """
    Convert FORMAT 2 entities/relations to:
    - text chunks (entities as searchable text)
    - graph edges list

    Returns: (text_chunks, graph_edges)
    """
    if not isinstance(data, list):
        data = [data]

    text_chunks = []
    graph_edges = []

    for record in data:
        if not isinstance(record, dict):
            continue

        chunk_id  = record.get("chunk_id", "?")
        entities  = record.get("entities", [])
        relations = record.get("relations", [])

        # Convert entities to searchable text chunk
        if entities:
            ent_names = [e.get("name", "") for e in entities if e.get("name")]
            ent_types = [f"{e.get('name','')} ({e.get('type','')})" for e in entities]
            text = "كيانات زراعية: " + " | ".join(ent_names)
            if len(text) > 30:
                text_chunks.append({
                    "text":   text,
                    "source": f"entities_chunk_{chunk_id}",
                    "metadata": {
                        "type":     "entities",
                        "chunk_id": chunk_id,
                        "entities": ent_names,
                    },
                })

        # Convert relations to graph edges
        for rel in relations:
            src  = rel.get("source", "").strip()
            tgt  = rel.get("target", "").strip()
            rtype = rel.get("relation", "RELATED").strip()

            if not src or not tgt:
                continue

            # Normalize relation type to standard format
            rtype_norm = _normalize_relation(rtype)

            graph_edges.append({
                "source":   src,
                "target":   tgt,
                "relation": rtype_norm,
                "weight":   1.0,
            })

    logger.info("  Entities: %d text chunks, %d graph edges", len(text_chunks), len(graph_edges))
    return text_chunks, graph_edges


def _normalize_relation(rel: str) -> str:
    """Normalize relation types to standard set."""
    rel_upper = rel.upper().replace(" ", "_")
    mapping = {
        "CAUSES":                   "CAUSES",
        "TREATS":                   "TREATS",
        "TREATED_BY":               "TREATED_BY",
        "AFFECTS":                  "AFFECTS",
        "PREVENTS":                 "PREVENTS",
        "RELATED":                  "RELATED",
        "REQUIRES":                 "REQUIRES",
        "SYMPTOM_OF":               "SYMPTOM_OF",
        "CAUSED_BY":                "CAUSED_BY",
        "FOUND_IN":                 "FOUND_IN",
        "PHYLLOGENETIC_RELATIONSHIP":"RELATED",
        "DISTINCT_GROUP":           "RELATED",
        "USED_IN_EXPERIMENT":       "RELATED",
        "SUBJECT_TO_EXPERIMENTS":   "RELATED",
        "USED_MICROORGANISMS_TO_MAKE_BEER_AND_VINEGAR": "RELATED",
        "MICROORGANISMS":           "RELATED",
    }
    # Try exact match first
    if rel_upper in mapping:
        return mapping[rel_upper]
    # Try partial match
    for k, v in mapping.items():
        if k in rel_upper or rel_upper in k:
            return v
    return "RELATED"


# =========================================================
# FORMAT 3 — KNOWLEDGE GRAPH CONVERTER
# =========================================================

def convert_graph(data: Dict) -> Dict:
    """
    Convert FORMAT 3 graph to standard networkx node_link format.
    Input:  {"nodes": [["name", {"community": N}]], "edges": [...]}
    Output: {"directed": true, "nodes": [...], "links": [...]}
    """
    raw_nodes = data.get("nodes", [])
    raw_edges = data.get("edges", data.get("links", []))

    nodes = []
    seen_nodes = set()

    for item in raw_nodes:
        if isinstance(item, (list, tuple)) and len(item) >= 1:
            name   = str(item[0]).strip()
            attrs  = item[1] if len(item) > 1 else {}
        elif isinstance(item, dict):
            name  = item.get("id", item.get("name", "")).strip()
            attrs = {k: v for k, v in item.items() if k not in ("id", "name")}
        else:
            continue

        if not name or name in seen_nodes:
            continue
        seen_nodes.add(name)

        nodes.append({
            "id":        name,
            "original":  name,
            "community": attrs.get("community", 0) if isinstance(attrs, dict) else 0,
        })

    links = []
    for item in raw_edges:
        if isinstance(item, (list, tuple)):
            if len(item) == 3:
                src, tgt, attrs = item
            elif len(item) == 2:
                src, tgt, attrs = item[0], item[1], {}
            else:
                continue
        elif isinstance(item, dict):
            src   = item.get("source", "")
            tgt   = item.get("target", "")
            attrs = {k: v for k, v in item.items() if k not in ("source", "target")}
        else:
            continue

        src = str(src).strip()
        tgt = str(tgt).strip()
        if not src or not tgt:
            continue

        # Auto-add missing nodes
        for n in (src, tgt):
            if n not in seen_nodes:
                seen_nodes.add(n)
                nodes.append({"id": n, "original": n, "community": 0})

        rel    = attrs.get("relation", "RELATED") if isinstance(attrs, dict) else "RELATED"
        weight = attrs.get("weight", 1.0)          if isinstance(attrs, dict) else 1.0

        links.append({
            "source":   src,
            "target":   tgt,
            "relation": _normalize_relation(str(rel)),
            "weight":   float(weight),
        })

    result = {
        "directed":     True,
        "multigraph":   False,
        "graph":        {},
        "nodes":        nodes,
        "links":        links,
    }

    logger.info("  Graph: %d nodes, %d edges", len(nodes), len(links))
    return result


# =========================================================
# MERGE GRAPH: entities edges + existing graph
# =========================================================

def merge_graph(
    existing_graph: Optional[Dict],
    extra_edges: List[Dict],
) -> Dict:
    """Merge entity edges into existing graph (or create new)."""
    if existing_graph is None:
        existing_graph = {
            "directed": True, "multigraph": False,
            "graph": {}, "nodes": [], "links": [],
        }

    seen_nodes = {n["id"] for n in existing_graph["nodes"]}
    seen_links = {
        (l["source"], l["target"], l["relation"])
        for l in existing_graph["links"]
    }

    for edge in extra_edges:
        src = edge["source"]
        tgt = edge["target"]
        rel = edge["relation"]

        for n in (src, tgt):
            if n not in seen_nodes:
                seen_nodes.add(n)
                existing_graph["nodes"].append({"id": n, "original": n, "community": 0})

        key = (src, tgt, rel)
        if key not in seen_links:
            seen_links.add(key)
            existing_graph["links"].append(edge)

    return existing_graph


# =========================================================
# FILE LOADER
# =========================================================

def load_json_file(path: str) -> Any:
    """Load JSON or JSONL file, auto-detect format."""
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        content = f.read().strip()

    # Try full JSON first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try JSONL (one JSON per line)
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if records:
        return records

    raise ValueError(f"Could not parse {path} as JSON or JSONL")


def find_input_files(input_path: str) -> List[Path]:
    """Find all JSON/JSONL files in a path (file or directory)."""
    p = Path(input_path)
    if p.is_file():
        return [p]
    if p.is_dir():
        files = sorted(p.rglob("*.json")) + sorted(p.rglob("*.jsonl"))
        return [f for f in files if "ready" not in str(f) and "output" not in str(f)]
    return []


# =========================================================
# MAIN CONVERT FUNCTION
# =========================================================

def convert_all(
    input_path: str,
    output_dir: str,
    graph_path: Optional[str] = None,
    graph_output: Optional[str] = None,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    all_text_chunks: List[Dict] = []
    all_graph_edges: List[Dict] = []
    base_graph:      Optional[Dict] = None

    # ── Load knowledge graph if provided ──────────────────
    if graph_path and os.path.exists(graph_path):
        logger.info("Loading knowledge graph: %s", graph_path)
        g_data = load_json_file(graph_path)
        fmt    = detect_format(g_data)
        if fmt == "graph":
            base_graph = convert_graph(g_data)
        else:
            logger.warning("  Graph file format not recognized: %s", fmt)

    # ── Process input files ───────────────────────────────
    input_files = find_input_files(input_path)
    logger.info("Found %d input files", len(input_files))

    for file_path in input_files:
        logger.info("Processing: %s", file_path.name)
        try:
            data = load_json_file(str(file_path))
        except Exception as e:
            logger.error("  Failed to load %s: %s", file_path.name, e)
            continue

        fmt = detect_format(data)
        logger.info("  Detected format: %s", fmt)

        if fmt == "main_chunks":
            chunks = convert_main_chunks(data)
            all_text_chunks.extend(chunks)

        elif fmt == "entities":
            text_chunks, graph_edges = convert_entities(data)
            all_text_chunks.extend(text_chunks)
            all_graph_edges.extend(graph_edges)

        elif fmt == "graph":
            converted = convert_graph(data)
            if base_graph is None:
                base_graph = converted
            else:
                base_graph = merge_graph(base_graph, converted.get("links", []))

        else:
            logger.warning("  Unknown format — skipping %s", file_path.name)

    # ── Merge entity edges into graph ─────────────────────
    if all_graph_edges:
        base_graph = merge_graph(base_graph, all_graph_edges)

    # ── Save text chunks ──────────────────────────────────
    if all_text_chunks:
        chunks_out = os.path.join(output_dir, "docs_ready.jsonl")
        with open(chunks_out, "w", encoding="utf-8") as f:
            for chunk in all_text_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        logger.info("✅ Text chunks saved: %s (%d chunks)", chunks_out, len(all_text_chunks))
    else:
        logger.warning("⚠️  No text chunks generated")

    # ── Save knowledge graph ──────────────────────────────
    graph_out = graph_output or os.path.join(".", "knowledge_graph.json")
    if base_graph:
        with open(graph_out, "w", encoding="utf-8") as f:
            json.dump(base_graph, f, ensure_ascii=False, indent=2)
        n = len(base_graph.get("nodes", []))
        e = len(base_graph.get("links", []))
        logger.info("✅ Knowledge graph saved: %s (%d nodes, %d edges)", graph_out, n, e)
    else:
        logger.warning("⚠️  No graph data generated")

    # ── Summary ───────────────────────────────────────────
    print("\n" + "="*55)
    print("📊 ملخص التحويل:")
    print(f"   نصوص قابلة للبحث:  {len(all_text_chunks):,} chunk")
    print(f"   علاقات الجراف:      {len(all_graph_edges):,} edge")
    if base_graph:
        print(f"   الجراف النهائي:    {len(base_graph.get('nodes',[]))} node | {len(base_graph.get('links',[]))} edge")
    print(f"\n🚀 الخطوة التالية:")
    print(f"   python main.py --index {output_dir} --output .")
    print(f"   python main.py --chat")
    print("="*55)


# =========================================================
# CLI
# =========================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AgriAI v8 Data Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  python scripts/convert_data.py --input data/ --output data/ready/
  python scripts/convert_data.py --input data/docs.json --output data/ready/
  python scripts/convert_data.py --input data/ --output data/ready/ --graph data/graph.json
        """
    )
    parser.add_argument("--input",  required=True,  help="مسار الداتا (ملف أو فولدر)")
    parser.add_argument("--output", required=True,  help="فولدر الإخراج")
    parser.add_argument("--graph",  default=None,   help="مسار knowledge_graph.json (اختياري)")
    parser.add_argument("--graph-output", default=None, help="مسار حفظ الجراف (default: ./knowledge_graph.json)")
    args = parser.parse_args()

    convert_all(
        input_path  = args.input,
        output_dir  = args.output,
        graph_path  = args.graph,
        graph_output= args.graph_output,
    )
