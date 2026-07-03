# AgriXAI Module 6 — Knowledge Graph & Explainable Reasoning

The Cognitive Layer that sits on top of your EfficientNet-B3 dual-head model.
Takes top-k predictions, reasons over a hierarchical NetworkX KG, breaks ties
with weather + KG facts, computes economic-threshold severity, and emits a
structured JSON envelope plus a bilingual (Arabic / English) HTML report.

## Architecture

```
inference.py (Module 5: Vision)
     │  top_k = [(class, confidence), ...]
     ▼
┌─────────────────────────────────────────────────────────────┐
│               AgriMasterController.diagnose()               │
│                                                             │
│   ┌─────────────────┐    ┌──────────────────────────────┐   │
│   │ WeatherProvider │───►│ Differential Diagnosis        │   │
│   │ (pluggable)     │    │  • cluster detection (KG)    │   │
│   └─────────────────┘    │  • env-fitness scoring        │   │
│                          │  • imbalance correction       │   │
│                          │  • adaptive α blend           │   │
│                          └──────────────┬────────────────┘   │
│                                         ▼                   │
│   ┌─────────────────┐    ┌──────────────────────────────┐   │
│   │ Hierarchical KG │───►│ Rule Engine                   │   │
│   │ (NetworkX)      │    │  • high_confidence_pass       │   │
│   │  ROOT           │    │  • invoke_differential        │   │
│   │  └─Category     │    │  • default_to_top             │   │
│   │    └─Family     │    └──────────────┬────────────────┘   │
│   │      └─Crop     │                   ▼                   │
│   │        └─Class  │    ┌──────────────────────────────┐   │
│   │          ├─Pathogen │ Deficiency Stage Prioritizer  │   │
│   │          ├─Trigger  │  (only if winner is deficiency)│   │
│   │          ├─Control  └──────────────┬────────────────┘   │
│   │          ├─Predator                ▼                   │
│   │          └─Differential   ┌──────────────────────┐    │
│   └─────────────────┘         │ YieldImpactCalculator │    │
│                               │  ET lookup + severity │    │
│                               └──────────┬────────────┘    │
│                                          ▼                  │
│                              ┌────────────────────────┐    │
│                              │ XAI Report (Jinja2)    │    │
│                              │  text_en, text_ar, html │    │
│                              └────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              { "json": {...}, "report": {...}, "trace": [...] }
```

## File layout

```
module6/
├── __init__.py
├── kg_builder.py          # Hierarchical NetworkX KG + traversal helpers
├── rule_engine.py         # Forward-chaining engine (Experta replacement)
├── differential.py        # Yellow-vs-Brown-Rust style tie-breaking
├── deficiency_matrix.py   # Stage-aware coffee/maize/rice prioritization
├── yield_impact.py        # Economic Threshold severity grading
├── weather_provider.py    # Pluggable weather interface
├── xai_report.py          # Bilingual narrative + Jinja2 HTML
├── controller.py          # AgriMasterController (public entrypoint)
└── data/
    ├── kg_facts.json      # Pathogen → triggers, hosts, controls (seed)
    └── economic_thresholds.json   # ET table (seed + category fallback)
```

## Why a custom rule engine instead of Experta?

Experta depends on `frozendict` in a way that breaks on Python 3.10+; Colab now
ships 3.11 by default. We built a small forward-chaining engine
(~150 lines) with explicit salience and fixed-point convergence. For Module 6
we have <50 rules and <200 facts at any time, so the naive O(rules × facts)
match per cycle is fast enough and dramatically easier to debug than RETE.
Each rule fires at most once per `engine.run()`; call `engine.reset()` for a
new diagnosis.

## Imbalance handling

Your dataset spans an 11x range across the 189 classes. Two safeguards:

1. **Differential blend** — `imbalance_weight()` in `differential.py` gives
   rare classes a small (~±15%) multiplicative boost, log-scaled against the
   median class size of 935 images. A 200-image class gets ~+10%; a 5,000-image
   class gets ~−11%. Gentle by design — we don't want to override a confident
   CNN call.

2. **Confidence gating in ET** — every class entry in `economic_thresholds.json`
   has a `min_confidence_for_alert`. If the CNN's confidence falls below that
   threshold (more likely on rare classes), severity is downgraded from
   `warning`/`critical` to `watch`.

## Integrating with your existing pipeline

```python
# In your Colab notebook, after model.predict():

from module6 import AgriMasterController, MockWeatherProvider, WeatherReading

# Build once and reuse — KG construction is ~5ms but unnecessary per call.
controller = AgriMasterController(
    class_sample_counts=train_class_counts,   # the dict you compute in datasets.py
    weather_provider=MockWeatherProvider(),   # swap to real provider in production
)

# Per inference:
top5 = [(IDX_TO_CLASS[i], float(p)) for i, p in zip(top5_idx, top5_probs)]
out = controller.diagnose(
    top_k=top5,
    image_id=image_path.name,
    location=(lat, lon),
    growth_stage="flowering",   # if known from user input
)

ui_payload = out["json"]               # send to your front-end
html_report = out["report"]["html"]    # render in webview
print(out["report"]["text_ar"])        # for the Arabic side
```

## Wiring a real weather provider

Subclass `WeatherProvider` and implement `.get(lat, lon)`:

```python
import requests
from module6 import WeatherProvider, WeatherReading

class OpenWeatherMapProvider(WeatherProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get(self, lat=None, lon=None):
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"},
            timeout=5,
        ).json()
        return WeatherReading(
            temperature_c=r["main"]["temp"],
            humidity_pct=r["main"]["humidity"],
            wind_kmh=r["wind"]["speed"] * 3.6,
            location_name=r.get("name"),
        )

controller = AgriMasterController(
    class_sample_counts=train_counts,
    weather_provider=OpenWeatherMapProvider(api_key=os.environ["OWM_KEY"]),
)
```

## Extending the KG

`module6/data/kg_facts.json` currently seeds the high-value classes you called
out (wheat rusts, rice borers, *Lycorma delicatula*, *Xylotrechus*, coffee
deficiencies). For the long tail of 189 classes, add entries in the same
schema. Classes without entries fall back to the category-level node in the
KG and the category-level fallback in `economic_thresholds.json`, so the
system keeps working — it just can't reason about their specific triggers.

A pragmatic plan: seed the 30–40 most economically important classes by hand;
write a script that mines the rest from a structured agronomic database
(EPPO Global Database is free for non-commercial use and has Latin names +
hosts + controls).

## Limits of the current design

- **No hyphal staging.** Diseases don't have lifecycle nodes; we treat them
  as point-in-time detections. If you want "early infection" vs "late necrosis"
  reasoning, add a `stage` attribute on the class node.
- **Damage estimates are heuristic.** `damage_pct_untreated_15d` values were
  seeded conservatively from extension-service literature. For a real
  deployment, calibrate them from your own field-trial data.
- **No uncertainty propagation.** The confidence number is the CNN softmax
  probability; we don't propagate epistemic uncertainty through the rule
  engine. If you add MC-dropout or deep ensembles later, surface the std-dev
  in the JSON envelope and lower severity when it's high.

## Dependencies

- `networkx >= 3.0`
- `Jinja2 >= 3.0`

That's it. No Experta, no `frozendict`, no `clips`, no RETE library.
