"""
yield_impact.py
===============
Economic-Threshold-driven severity ranking.

The Economic Threshold (ET) is the % yield loss at which the cost of
intervention equals the value of saved yield. Below ET the rational call is
"monitor" or "no action"; above ET the call becomes "intervene".

We expose:
    YieldImpactCalculator(et_table_path)
        .assess(class_name, confidence, expected_damage_pct=None) -> YieldImpactResult

The calculator looks up the class-specific ET, falls back to category defaults
for the long tail of 189 classes, and downgrades severity when CNN confidence
falls below the class's `min_confidence_for_alert`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import json
import logging

log = logging.getLogger(__name__)


@dataclass
class YieldImpactResult:
    class_name: str
    severity: str                       # 'info' | 'watch' | 'warning' | 'critical'
    expected_damage_pct: float
    economic_threshold_pct: float
    expected_loss_usd_ha: float
    intervention_cost_usd_ha: float
    benefit_cost_ratio: float           # loss_avoided / intervention_cost
    is_above_threshold: bool
    confidence_gate_passed: bool
    rationale: str


class YieldImpactCalculator:
    """Economic threshold lookup and severity grading."""

    SEVERITY_ORDER = ("info", "watch", "warning", "critical")

    def __init__(self, et_table_path: Optional[str | Path] = None) -> None:
        if et_table_path is None:
            et_table_path = Path(__file__).parent / "data" / "economic_thresholds.json"
        with open(et_table_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._fallback = data.pop("_meta", {}).get("fallback", {})
        self._table: Dict[str, Dict] = data

    def _entry_for(self, class_name: str, category: str) -> Dict:
        if class_name in self._table:
            return self._table[class_name]
        fb = self._fallback.get(category) or self._fallback.get("disease", {})
        log.debug("ET fallback used for %s (%s)", class_name, category)
        return fb

    def assess(
        self,
        class_name: str,
        category: str,
        confidence: float,
        expected_damage_pct: Optional[float] = None,
    ) -> YieldImpactResult:
        entry = self._entry_for(class_name, category)
        et_pct = float(entry.get("et_pct", 12))
        cost = float(entry.get("intervention_cost_usd_ha", 80))
        yield_value = float(entry.get("yield_value_usd_ha", 1500))
        min_conf = float(entry.get("min_confidence_for_alert", 0.55))

        # If caller didn't supply a damage estimate, use a heuristic:
        # damage scales with confidence and a category-specific anchor.
        if expected_damage_pct is None:
            anchor = {"disease": 25.0, "pest": 22.0, "deficiency": 15.0}.get(category, 20.0)
            expected_damage_pct = anchor * float(confidence)

        loss_usd = (expected_damage_pct / 100.0) * yield_value
        bcr = (loss_usd / cost) if cost > 0 else 0.0
        confidence_gate = confidence >= min_conf
        above_et = expected_damage_pct >= et_pct

        # Severity grading: a 2-D matrix over (above_et, confidence_gate).
        if above_et and confidence_gate:
            severity = "critical" if bcr >= 2.0 else "warning"
        elif above_et and not confidence_gate:
            severity = "watch"
        elif not above_et and confidence_gate:
            severity = "watch"
        else:
            severity = "info"

        rationale = (
            f"Expected damage {expected_damage_pct:.1f}% vs ET {et_pct:.1f}%; "
            f"loss ${loss_usd:.0f}/ha vs cost ${cost:.0f}/ha (BCR={bcr:.2f}); "
            f"confidence {confidence:.0%} {'≥' if confidence_gate else '<'} "
            f"alert threshold {min_conf:.0%}."
        )

        return YieldImpactResult(
            class_name=class_name,
            severity=severity,
            expected_damage_pct=float(expected_damage_pct),
            economic_threshold_pct=et_pct,
            expected_loss_usd_ha=loss_usd,
            intervention_cost_usd_ha=cost,
            benefit_cost_ratio=bcr,
            is_above_threshold=above_et,
            confidence_gate_passed=confidence_gate,
            rationale=rationale,
        )
