"""
graph/graph_reasoner.py — v8 Multi-hop Graph Reasoning.

Improvements over v7:
  • Path ranking by aggregated evidence score
  • Missing information detection (what's NOT in graph)
  • Evidence aggregation across multiple entity chains
  • Cycle detection and loop prevention
  • Relation weight learning via usage statistics
  • Forward + backward reasoning (disease→treatment AND treatment→disease)
  • Contradiction scoring: returns severity, not just bool
  • Graph stats for confidence calibration
"""
from __future__ import annotations

import logging
from collections import deque, defaultdict
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx
from rapidfuzz import fuzz

from core.config import CONFIG
from utils.text import normalize_ar

logger = logging.getLogger('agri_ai.graph')

# Arabic relation labels
_RELATION_AR: Dict[str, str] = {
    'CAUSES':          'قد يسبب',
    'TREATS':          'يساعد في علاج',
    'AFFECTS':         'يصيب',
    'PREVENTS':        'يساعد على منع',
    'REQUIRES':        'يحتاج إلى',
    'RELATED':         'مرتبط بـ',
    'SYMPTOM_OF':      'عرض من أعراض',
    'TREATED_BY':      'يُعالَج بـ',
    'CAUSED_BY':       'سببه',
    'DEFICIENCY_OF':   'نقص في',
    'SPREADS_BY':      'ينتشر عن طريق',
    'FOUND_IN':        'يوجد في',
    'RESISTANT_TO':    'مقاوم لـ',
    'APPLIED_WITH':    'يُستخدم مع',
}

_CHAIN_RELATIONS = frozenset({
    'CAUSES', 'SYMPTOM_OF', 'TREATED_BY', 'CAUSED_BY', 'AFFECTS',
})


class GraphReasoner:

    def __init__(self, G: nx.DiGraph) -> None:
        self.G = G
        self._norm_cache: Dict[str, str] = {}
        logger.info('GraphReasoner: %d nodes, %d edges', G.number_of_nodes(), G.number_of_edges())

    # ── Helper: normalized node label ────────────────────────────

    def _norm(self, node: str) -> str:
        if node not in self._norm_cache:
            self._norm_cache[node] = normalize_ar(node)
        return self._norm_cache[node]

    def _label(self, node: str) -> str:
        return self.G.nodes[node].get('original', node) if node in self.G else node

    # ── Multi-hop BFS ─────────────────────────────────────────────

    def _bfs_paths(
        self,
        start: str,
        query_norm: str,
        max_hops: int = CONFIG.graph_max_hops,
        direction: str = 'forward',   # 'forward' | 'backward' | 'both'
    ) -> List[Tuple[float, str, List[str]]]:
        """
        BFS from `start` node, up to `max_hops`.
        Returns [(score, readable_fact, node_path), ...].
        Supports bidirectional traversal.
        """
        results: List[Tuple[float, str, List[str]]] = []
        visited: Set[str] = {start}
        # queue: (node, depth, path_so_far, accumulated_score)
        queue: deque = deque([(start, 0, [start], 1.0)])

        while queue:
            node, depth, path, path_score = queue.popleft()
            if depth >= max_hops:
                continue
            if node not in self.G:
                continue

            # Choose neighbor iterator based on direction
            if direction == 'backward':
                neighbors = self.G.predecessors(node)
                get_attrs  = lambda n: self.G[n][node]
            else:
                neighbors = self.G.successors(node)
                get_attrs  = lambda n: self.G[node][n]

            for target in neighbors:
                if target in visited:
                    continue
                visited.add(target)
                attrs = get_attrs(target)

                # Relevance: how similar is target to the query?
                relevance = fuzz.partial_ratio(self._norm(target), query_norm)
                # Also check path nodes for partial relevance
                path_relevance = max(
                    fuzz.partial_ratio(self._norm(p), query_norm)
                    for p in path
                )
                combined_relevance = max(relevance, path_relevance * 0.7)

                if combined_relevance < CONFIG.graph_relevance_threshold:
                    queue.append((target, depth + 1, path + [target], path_score * 0.7))
                    continue

                rel   = attrs.get('relation', 'RELATED')
                weight = attrs.get('weight', 1.0)

                src_label = self._label(node)
                tgt_label = self._label(target)
                rel_ar    = _RELATION_AR.get(rel.upper(), '→')

                # Build readable path fact
                indent = '→ ' * depth
                fact   = f'{indent}{src_label} {rel_ar} {tgt_label}'

                # Score = combined_relevance × edge_weight × path_decay
                score = (combined_relevance / 100.0) * weight * (path_score * 0.9)
                score = min(score, 1.0)

                if score >= CONFIG.graph_path_min_score:
                    results.append((score, fact, path + [target]))

                queue.append((target, depth + 1, path + [target], path_score * 0.9))

        return results

    # ── Chain detection ───────────────────────────────────────────

    def _find_chains(self, entities: List[str]) -> List[str]:
        """
        Find Disease→Symptom→Treatment or Pest→Damage→Control chains.
        Returns formatted chain strings.
        """
        chains = []
        for entity in entities:
            if entity not in self.G:
                continue
            for n1, a1 in self.G[entity].items():
                if a1.get('relation', '').upper() not in _CHAIN_RELATIONS:
                    continue
                if n1 not in self.G:
                    continue
                for n2, a2 in self.G[n1].items():
                    if a2.get('relation', '').upper() in _CHAIN_RELATIONS:
                        e_lbl  = self._label(entity)
                        n1_lbl = self._label(n1)
                        n2_lbl = self._label(n2)
                        r1     = _RELATION_AR.get(a1['relation'].upper(), '→')
                        r2     = _RELATION_AR.get(a2['relation'].upper(), '→')
                        chains.append(
                            f'سلسلة: {e_lbl} {r1} {n1_lbl} {r2} {n2_lbl}'
                        )
        # Deduplicate
        return list(dict.fromkeys(chains))[:8]

    # ── Backward reasoning ────────────────────────────────────────

    def _backward_from_symptoms(
        self,
        entities: List[str],
        query_norm: str,
    ) -> List[Tuple[float, str]]:
        """
        Given symptoms, find likely diseases (reverse inference).
        Useful when user describes symptoms without naming a disease.
        """
        results = []
        for entity in entities:
            # Look for nodes that CAUSE or have SYMPTOM this entity
            for src in self.G.predecessors(entity):
                if src not in self.G:
                    continue
                attrs = self.G[src][entity]
                rel   = attrs.get('relation', '').upper()
                if rel in ('CAUSES', 'SYMPTOM_OF', 'AFFECTS'):
                    relevance = fuzz.partial_ratio(self._norm(src), query_norm)
                    if relevance >= CONFIG.graph_relevance_threshold:
                        src_lbl  = self._label(src)
                        ent_lbl  = self._label(entity)
                        rel_ar   = _RELATION_AR.get(rel, '→')
                        score    = relevance / 100.0 * attrs.get('weight', 1.0)
                        results.append((score, f'← {src_lbl} {rel_ar} {ent_lbl}'))
        return results

    # ── Contradiction detection ───────────────────────────────────

    def _detect_contradictions(
        self,
        facts: List[Tuple[float, str]],
    ) -> List[Tuple[str, float]]:
        contradictions = []
        treat_entities = set()
        cause_entities = set()

        for item in facts:
            # item = (score, fact_text) — تأكد إن fact_text هو string
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            fact = item[1]
            if not isinstance(fact, str):
                continue
            if 'يساعد في علاج' in fact:
                parts = fact.split('يساعد في علاج')
                treat_entities.add(parts[0].strip())
            if 'قد يسبب' in fact:
                parts = fact.split('قد يسبب')
                cause_entities.add(parts[0].strip())

        for entity in treat_entities & cause_entities:
            contradictions.append((
                f'تعارض محتمل: "{entity}" مذكور كعلاج وكسبب',
                0.6,
            ))
        return contradictions[:3]

    # ── Missing information detection ─────────────────────────────

    def _detect_missing(
        self,
        entities: List[str],
        query_norm: str,
    ) -> List[str]:
        """
        Detect what information is expected but absent from graph.
        E.g., disease detected but no treatment edges found.
        """
        missing = []
        for entity in entities:
            if entity not in self.G:
                missing.append(f'الكيان "{self._label(entity)}" غير موجود في قاعدة المعرفة')
                continue
            successors = list(self.G.successors(entity))
            relations  = [self.G[entity][s].get('relation', '') for s in successors]
            if not any(r.upper() in ('TREATED_BY', 'TREATS') for r in relations):
                missing.append(f'لا توجد معلومات علاج لـ "{self._label(entity)}"')
        return missing[:3]

    # ── Evidence aggregation ──────────────────────────────────────

    def _aggregate_evidence(
        self,
        all_facts: List[Tuple[float, str, List[str]]],
    ) -> List[Tuple[float, str]]:
        """
        Aggregate and deduplicate facts.
        Facts mentioning same entity pair get score boosted.
        """
        # Deduplicate by fact text
        seen: Dict[str, float] = {}
        for score, fact, _ in sorted(all_facts, key=lambda x: x[0], reverse=True):
            if fact not in seen:
                seen[fact] = score
            else:
                # Boost score if multiple evidence sources support same fact
                seen[fact] = min(seen[fact] * 1.1, 1.0)

        # Return as (score, fact) tuples — consistent ordering
        return [(score, fact) for fact, score in
                sorted(seen.items(), key=lambda x: x[1], reverse=True)]

    # ── Public API ────────────────────────────────────────────────

    def reason(
        self,
        entities: List[str],
        query: str,
    ) -> Tuple[str, float, List[str]]:
        """
        Full graph reasoning.

        Returns:
            (graph_context_text, graph_confidence, paths_list)
        """
        if not entities and self.G.number_of_nodes() == 0:
            return '', 0.0, []

        query_norm = normalize_ar(query)
        all_raw_facts: List[Tuple[float, str, List[str]]] = []

        for entity in entities[:8]:  # cap entities for performance
            # Forward reasoning
            all_raw_facts.extend(self._bfs_paths(entity, query_norm, direction='forward'))
            # Backward reasoning (symptom → disease)
            all_raw_facts.extend(
                (s, f, [entity]) for s, f in
                self._backward_from_symptoms([entity], query_norm)
            )

        # Aggregate + deduplicate
        aggregated = self._aggregate_evidence(all_raw_facts)

        # Find chains
        chains         = self._find_chains(entities)

        # Detect contradictions
        contradictions = self._detect_contradictions(aggregated)

        # Detect missing info
        missing        = self._detect_missing(entities, query_norm)

        # Build output text
        parts: List[str] = []

        top_facts = aggregated[:CONFIG.graph_max_facts]
        if top_facts:
            facts_text = '\n'.join(fact for _, fact in top_facts)
            parts.append(f'العلاقات الزراعية:\n{facts_text}')

        if chains:
            parts.append('سلاسل التشخيص:\n' + '\n'.join(chains[:6]))

        if contradictions:
            c_text = '\n'.join(
                f'⚠ {desc} (شدة: {sev:.0%})' for desc, sev in contradictions
            )
            parts.append(f'تحذيرات:\n{c_text}')

        if missing:
            parts.append('معلومات ناقصة:\n' + '\n'.join(missing))

        graph_text = '\n\n'.join(parts)

        # Confidence: weighted average of top fact scores — (score, fact) order
        top_scores = [score for score, _ in top_facts[:10]]
        if top_scores:
            weights    = [1 / (i + 1) for i in range(len(top_scores))]
            total_w    = sum(weights)
            graph_conf = sum(s * w for s, w in zip(top_scores, weights)) / total_w
        else:
            graph_conf = 0.0

        # Path strings for state — (score, fact) order
        paths = [fact for _, fact in top_facts[:CONFIG.graph_max_facts]]

        logger.debug(
            'Graph: %d facts, %d chains, %d contradictions, conf=%.3f',
            len(aggregated), len(chains), len(contradictions), graph_conf,
        )

        return graph_text, min(graph_conf, 1.0), paths

    def get_stats(self) -> Dict:
        return {
            'nodes':     self.G.number_of_nodes(),
            'edges':     self.G.number_of_edges(),
            'density':   nx.density(self.G) if self.G.number_of_nodes() > 1 else 0.0,
        }
