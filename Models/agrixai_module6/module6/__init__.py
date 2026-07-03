"""
AgriXAI Module 6 — Knowledge Graph & Explainable Reasoning (Cognitive Layer).

Public API:
    AgriMasterController         -- main orchestrator
    MockWeatherProvider          -- pluggable weather (default for testing)
    DictWeatherProvider          -- weather from a plain dict
    WeatherProvider, WeatherReading -- interface + data class

    build_graph                  -- construct the NetworkX KG directly
    YieldImpactCalculator        -- direct ET access if needed
"""

from .controller import AgriMasterController
from .weather_provider import (
    WeatherProvider, MockWeatherProvider, DictWeatherProvider, WeatherReading
)
from .kg_builder import build_graph, get_class_metadata, traverse_path
from .yield_impact import YieldImpactCalculator, YieldImpactResult
from .differential import resolve_differential, DifferentialResult
from .deficiency_matrix import prioritize_deficiencies, PrioritizedDeficiency
from .xai_report import ReportPayload, render_full_report

__all__ = [
    "AgriMasterController",
    "WeatherProvider", "MockWeatherProvider", "DictWeatherProvider", "WeatherReading",
    "build_graph", "get_class_metadata", "traverse_path",
    "YieldImpactCalculator", "YieldImpactResult",
    "resolve_differential", "DifferentialResult",
    "prioritize_deficiencies", "PrioritizedDeficiency",
    "ReportPayload", "render_full_report",
]

__version__ = "1.0.0"
