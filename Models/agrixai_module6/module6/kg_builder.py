"""
kg_builder.py
=============
Hierarchical Knowledge Graph for AgriXAI Module 6.

Graph structure (multi-relational, directed):

    ROOT
    ├── Category: Disease | Pest | Deficiency
    │   └── CropFamily: Cereal | Solanaceae | Rubiaceae | Vitaceae | ...
    │       └── Crop: Wheat | Rice | Tomato | Coffee | Grape | ...
    │           └── ClassNode: e.g. "Wheat_Yellow_Rust"
    │               ├── --has_pathogen-->     PathogenNode
    │               ├── --triggered_by-->     EnvCondition (temp range, humidity)
    │               ├── --controlled_by-->    Intervention (biological/chemical/cultural)
    │               ├── --differential_with-> sibling ClassNodes
    │               └── --has_predator-->    Predator (pests only)

Edges carry a `relation` attribute and optional weight. We expose helpers:
  - build_graph(facts: dict)  -> nx.MultiDiGraph
  - traverse_path(g, start, end) -> list[str]   (for XAI "KG path: ...")
  - neighbors_by_relation(g, node, rel) -> list

We use MultiDiGraph because two nodes can be linked by more than one relation
(e.g. "Wheat -> Wheat_Yellow_Rust" via 'has_disease' and "Wheat_Yellow_Rust ->
Wheat -> 'host_of'" — distinct semantics).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import json
import logging

import networkx as nx

log = logging.getLogger(__name__)

# Relation constants -- single source of truth.
REL_HAS_CHILD       = "has_child"          # hierarchy
REL_HAS_PATHOGEN    = "has_pathogen"
REL_TRIGGERED_BY    = "triggered_by"
REL_CONTROLLED_BY   = "controlled_by"
REL_DIFFERENTIAL    = "differential_with"
REL_HAS_PREDATOR    = "has_predator"
REL_HOST_OF         = "host_of"
REL_AFFECTS         = "affects"            # deficiency element -> crop


CATEGORY_NODES = {
    "disease": "Category::Disease",
    "pest": "Category::Pest",
    "deficiency": "Category::Deficiency",
}


def _load_facts(facts_path: Optional[str | Path] = None) -> Dict:
    """Load the seeded fact base from JSON. Strips the `_meta` block."""
    if facts_path is None:
        facts_path = Path(__file__).parent / "data" / "kg_facts.json"
    with open(facts_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_meta", None)
    return data


def build_graph(
    facts: Optional[Dict] = None,
    class_sample_counts: Optional[Dict[str, int]] = None,
) -> nx.MultiDiGraph:
    """Construct the full hierarchical KG.

    Parameters
    ----------
    facts : dict, optional
        Mapping class_name -> fact dict (see kg_facts.json schema).
        If None, loads the bundled JSON.
    class_sample_counts : dict, optional
        Mapping class_name -> training sample count. Stored as a node attribute
        and later used by the rule engine to weight decisions for imbalanced
        classes (a 1k-image class shouldn't outvote a 50-image class on raw
        confidence alone).

    Returns
    -------
    networkx.MultiDiGraph
    """
    if facts is None:
        facts = _load_facts()

    g = nx.MultiDiGraph()
    g.add_node("ROOT", node_type="root", label="AgriXAI KG")

    # Category nodes
    for cat, node_id in CATEGORY_NODES.items():
        g.add_node(node_id, node_type="category", label=cat.title())
        g.add_edge("ROOT", node_id, relation=REL_HAS_CHILD)

    for class_name, info in facts.items():
        category = info.get("category", "disease")
        cat_node = CATEGORY_NODES.get(category, CATEGORY_NODES["disease"])

        # Crop family node
        family = info.get("crop_family", "Unknown")
        family_node = f"Family::{family}"
        if family_node not in g:
            g.add_node(family_node, node_type="crop_family", label=family)
            g.add_edge(cat_node, family_node, relation=REL_HAS_CHILD)

        # Crop node
        crop = info.get("crop", "Unknown")
        crop_node = f"Crop::{crop}"
        if crop_node not in g:
            g.add_node(crop_node, node_type="crop", label=crop)
            g.add_edge(family_node, crop_node, relation=REL_HAS_CHILD)

        # Class (specific disease/pest/deficiency) node
        sample_count = (class_sample_counts or {}).get(class_name)
        g.add_node(
            class_name,
            node_type="class",
            category=category,
            label=info.get("common_name_en", class_name),
            label_ar=info.get("common_name_ar", ""),
            sample_count=sample_count,
            damage_pct_untreated_15d=info.get("damage_pct_untreated_15d"),
            critical_growth_stages=info.get("critical_growth_stages", []),
        )
        g.add_edge(crop_node, class_name, relation=REL_HAS_CHILD)

        # Pathogen / agent node
        pathogen = info.get("pathogen_or_agent")
        if pathogen:
            pnode = f"Agent::{pathogen}"
            if pnode not in g:
                g.add_node(pnode, node_type="pathogen", label=pathogen)
            g.add_edge(class_name, pnode, relation=REL_HAS_PATHOGEN)

        # Environmental triggers
        triggers = info.get("triggers") or {}
        if triggers:
            trig_id = f"Trigger::{class_name}"
            g.add_node(
                trig_id,
                node_type="env_condition",
                temp_c=triggers.get("temp_c"),
                humidity_pct_min=triggers.get("humidity_pct_min"),
                season=triggers.get("season"),
                soil_ph_above=triggers.get("soil_ph_above"),
                label=_trigger_label(triggers),
            )
            g.add_edge(class_name, trig_id, relation=REL_TRIGGERED_BY)

        # Controls (biological / chemical / cultural)
        controls = info.get("controls") or {}
        for ctype, items in controls.items():
            for item in items:
                ctrl_id = f"Control::{ctype}::{item}"
                if ctrl_id not in g:
                    g.add_node(ctrl_id, node_type="intervention",
                               control_type=ctype, label=item)
                g.add_edge(class_name, ctrl_id, relation=REL_CONTROLLED_BY,
                           control_type=ctype)

        # Hosts (the crop is already linked, but for pests we note alternate hosts)
        for host in info.get("hosts", []):
            host_id = f"Crop::{host}"
            if host_id not in g:
                g.add_node(host_id, node_type="crop", label=host)
            # 'host_of' goes pathogen/pest -> crop (semantic clarity)
            g.add_edge(class_name, host_id, relation=REL_HOST_OF)

        # Predators (pest classes)
        for predator in info.get("predators", []):
            pred_id = f"Predator::{predator}"
            if pred_id not in g:
                g.add_node(pred_id, node_type="predator", label=predator)
            g.add_edge(class_name, pred_id, relation=REL_HAS_PREDATOR)

        # Differential (sibling links — confused-with relationships)
        for sibling in info.get("differential_with", []):
            # Add as a placeholder if sibling not yet visited; the second pass
            # below will fill in attributes.
            if sibling not in g:
                g.add_node(sibling, node_type="class", category=category,
                           label=sibling)
            g.add_edge(class_name, sibling, relation=REL_DIFFERENTIAL)

    log.info("KG built: %d nodes, %d edges", g.number_of_nodes(), g.number_of_edges())
    return g


def _trigger_label(triggers: dict) -> str:
    """Human-readable summary of an env_condition node."""
    parts = []
    if triggers.get("temp_c"):
        lo, hi = triggers["temp_c"]
        parts.append(f"{lo}-{hi}°C")
    if triggers.get("humidity_pct_min") is not None:
        parts.append(f"≥{triggers['humidity_pct_min']}% RH")
    if triggers.get("season"):
        parts.append("/".join(triggers["season"]))
    return ", ".join(parts) if parts else "any"


# ---------------------------------------------------------------------------
# Traversal helpers (used by XAI report generation)
# ---------------------------------------------------------------------------

def neighbors_by_relation(g: nx.MultiDiGraph, node: str, relation: str) -> List[str]:
    """Return all out-neighbors of `node` reached via edges with given relation."""
    out = []
    if node not in g:
        return out
    for _, tgt, data in g.out_edges(node, data=True):
        if data.get("relation") == relation:
            out.append(tgt)
    return out


def traverse_path(g: nx.MultiDiGraph, target_class: str) -> List[str]:
    """Walk from ROOT down to `target_class` and return labels along the way.

    Used to produce strings like:
        "Pests -> Wood Borers -> Xylotrechus -> Host: Grape"
    """
    if target_class not in g:
        return []
    try:
        # MultiDiGraph: use shortest_path on the underlying view; relations
        # don't affect path length here.
        path = nx.shortest_path(g, source="ROOT", target=target_class)
    except nx.NetworkXNoPath:
        return []
    labels = [g.nodes[n].get("label", n) for n in path]
    # Append a host hint if available
    hosts = neighbors_by_relation(g, target_class, REL_HOST_OF)
    if hosts:
        primary_host = g.nodes[hosts[0]].get("label", hosts[0].split("::", 1)[-1])
        labels.append(f"Host: {primary_host}")
    return labels


def get_class_metadata(g: nx.MultiDiGraph, class_name: str) -> Dict:
    """Return a dict consolidating everything the XAI report needs."""
    if class_name not in g:
        return {}
    meta = dict(g.nodes[class_name])
    meta["pathogens"] = [g.nodes[n]["label"]
                         for n in neighbors_by_relation(g, class_name, REL_HAS_PATHOGEN)]
    meta["controls"] = {
        ctype: [g.nodes[n]["label"]
                for _, n, d in g.out_edges(class_name, data=True)
                if d.get("relation") == REL_CONTROLLED_BY
                and d.get("control_type") == ctype]
        for ctype in ("biological", "chemical", "cultural")
    }
    meta["differential_siblings"] = neighbors_by_relation(g, class_name, REL_DIFFERENTIAL)
    meta["predators"] = [g.nodes[n]["label"]
                         for n in neighbors_by_relation(g, class_name, REL_HAS_PREDATOR)]
    triggers = neighbors_by_relation(g, class_name, REL_TRIGGERED_BY)
    if triggers:
        tnode = g.nodes[triggers[0]]
        meta["triggers"] = {
            "temp_c": tnode.get("temp_c"),
            "humidity_pct_min": tnode.get("humidity_pct_min"),
            "season": tnode.get("season"),
            "soil_ph_above": tnode.get("soil_ph_above"),
        }
    else:
        meta["triggers"] = {}
    return meta
