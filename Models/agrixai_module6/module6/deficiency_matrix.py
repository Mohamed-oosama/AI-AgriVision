"""
deficiency_matrix.py
====================
Growth-stage-aware prioritization for nutrient deficiencies.

When the model returns multiple deficiency candidates (Nitrogen vs Boron vs
Iron, etc.), raw confidence isn't enough — the *current growth stage* changes
which deficiency is most damaging right now. Boron during flowering is far
more critical than Boron during vegetative growth, even at lower confidence.

This module exposes a single function:

    prioritize_deficiencies(
        candidates: list[(class_name, confidence)],
        growth_stage: str,
        kg: nx.MultiDiGraph,
    ) -> list[PrioritizedDeficiency]

It returns the candidates re-ordered by *clinical urgency* (a blend of
confidence, KG-defined critical stage matching, and the class's untreated
damage estimate).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import networkx as nx

from .kg_builder import get_class_metadata


# Stage-aware urgency multipliers. Tunable.
STAGE_MATCH_BONUS = 1.5      # if current stage is in class's critical_growth_stages
STAGE_MISMATCH_PENALTY = 0.7  # if current stage is known and not critical
DEFAULT_DAMAGE_PCT = 12.0    # if KG missing, treat as moderate


@dataclass
class PrioritizedDeficiency:
    class_name: str
    cnn_confidence: float
    urgency_score: float       # final ranking key
    is_critical_stage: bool
    damage_pct_untreated: float
    rationale: str


def prioritize_deficiencies(
    candidates: List[Tuple[str, float]],
    growth_stage: str | None,
    kg: nx.MultiDiGraph,
) -> List[PrioritizedDeficiency]:
    """Re-rank deficiency candidates by stage-aware urgency.

    `candidates` should already be filtered to deficiency classes.
    """
    out: List[PrioritizedDeficiency] = []

    for class_name, conf in candidates:
        meta = get_class_metadata(kg, class_name)
        critical_stages = meta.get("critical_growth_stages") or []
        damage = meta.get("damage_pct_untreated_15d") or DEFAULT_DAMAGE_PCT

        if growth_stage and critical_stages:
            if growth_stage in critical_stages:
                stage_factor = STAGE_MATCH_BONUS
                is_critical = True
                stage_note = f"current stage '{growth_stage}' IS critical for this nutrient"
            else:
                stage_factor = STAGE_MISMATCH_PENALTY
                is_critical = False
                stage_note = (
                    f"current stage '{growth_stage}' is not in critical window "
                    f"({', '.join(critical_stages)})"
                )
        else:
            stage_factor = 1.0
            is_critical = False
            stage_note = "growth stage unknown — using neutral weight"

        # urgency = confidence * stage_factor * (damage_pct / 20)
        # The /20 normaliser keeps the urgency loosely on a 0–1 scale.
        urgency = float(conf) * stage_factor * (damage / 20.0)

        out.append(PrioritizedDeficiency(
            class_name=class_name,
            cnn_confidence=float(conf),
            urgency_score=urgency,
            is_critical_stage=is_critical,
            damage_pct_untreated=float(damage),
            rationale=(f"conf={conf:.2f} × stage_factor={stage_factor:.2f} "
                       f"× damage_norm={damage/20:.2f}; {stage_note}"),
        ))

    out.sort(key=lambda d: d.urgency_score, reverse=True)
    return out
