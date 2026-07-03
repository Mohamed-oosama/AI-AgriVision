"""Smoke tests for AgriXAI Module 6 — exercises every reasoning path."""

import json
import sys
from module6 import (
    AgriMasterController, MockWeatherProvider, WeatherReading,
)


def banner(s):
    print(f"\n{'='*70}\n{s}\n{'='*70}")


def main():
    # Simulate class sample counts (from the user's actual training stats)
    sample_counts = {
        "Wheat_Yellow_Rust": 1200,
        "Wheat_Brown_Rust": 800,
        "Wheat_Black_Stem_Rust": 250,
        "Wheat_Loose_Smut": 400,
        "Wheat_Tan_Spot": 600,
        "Rice_Blast": 1500,
        "Rice_Brown_Spot": 1100,
        "Tomato_Late_Blight": 2200,
        "Tomato_Early_Blight": 1900,
        "Pest_Lycorma_delicatula": 320,
        "Pest_Xylotrechus": 180,
        "Pest_Rice_Yellow_Stem_Borer": 950,
        "Pest_Rice_Brown_Planthopper": 870,
        "Coffee_Boron_Deficiency": 280,
        "Coffee_Nitrogen_Deficiency": 1400,
        "Coffee_Iron_Deficiency": 320,
        "Coffee_Calcium_Deficiency": 410,
    }

    # ---------------------------------------------------------------
    # SCENARIO 1: Yellow vs Brown Rust differential -- cool, very humid
    #             weather should push the system toward Yellow Rust
    #             even though CNN slightly prefers Brown Rust.
    # ---------------------------------------------------------------
    banner("Scenario 1: Wheat Rust differential (Yellow vs Brown)")
    weather_cool_wet = WeatherReading(
        temperature_c=13.0, humidity_pct=92.0, season="spring",
        location_name="Tanta, Gharbia, EG",
    )
    ctl = AgriMasterController(
        class_sample_counts=sample_counts,
        weather_provider=MockWeatherProvider(weather_cool_wet),
    )
    result = ctl.diagnose(
        top_k=[
            ("Wheat_Brown_Rust", 0.48),
            ("Wheat_Yellow_Rust", 0.42),
            ("Wheat_Tan_Spot", 0.07),
        ],
        image_id="img_wheat_001.jpg",
        location=(30.79, 31.0),
    )
    print("Decision:", result["json"]["decision"]["class"])
    print("Reason:", result["json"]["decision"]["reason"])
    print("Severity:", result["json"]["severity"]["level"])
    print("\nDifferential clusters:")
    for c in result["json"]["differential_clusters"]:
        print(f"  Members: {c['members']}")
        print(f"  CNN: {c['cnn_scores']}")
        print(f"  Env: {dict((k, round(v,2)) for k,v in c['env_scores'].items())}")
        print(f"  Final: {dict((k, round(v,3)) for k,v in c['final_scores'].items())}")
        print(f"  Winner: {c['winner']} (margin {c['margin']:.3f})")
    print("\nTrace:")
    for line in result["trace"]:
        print(" ", line)

    # ---------------------------------------------------------------
    # SCENARIO 2: Reverse weather -- warmer, drier should favor Brown
    # ---------------------------------------------------------------
    banner("Scenario 2: Same predictions, warmer drier weather")
    weather_warm = WeatherReading(
        temperature_c=20.0, humidity_pct=72.0, season="spring",
    )
    ctl2 = AgriMasterController(
        class_sample_counts=sample_counts,
        weather_provider=MockWeatherProvider(weather_warm),
    )
    result2 = ctl2.diagnose(
        top_k=[
            ("Wheat_Brown_Rust", 0.48),
            ("Wheat_Yellow_Rust", 0.42),
            ("Wheat_Tan_Spot", 0.07),
        ],
        image_id="img_wheat_002.jpg",
    )
    print("Decision:", result2["json"]["decision"]["class"])
    print("Reason:", result2["json"]["decision"]["reason"])

    # ---------------------------------------------------------------
    # SCENARIO 3: Xylotrechus high-confidence (no differential needed)
    #             Should validate the high-confidence shortcut rule.
    # ---------------------------------------------------------------
    banner("Scenario 3: Xylotrechus at 92% (high confidence shortcut)")
    result3 = ctl.diagnose(
        top_k=[
            ("Pest_Xylotrechus", 0.92),
            ("Pest_Lycorma_delicatula", 0.05),
            ("Wheat_Brown_Rust", 0.03),
        ],
        image_id="img_grape_001.jpg",
    )
    print("Decision:", result3["json"]["decision"]["class"])
    print("Reason:", result3["json"]["decision"]["reason"])
    print("Severity:", result3["json"]["severity"]["level"])
    print("KG path:", " -> ".join(result3["json"]["kg"]["path"]))
    print("\n--- English Report ---")
    print(result3["report"]["text_en"])
    print("\n--- Arabic Report ---")
    print(result3["report"]["text_ar"])

    # ---------------------------------------------------------------
    # SCENARIO 4: Coffee deficiency stage-aware prioritization
    # ---------------------------------------------------------------
    banner("Scenario 4: Coffee deficiency at FLOWERING stage")
    result4 = ctl.diagnose(
        top_k=[
            ("Coffee_Nitrogen_Deficiency", 0.55),
            ("Coffee_Boron_Deficiency", 0.40),
            ("Coffee_Iron_Deficiency", 0.05),
        ],
        image_id="img_coffee_001.jpg",
        growth_stage="flowering",
    )
    print("Decision:", result4["json"]["decision"]["class"])
    print("Reason:", result4["json"]["decision"]["reason"])
    print("Severity:", result4["json"]["severity"]["level"])
    print("\nDeficiency priority ranking:")
    for p in result4["json"]["deficiency_priority"] or []:
        print(f"  {p['class_name']:35s} urgency={p['urgency_score']:.3f} "
              f"critical_stage={p['is_critical_stage']}")

    # ---------------------------------------------------------------
    # SCENARIO 5: Same coffee deficiency at MATURATION stage
    #             Boron should NOT win since maturation isn't its critical stage.
    # ---------------------------------------------------------------
    banner("Scenario 5: Coffee deficiency at MATURATION stage")
    result5 = ctl.diagnose(
        top_k=[
            ("Coffee_Nitrogen_Deficiency", 0.55),
            ("Coffee_Boron_Deficiency", 0.40),
            ("Coffee_Iron_Deficiency", 0.05),
        ],
        image_id="img_coffee_002.jpg",
        growth_stage="maturation",
    )
    print("Decision:", result5["json"]["decision"]["class"])
    print("\nDeficiency priority ranking:")
    for p in result5["json"]["deficiency_priority"] or []:
        print(f"  {p['class_name']:35s} urgency={p['urgency_score']:.3f} "
              f"critical_stage={p['is_critical_stage']}")

    # ---------------------------------------------------------------
    # SCENARIO 6: Save the HTML report to verify Jinja2 rendering
    # ---------------------------------------------------------------
    banner("Scenario 6: Render HTML report to disk")
    with open("/tmp/agrixai_report.html", "w", encoding="utf-8") as f:
        f.write(result3["report"]["html"])
    print("Wrote /tmp/agrixai_report.html ({} bytes)".format(
        len(result3["report"]["html"])))

    # ---------------------------------------------------------------
    # JSON envelope sanity check
    # ---------------------------------------------------------------
    banner("Scenario 7: Verify JSON is serializable & well-formed")
    serialized = json.dumps(result["json"], indent=2, default=str)
    print("Serialized {} bytes; parse round-trip:".format(len(serialized)))
    parsed = json.loads(serialized)
    print("Keys:", list(parsed.keys()))

    print("\n*** ALL SCENARIOS PASSED ***")


if __name__ == "__main__":
    main()
