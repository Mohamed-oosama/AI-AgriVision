"""
differential.py
===============
Differential Diagnosis using KG environmental triggers.

When the CNN's top-k predictions cluster around siblings that the KG marks as
`differential_with` each other (e.g. Yellow Rust vs Brown Rust), raw softmax
confidence is a poor guide -- the network may be torn between visually similar
classes. This module re-ranks them by checking which class's environmental
preconditions match the current weather most closely.

Algorithm
---------
1. Identify "differential clusters" inside the top-k predictions: groups of
   predictions that are mutually marked as `differential_with` in the KG.
2. For each candidate in a cluster, compute an environmental fitness score in
   [0, 1] based on the KG trigger node:
      - temp_c range:        1.0 if inside, else exp-decay outside
      - humidity_pct_min:    1.0 if humidity >= min, else linear penalty
      - season:              1.0 if current matches, 0.5 if unknown, 0 if mismatch
3. Combine with the original CNN confidence using a learned blend `alpha`
   (default 0.6 = 60% CNN, 40% environment). Re-rank.
4. Apply class imbalance correction: rare classes (small `sample_count`) get a
   small boost so they're not buried by frequent classes.
5. Emit a `differential_decision` Fact for the rule engine and downstream XAI.

The result is a *re-weighted* top-k, not a hard override -- the report still
shows the original CNN ranking and explains the adjustment.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log
from typing import Dict, List, Optional, Tuple

import networkx as nx

from .kg_builder import REL_DIFFERENTIAL, get_class_metadata, neighbors_by_relation
from .weather_provider import WeatherReading


@dataclass
class DifferentialResult:
    """Outcome of a differential diagnosis pass."""
    cluster: List[str]                            # the competing classes
    cnn_scores: Dict[str, float]                  # original confidences
    env_scores: Dict[str, float]                  # environmental fitness
    final_scores: Dict[str, float]                # blended
    winner: str
    margin: float                                 # winner - runner-up
    rationale: List[str]                          # human-readable bullets


# ---------------------------------------------------------------------------
# Environmental fitness
# ---------------------------------------------------------------------------

def _temp_score(temp_c: Optional[float], temp_range: Optional[List[float]]) -> float:
    """1.0 inside range, decays exponentially with distance outside."""
    if temp_c is None or not temp_range or len(temp_range) != 2:
        return 0.5  # unknown -> neutral
    lo, hi = temp_range
    if lo <= temp_c <= hi:
        return 1.0
    distance = (lo - temp_c) if temp_c < lo else (temp_c - hi)
    # 5 degrees off = ~0.37, 10 degrees off = ~0.14
    return float(exp(-distance / 5.0))


def _humidity_score(humidity: Optional[float], min_humidity: Optional[float]) -> float:
    if humidity is None or min_humidity is None:
        return 0.5
    if humidity >= min_humidity:
        return 1.0
    # Linear penalty: 20 percentage-points below threshold = 0
    deficit = min_humidity - humidity
    return max(0.0, 1.0 - deficit / 20.0)


def _season_score(current: Optional[str], allowed: Optional[List[str]]) -> float:
    if not allowed:
        return 0.5
    if current is None:
        return 0.5
    if "any" in allowed:
        return 1.0
    return 1.0 if current in allowed else 0.0


def env_fitness(
    g: nx.MultiDiGraph, class_name: str, weather: WeatherReading
) -> Tuple[float, Dict[str, float]]:
    """Return (overall_score, components) for a class given weather."""
    meta = get_class_metadata(g, class_name)
    triggers = meta.get("triggers", {}) or {}

    components = {
        "temp": _temp_score(weather.temperature_c, triggers.get("temp_c")),
        "humidity": _humidity_score(weather.humidity_pct, triggers.get("humidity_pct_min")),
        "season": _season_score(weather.season, triggers.get("season")),
    }
    # Weighted average. Temp and humidity dominate; season is a soft prior.
    overall = (0.4 * components["temp"]
               + 0.4 * components["humidity"]
               + 0.2 * components["season"])
    return overall, components


# ---------------------------------------------------------------------------
# Cluster detection
# ---------------------------------------------------------------------------

def detect_differential_clusters(
    g: nx.MultiDiGraph, top_k: List[Tuple[str, float]]
) -> List[List[str]]:
    """Find subsets of top_k that the KG flags as mutually differential.

    Returns a list of clusters (each a list of class names). A class only
    appears in one cluster. Singletons (no differential siblings in top_k)
    are not returned -- they don't need re-ranking.
    """
    classes = [c for c, _ in top_k]
    clusters: List[List[str]] = []
    seen = set()
    for c in classes:
        if c in seen or c not in g:
            continue
        siblings = set(neighbors_by_relation(g, c, REL_DIFFERENTIAL))
        cluster = [c] + [s for s in classes if s != c and s in siblings]
        if len(cluster) >= 2:
            clusters.append(cluster)
            seen.update(cluster)
    return clusters


# ---------------------------------------------------------------------------
# Imbalance correction
# ---------------------------------------------------------------------------

def imbalance_weight(
    g: nx.MultiDiGraph, class_name: str, gamma: float = 0.15
) -> float:
    """Return a multiplicative correction factor in roughly [0.85, 1.15].

    Rare classes get a small boost; abundant classes a small dampening.
    The shape is log-based so an order-of-magnitude difference shifts the
    weight by ~gamma. With gamma=0.15 the correction is gentle by design --
    we don't want to override a confident CNN call.
    """
    sample_count = (g.nodes.get(class_name, {}) or {}).get("sample_count")
    if not sample_count:
        return 1.0
    # Reference: median class size in your dataset is ~177k/189 ≈ 935
    reference = 935.0
    return float(1.0 + gamma * log(reference / sample_count) / log(10))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def resolve_differential(
    g: nx.MultiDiGraph,
    top_k: List[Tuple[str, float]],
    weather: WeatherReading,
    alpha: float = 0.5,
) -> List[DifferentialResult]:
    """Run differential diagnosis on the top-k predictions.

    Parameters
    ----------
    alpha : float
        Base blend weight between CNN and environmental signals.
        final = alpha * cnn + (1 - alpha) * env_fitness, then * imbalance_weight.
        When the CNN's top-2 inside a cluster are within 0.10 of each other,
        we adaptively reduce alpha by 0.15 — a torn network is exactly when
        the KG should get more authority.

    Returns
    -------
    list[DifferentialResult]
        One per detected cluster. May be empty if no cluster found.
    """
    cnn_scores = {c: float(p) for c, p in top_k}
    clusters = detect_differential_clusters(g, top_k)
    results: List[DifferentialResult] = []

    for cluster in clusters:
        env_scores: Dict[str, float] = {}
        env_components: Dict[str, Dict[str, float]] = {}
        for cls in cluster:
            score, comps = env_fitness(g, cls, weather)
            env_scores[cls] = score
            env_components[cls] = comps

        # Adaptive alpha: if the CNN is torn (small gap), trust env more.
        sorted_cnn = sorted([cnn_scores[c] for c in cluster], reverse=True)
        cnn_gap = sorted_cnn[0] - sorted_cnn[1] if len(sorted_cnn) >= 2 else 1.0
        local_alpha = alpha - 0.15 if cnn_gap < 0.10 else alpha
        local_alpha = max(0.25, min(0.85, local_alpha))

        final: Dict[str, float] = {}
        for cls in cluster:
            blended = local_alpha * cnn_scores[cls] + (1 - local_alpha) * env_scores[cls]
            final[cls] = blended * imbalance_weight(g, cls)

        ranked = sorted(final.items(), key=lambda kv: kv[1], reverse=True)
        winner = ranked[0][0]
        margin = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)

        rationale = _build_rationale(
            cluster, cnn_scores, env_scores, env_components, final,
            winner, weather, g, local_alpha,
        )
        results.append(DifferentialResult(
            cluster=cluster,
            cnn_scores={c: cnn_scores[c] for c in cluster},
            env_scores=env_scores,
            final_scores=final,
            winner=winner,
            margin=margin,
            rationale=rationale,
        ))
    return results


def _build_rationale(
    cluster, cnn_scores, env_scores, env_components, final, winner,
    weather: WeatherReading, g: nx.MultiDiGraph, alpha_used: float,
) -> List[str]:
    bullets = []
    cnn_top = max(cluster, key=lambda c: cnn_scores[c])
    bullets.append(
        f"CNN initially favored {cnn_top} ({cnn_scores[cnn_top]:.0%}); "
        f"siblings in dispute: {', '.join(c for c in cluster if c != cnn_top)}."
    )
    bullets.append(
        f"Weather snapshot: T={weather.temperature_c}°C, "
        f"RH={weather.humidity_pct}%, season={weather.season or 'unknown'}."
    )
    bullets.append(
        f"Blend weight α={alpha_used:.2f} (lower α = more KG authority)."
    )
    for cls in cluster:
        triggers = get_class_metadata(g, cls).get("triggers", {})
        bullets.append(
            f"{cls}: trigger window T={triggers.get('temp_c')}, "
            f"RH≥{triggers.get('humidity_pct_min')}, season={triggers.get('season')} "
            f"-> env fit {env_scores[cls]:.2f}, final {final[cls]:.3f}."
        )
    if winner != cnn_top:
        bullets.append(
            f"Decision: re-ranked from {cnn_top} to {winner} -- "
            f"environmental conditions favor the latter."
        )
    else:
        bullets.append(f"Decision: {winner} confirmed (CNN and KG agree).")
    return bullets
