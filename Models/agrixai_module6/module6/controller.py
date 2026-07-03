"""
controller.py
=============
AgriMasterController — public entrypoint for AgriXAI Module 6.

Usage from your inference pipeline:

    from module6 import AgriMasterController, MockWeatherProvider

    controller = AgriMasterController(
        class_sample_counts=train_counts,           # for imbalance correction
        weather_provider=MockWeatherProvider(),     # swap for real provider later
    )

    top_k = [("Wheat_Yellow_Rust", 0.51),
             ("Wheat_Brown_Rust",  0.39),
             ("Wheat_Tan_Spot",    0.06)]

    result = controller.diagnose(
        top_k=top_k,
        image_id="img_0042.jpg",
        location=(31.0, 31.0),       # optional, passed to weather provider
        growth_stage="flowering",     # optional
    )

    result["json"]                    # structured payload for the UI
    result["report"]["html"]          # ready-to-render Jinja2 HTML
    result["report"]["text_en"]
    result["report"]["text_ar"]

Pipeline stages
---------------
1. Build / reuse KG.
2. Pull weather (allow override).
3. Run the rule engine over the top-k:
     - cluster differential candidates
     - resolve them with weather + imbalance weights
     - pick a 'final winner' per cluster
4. For deficiency winners, apply growth-stage prioritization.
5. Compute Economic Threshold severity for the top winner.
6. Build the bilingual XAI report.
7. Emit a structured JSON envelope for the UI.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import logging

from .kg_builder import build_graph, get_class_metadata, traverse_path
from .rule_engine import Engine, Fact, Rule, WorkingMemory
from .differential import resolve_differential, DifferentialResult
from .deficiency_matrix import prioritize_deficiencies
from .yield_impact import YieldImpactCalculator
from .weather_provider import (
    WeatherProvider, MockWeatherProvider, WeatherReading
)
from .xai_report import ReportPayload, render_full_report

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

def _rule_high_confidence_pass(wm: WorkingMemory):
    """If the top prediction is already > 0.85, no differential needed."""
    top = wm.first("top_prediction")
    if top and top["confidence"] > 0.85:
        return {"top": top}
    return None

def _action_high_confidence_pass(wm: WorkingMemory, b: Dict) -> List[Fact]:
    return [Fact(kind="final_decision",
                 class_name=b["top"]["class_name"],
                 confidence=b["top"]["confidence"],
                 reason="single high-confidence prediction (>85%)",
                 differential_used=False)]


def _rule_invoke_differential(wm: WorkingMemory):
    """If no final_decision yet AND there's a differential cluster -> resolve."""
    if wm.exists("final_decision"):
        return None
    cluster_fact = wm.first("differential_cluster")
    if cluster_fact:
        return {"cluster": cluster_fact}
    return None

def _action_invoke_differential(wm: WorkingMemory, b: Dict) -> List[Fact]:
    diff: DifferentialResult = b["cluster"]["result"]
    return [Fact(kind="final_decision",
                 class_name=diff.winner,
                 confidence=diff.final_scores[diff.winner],
                 reason="differential diagnosis (KG + weather)",
                 differential_used=True,
                 cluster=diff.cluster,
                 margin=diff.margin)]


def _rule_default_to_top(wm: WorkingMemory):
    """Last-resort: if nothing else fired, accept the top-1 CNN prediction."""
    if wm.exists("final_decision"):
        return None
    top = wm.first("top_prediction")
    if top:
        return {"top": top}
    return None

def _action_default_to_top(wm: WorkingMemory, b: Dict) -> List[Fact]:
    return [Fact(kind="final_decision",
                 class_name=b["top"]["class_name"],
                 confidence=b["top"]["confidence"],
                 reason="top-1 CNN prediction (no differential cluster)",
                 differential_used=False)]


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class AgriMasterController:
    """High-level orchestrator. Stateless across calls (the KG is held once)."""

    def __init__(
        self,
        class_sample_counts: Optional[Dict[str, int]] = None,
        weather_provider: Optional[WeatherProvider] = None,
        kg_facts: Optional[Dict] = None,
        et_table_path: Optional[str] = None,
    ) -> None:
        self.kg = build_graph(facts=kg_facts, class_sample_counts=class_sample_counts)
        self.weather = weather_provider or MockWeatherProvider()
        self.yield_calc = YieldImpactCalculator(et_table_path=et_table_path)

    # ---- main entry point -------------------------------------------------

    def diagnose(
        self,
        top_k: List[Tuple[str, float]],
        image_id: Optional[str] = None,
        location: Optional[Tuple[float, float]] = None,
        growth_stage: Optional[str] = None,
        weather_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the full Cognitive Layer pipeline.

        Parameters
        ----------
        top_k : list of (class_name, confidence)
            Output of your EfficientNet inference, sorted descending.
        image_id : str
            Optional identifier for tracing/logging.
        location : (lat, lon)
            Passed to the weather provider.
        growth_stage : str
            One of 'vegetative' | 'flowering' | 'fruit_set' | 'maturation'.
            Used by deficiency prioritization. Falls back to weather provider
            if it can supply a stage.
        weather_override : dict
            If supplied, bypass the provider and use this dict.

        Returns
        -------
        dict with keys: 'json' (UI payload), 'report' (text_en/text_ar/html),
        'trace' (rule firing log).
        """
        if not top_k:
            return self._empty_result(image_id, "no predictions supplied")

        # ---- 1. weather ---------------------------------------------------
        if weather_override:
            from .weather_provider import DictWeatherProvider
            weather = DictWeatherProvider(weather_override).get()
        else:
            lat, lon = (location or (None, None))
            weather = self.weather.get(lat=lat, lon=lon)
        # Caller's explicit growth_stage takes priority over provider defaults
        # (the provider may not actually know — it could be a static mock or
        # a weather API that has no agronomic context).
        if growth_stage:
            weather.growth_stage = growth_stage

        # ---- 2. differential cluster detection & resolution ---------------
        differential_results = resolve_differential(self.kg, top_k, weather)

        # ---- 3. rule engine to pick the final decision --------------------
        engine = Engine()
        engine.add_rule(Rule(
            "high_confidence_pass",
            _rule_high_confidence_pass, _action_high_confidence_pass,
            salience=100,
        ))
        engine.add_rule(Rule(
            "invoke_differential",
            _rule_invoke_differential, _action_invoke_differential,
            salience=50,
        ))
        engine.add_rule(Rule(
            "default_to_top",
            _rule_default_to_top, _action_default_to_top,
            salience=10,
        ))

        engine.assert_facts([
            Fact(kind="top_prediction", class_name=c, confidence=p)
            for c, p in top_k
        ])
        engine.assert_facts([
            Fact(kind="differential_cluster", classes=d.cluster, result=d)
            for d in differential_results
        ])
        engine.run()

        final_fact = engine.wm.first("final_decision")
        if final_fact is None:
            return self._empty_result(image_id, "rule engine produced no decision")

        winner_class = final_fact["class_name"]
        winner_conf = float(final_fact["confidence"])

        # ---- 4. deficiency prioritization (if applicable) -----------------
        winner_meta = get_class_metadata(self.kg, winner_class)
        category = winner_meta.get("category", "disease")
        deficiency_priority = None
        if category == "deficiency":
            def_candidates = [
                (c, p) for c, p in top_k
                if get_class_metadata(self.kg, c).get("category") == "deficiency"
            ]
            if def_candidates:
                deficiency_priority = prioritize_deficiencies(
                    def_candidates, weather.growth_stage, self.kg
                )
                # If stage-aware ranking changed the winner, honor it.
                if deficiency_priority and deficiency_priority[0].class_name != winner_class:
                    winner_class = deficiency_priority[0].class_name
                    winner_conf = deficiency_priority[0].cnn_confidence
                    winner_meta = get_class_metadata(self.kg, winner_class)
                    category = "deficiency"
                    final_fact["class_name"] = winner_class
                    final_fact["confidence"] = winner_conf
                    final_fact["reason"] = (
                        "stage-aware deficiency prioritization "
                        f"(growth stage = {weather.growth_stage})"
                    )
                    final_fact["differential_used"] = True

        # ---- 5. economic threshold / severity -----------------------------
        damage_pct = winner_meta.get("damage_pct_untreated_15d")
        impact = self.yield_calc.assess(
            class_name=winner_class,
            category=category,
            confidence=winner_conf,
            expected_damage_pct=damage_pct,
        )

        # ---- 6. XAI report ------------------------------------------------
        payload = self._build_payload(
            winner_class, winner_conf, winner_meta, weather,
            differential_results, impact,
        )
        rendered = render_full_report(payload)

        # ---- 7. structured JSON for the UI --------------------------------
        ui_json = self._to_ui_json(
            image_id, top_k, winner_class, winner_conf,
            winner_meta, impact, differential_results,
            deficiency_priority, weather, final_fact,
        )

        return {
            "json": ui_json,
            "report": rendered,
            "trace": engine.trace,
        }

    # ---- helpers ----------------------------------------------------------

    def _build_payload(
        self,
        class_name: str,
        confidence: float,
        meta: Dict,
        weather: WeatherReading,
        differentials: List[DifferentialResult],
        impact,
    ) -> ReportPayload:
        # Find the differential result this class belongs to (if any) for
        # the rationale block.
        rationale_lines = []
        for d in differentials:
            if class_name in d.cluster:
                rationale_lines = d.rationale
                break

        controls = meta.get("controls", {}) or {}
        weather_summary_parts = []
        if weather.temperature_c is not None:
            weather_summary_parts.append(f"{weather.temperature_c:.1f}°C")
        if weather.humidity_pct is not None:
            weather_summary_parts.append(f"{weather.humidity_pct:.0f}% RH")
        if weather.season:
            weather_summary_parts.append(weather.season)
        weather_summary = ", ".join(weather_summary_parts)

        return ReportPayload(
            class_name=class_name,
            label_en=meta.get("label", class_name),
            label_ar=meta.get("label_ar", ""),
            confidence=confidence,
            category=meta.get("category", "disease"),
            kg_path_en=traverse_path(self.kg, class_name),
            pathogens=meta.get("pathogens", []),
            triggers=meta.get("triggers", {}) or {},
            biological_controls=controls.get("biological", []),
            chemical_controls=controls.get("chemical", []),
            cultural_controls=controls.get("cultural", []),
            predators=meta.get("predators", []),
            damage_pct_15d=float(meta.get("damage_pct_untreated_15d") or 0),
            severity=impact.severity,
            differential_explanation=rationale_lines,
            yield_rationale=impact.rationale,
            weather_summary=weather_summary,
        )

    def _to_ui_json(
        self,
        image_id, top_k, winner_class, winner_conf, winner_meta,
        impact, differentials, deficiency_priority, weather, final_fact,
    ) -> Dict[str, Any]:
        return {
            "image_id": image_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "top_k_input": [{"class": c, "confidence": float(p)} for c, p in top_k],
            "decision": {
                "class": winner_class,
                "label_en": winner_meta.get("label", winner_class),
                "label_ar": winner_meta.get("label_ar", ""),
                "category": winner_meta.get("category"),
                "confidence": winner_conf,
                "reason": final_fact.get("reason"),
                "differential_used": bool(final_fact.get("differential_used")),
            },
            "severity": {
                "level": impact.severity,
                "expected_damage_pct": impact.expected_damage_pct,
                "economic_threshold_pct": impact.economic_threshold_pct,
                "expected_loss_usd_ha": impact.expected_loss_usd_ha,
                "intervention_cost_usd_ha": impact.intervention_cost_usd_ha,
                "benefit_cost_ratio": impact.benefit_cost_ratio,
                "confidence_gate_passed": impact.confidence_gate_passed,
            },
            "differential_clusters": [
                {
                    "members": d.cluster,
                    "winner": d.winner,
                    "margin": d.margin,
                    "cnn_scores": d.cnn_scores,
                    "env_scores": d.env_scores,
                    "final_scores": d.final_scores,
                }
                for d in differentials
            ],
            "deficiency_priority": (
                [asdict(p) for p in deficiency_priority] if deficiency_priority else None
            ),
            "weather": weather.to_dict(),
            "kg": {
                "path": traverse_path(self.kg, winner_class),
                "pathogens": winner_meta.get("pathogens", []),
                "triggers": winner_meta.get("triggers", {}),
                "controls": winner_meta.get("controls", {}),
                "predators": winner_meta.get("predators", []),
                "differential_siblings": winner_meta.get("differential_siblings", []),
            },
        }

    def _empty_result(self, image_id: Optional[str], reason: str) -> Dict[str, Any]:
        return {
            "json": {
                "image_id": image_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "decision": None,
                "error": reason,
            },
            "report": {"text_en": f"No diagnosis: {reason}",
                       "text_ar": f"لا يوجد تشخيص: {reason}",
                       "html": f"<html><body><p>No diagnosis: {reason}</p></body></html>"},
            "trace": [],
        }
