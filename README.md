# AI AgriVision 🌾🤖

<div align="center">

**An Intelligent Multi-Module Agricultural Diagnosis and Advisory System for Egyptian and Arab Agriculture**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1%2B-orange)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Arabic](https://img.shields.io/badge/Language-Arabic%20%7C%20English-brightgreen)]()

<img src="docs/images/agrivision_banner.png" alt="AI AgriVision Banner" width="800"/>

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Six AI Modules](#-six-ai-modules)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Datasets](#-datasets)
- [Results & Performance](#-results--performance)
- [Project Structure](#-project-structure)
- [Technology Stack](#-technology-stack)
- [Contributors](#-contributors)
- [Supervisors](#-supervisors)
- [Acknowledgments](#-acknowledgments)
- [License](#-license)
- [Future Work](#-future-work)
- [Contact](#-contact)

---

## 🎯 Overview

**AI AgriVision** is a comprehensive, locally-deployable intelligent agricultural platform specifically designed for the **Egyptian and Arab agricultural context**. The platform integrates **six complementary AI modules** that address different dimensions of agricultural intelligence — from plant disease diagnosis and bilingual agricultural Q&A to soil fertilization recommendations, crop yield prediction, environmental stress monitoring, and explainable treatment recommendations.

### Why AI AgriVision?

- 🌍 **Bilingual**: Full support for **Modern Standard Arabic (MSA)**, **Egyptian colloquial Arabic**, and **English**
- 💻 **Locally Deployable**: Runs entirely on local hardware via **Ollama** — no cloud dependency, no data privacy concerns
- 🧠 **Explainable AI**: Every prediction comes with visual explanations (Grad-CAM), economic justifications (BCR), or source citations (RAG)
- 📊 **Validated Performance**: All six modules meet or exceed their target metrics on held-out test sets
- 🌱 **Impact-Driven**: Projected **+20% yield increase**, **-32.5% crop loss reduction**, and **-20% input cost savings**

> 🎓 **Graduation Project** — Artificial Intelligence Engineering Program  
> 🏛️ **Faculty of Engineering, Mansoura National University**  
> 📅 **Academic Year 2025–2026**

---

## ✨ Key Features

| Feature | Description | Module |
|---------|-------------|--------|
| 🔬 **Plant Disease Diagnosis** | Dual-head CNN (EfficientNet-B3) for hierarchical classification into 3 categories + fine-grained diseases | M2 |
| 💬 **Bilingual Agricultural Chat** | Hybrid RAG system with Knowledge Graph for Arabic/English agricultural Q&A | M5 |
| 🧪 **Soil Fertilization Advisor** | QLoRA fine-tuned Mistral-7B for Arabic fertilizer recommendations | M4 |
| 📈 **Crop Yield Prediction** | Random Forest + Gradient Boosting ensemble with climate scenario analysis | M3 |
| 🚨 **Vegetation Stress Early Warning** | ML ensemble for monitoring Egypt's 31 protected areas | M6 |
| 🧠 **Cognitive Reasoning Layer** | KG-augmented explainable treatment with economic severity grading | M1 |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI AgriVision — Central Platform                    │
│                    (FastAPI + LangGraph + Ollama)                     │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │  M2     │  │  M5     │  │  M4     │  │  M3     │  │  M6     │  │
│  │ AgriXAI │  │AgriChat │  │Agrivision│  │Egypt FAO│  │ EWS-PA  │  │
│  │  CNN    │  │ Hybrid  │  │   LLM   │  │  Yield  │  │  EWS    │  │
│  │Diagnosis│  │   RAG   │  │Fertilizer│  │Predictor│  │ Monitor │  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  │
│       │            │            │            │            │       │
│  ┌────┴────────────┴────────────┴────────────┴────────────┴────┐  │
│  │                    M1 — AgriXAI Cognitive Layer                 │  │
│  │         (Knowledge Graph + Rules + Explainability)              │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  React.js Web   │
                    │    Frontend     │
                    │ (Arabic/English)│
                    └─────────────────┘
```

### Deployment Architecture
- **Local-first**: Single-machine deployment via Ollama
- **Microservices**: Each module runs as independent Python process
- **REST APIs**: Standardized JSON input/output across all modules
- **Streaming**: Server-Sent Events (SSE) for conversational interactions

---

## 🔬 Six AI Modules

### Module 2 — AgriXAI v2: Plant Disease Diagnosis System 🌿

**Technology**: EfficientNet-B3 Dual-Head CNN + XAI  
**Primary Metric**: Category Accuracy **92.56%** (Target: ≥90%)

A dual-head convolutional neural network that simultaneously performs:
- **Category-level classification**: Disease / Pest / Deficiency
- **Fine-grained classification**: Specific disease or pest species

**Explainability Features**:
- Grad-CAM heatmaps highlighting disease-affected regions
- Gradient saliency maps
- Intermediate feature maps (4 panels)
- Confidence-gap warning for uncertain predictions

```python
# Example API Call
POST /diagnose
{
  "image": "tomato_leaf.jpg"
}

# Response
{
  "category": "Disease",
  "fine_class": "disease::tomato__late_blight",
  "confidence": 0.923,
  "grad_cam": "base64_encoded_image",
  "saliency_map": "base64_encoded_image",
  "warning": null
}
```

---

### Module 5 — AgriChat: Bilingual Hybrid RAG System 💬

**Technology**: FAISS + Knowledge Graph + LLaMA 3  
**Primary Metric**: Hybrid RAG Score **0.803** (+15.21% vs Vector-only)

A bilingual Arabic-English agricultural advisory chatbot combining:
- **Dense vector retrieval** via FAISS (28,613 text chunks)
- **Knowledge Graph traversal** via NetworkX (4,243 nodes, 4,233 edges)
- **Five-agent pipeline**: Classifier → Entity Extractor → FAISS Retriever → KG Traversal → Synthesis

**Corpus**: 28,613 clean text chunks (80.6% English, 19.4% Arabic) from FAO, MALR Egypt, and agricultural reference books.

```python
# Example API Call
POST /chat
{
  "message": "ما هي أفضل أسمدة النيتروجين للقمح؟",
  "history": []
}

# Response
{
  "answer": "...",
  "sources": ["chunk_1", "chunk_2", ...],
  "graph_rels": ["Wheat → REQUIRES → Nitrogen", ...],
  "response_time": "2.3s"
}
```

---

### Module 4 — AI Agrivision: Fertilization Recommendation System 🧪

**Technology**: Mistral-7B-Instruct + QLoRA Fine-Tuning  
**Primary Metric**: ROUGE-1 F1 **0.531** (Target: ≥0.50)

A QLoRA fine-tuned large language model for **Arabic-language soil fertilization recommendations** tailored to Egyptian farming conditions.

**Training Data**: 61,791 records integrating:
- Kaggle agricultural datasets
- Egyptian Ministry of Agriculture and Land Reclamation (MALR) soil standards
- FAO Egypt data

```python
# Example API Call
POST /fertilize
{
  "crop": "طماطم",
  "N": 80,
  "P": 40,
  "K": 90,
  "pH": 6.5,
  "location": "الدلتا"
}

# Response
{
  "recommendation_ar": "...",
  "recommendation_en": "...",
  "confidence": 0.86
}
```

---

### Module 3 — Egypt FAO: Crop Yield Prediction System 📈

**Technology**: Random Forest + Gradient Boosting Ensemble  
**Primary Metric**: R² = **0.9904** (Target: ≥0.95)

An ensemble machine learning system trained on **FAOSTAT data (1961–2024)** for Egyptian crop yield forecasting.

**Climate Scenarios Analyzed**:
| Scenario | Description | Avg Impact |
|----------|-------------|------------|
| Baseline | Historical average | 0% |
| Heatwave +2°C | Temperature increase | -1.2% to -1.6% |
| Drought -20% | Reduced inputs | -0.6% to -1.7% |
| Combined Stress | Heatwave + Drought | -0.7% to -3.4% |
| Tech + Green | Precision farming | +1.7% to +2.5% |

```python
# Example API Call
POST /predict_yield
{
  "crop": "wheat",
  "year": 2026,
  "climate_params": {
    "temp_anomaly": 1.5,
    "precipitation": 120,
    "nitrogen_used": 150
  }
}

# Response
{
  "yield_kg_ha": 18450,
  "confidence_interval": [18200, 18700],
  "scenario": "expected"
}
```

---

### Module 6 — EWS-PA v2.3: Vegetation Stress Early Warning System 🚨

**Technology**: XGBoost + Random Forest + Logistic Regression Ensemble  
**Primary Metric**: ROC-AUC = **0.817** (Target: ≥0.80)

A three-branch fusion Early Warning System for **Egypt's 31 protected areas**, combining:
- Rule-based EWS v1 logic
- ML ensemble with Platt probability calibration
- NDVI anomaly detection via per-area rolling baselines

**Dataset**: 5,192 labelled observations (7.9% positive stress rate)

```python
# Example API Call
POST /ews/check
{
  "area_id": 27,
  "ndvi": 0.35,
  "weather": {
    "temperature": 44.5,
    "humidity": 30,
    "soil_moisture": 0.025
  }
}

# Response
{
  "stress_label": "Low Stress",
  "probability": 0.096,
  "severity": "Healthy",
  "branch": "v2_high_conf",
  "recommended_actions": ["Routine monitoring"]
}
```

---

### Module 1 — AgriXAI Cognitive: Explainable Reasoning Layer 🧠

**Technology**: Knowledge Graph + Rule Engine + Economic Analysis  
**Primary Metric**: 100% Test Pass Rate (7/7 scenarios)

A Knowledge Graph-augmented cognitive reasoning layer that transforms raw CNN predictions into **economically-grounded, actionable treatment recommendations**.

**Pipeline Stages**:
1. Weather Acquisition (0.1ms)
2. Differential Diagnosis (0.1ms)
3. Rule Engine Execution (0.5ms)
4. Deficiency Priority (0.1ms)
5. Yield Impact Assessment (0.9ms)
6. XAI Report Generation (5.0ms)
7. JSON Envelope

**Total Latency**: **9.8ms** (warm) — well under 15ms target

```python
# Example API Call
POST /explain
{
  "top_k_predictions": [
    {"class": "disease::wheat__yellow_rust", "confidence": 0.48},
    {"class": "disease::wheat__brown_rust", "confidence": 0.42}
  ],
  "weather": {"temperature": 13, "humidity": 92, "season": "spring"}
}

# Response
{
  "winner": "disease::wheat__yellow_rust",
  "severity": "CRITICAL",
  "BCR": 7.0,
  "xai_report_html": "..."
}
```

---

## 🚀 Installation

### Prerequisites

- Python 3.9+
- CUDA-capable GPU (recommended) or CPU fallback
- 8GB+ RAM (16GB recommended)
- 6GB+ VRAM for LLM inference (with 4-bit quantization)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/AI-AgriVision.git
cd AI-AgriVision
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install Ollama (for Local LLM Inference)

```bash
# On Linux
curl -fsSL https://ollama.com/install.sh | sh

# On macOS
brew install ollama

# On Windows
# Download from https://ollama.com/download
```

### Step 5: Pull Required Models

```bash
ollama pull llama3:8b
ollama pull qwen2.5:3b
ollama pull mistral:7b
```

### Step 6: Download Datasets

```bash
# Run the dataset preparation script
python scripts/download_datasets.py

# Or manually download from:
# - PlantVillage: https://github.com/spMohanty/PlantVillage-Dataset
# - FAOSTAT: https://www.fao.org/faostat
# - MALR Egypt publications (see docs/DATASETS.md)
```

### Step 7: Start the Platform

```bash
# Start Ollama server
ollama serve

# In a new terminal, start the main platform
python main.py

# Or start individual modules
python modules/m2_cnn/app.py      # Plant Diagnosis
python modules/m5_rag/app.py       # AgriChat
python modules/m4_llm/app.py      # Fertilization
python modules/m3_yield/app.py    # Yield Prediction
python modules/m6_ews/app.py      # Early Warning
python modules/m1_cognitive/app.py # Cognitive Layer
```

The web interface will be available at: **http://localhost:8000**

---

## 💻 Usage

### Web Interface

1. Open your browser and navigate to `http://localhost:8000`
2. Select your preferred language (Arabic/English)
3. Choose a module from the dashboard:
   - 🔬 **Analyze a Plant** — Upload leaf images for disease diagnosis
   - 🧪 **Soil Analysis** — Get fertilizer recommendations
   - 📈 **Yield Predictor** — Forecast crop yields under climate scenarios
   - 💬 **AI Chat** — Ask agricultural questions in Arabic or English
   - 🚨 **Early Warning System** — Monitor protected area vegetation stress

### API Usage

All modules expose REST APIs. See the [API Documentation](#-api-documentation) section for details.

### Example: Complete Workflow

```python
import requests

# Step 1: Diagnose a plant image
with open("tomato_leaf.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/diagnose",
        files={"image": f}
    )
diagnosis = response.json()

# Step 2: Get explainable treatment recommendation
explain_response = requests.post(
    "http://localhost:8000/explain",
    json={
        "top_k_predictions": [
            {"class": diagnosis["fine_class"], "confidence": diagnosis["confidence"]}
        ],
        "weather": {"temperature": 25, "humidity": 60}
    }
)
treatment = explain_response.json()

# Step 3: Get detailed advisory from AgriChat
chat_response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": f"How to treat {diagnosis['fine_class']} organically?",
        "history": []
    }
)
advisory = chat_response.json()

print(f"Diagnosis: {diagnosis['fine_class']}")
print(f"Severity: {treatment['severity']}")
print(f"Treatment: {advisory['answer']}")
```

---

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

| Method | Endpoint | Module | Description |
|--------|----------|--------|-------------|
| POST | `/diagnose` | M2 | Plant disease diagnosis from image |
| POST | `/chat` | M5 | Bilingual agricultural Q&A |
| POST | `/chat/stream` | M5 | Streaming conversational response |
| POST | `/fertilize` | M4 | Soil fertilization recommendation |
| POST | `/predict_yield` | M3 | Crop yield prediction |
| POST | `/ews/check` | M6 | Vegetation stress detection |
| POST | `/explain` | M1 | Explainable treatment recommendation |
| GET | `/health` | ALL | System health check |

### Detailed API Docs

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 📊 Datasets

### Module 2 — Plant Disease (AgriXAI v2)

| Dataset | Size | Source |
|---------|------|--------|
| PlantVillage | 54,000 images | [GitHub](https://github.com/spMohanty/PlantVillage-Dataset) |
| Cassava Leaf Disease | 21,397 images | [Kaggle](https://www.kaggle.com/c/cassava-leaf-disease-classification) |
| Wheat Disease | 3,602 images | [Kaggle](https://www.kaggle.com/datasets/xpwu95/wheat-disease-dataset) |
| IP102 (Pests) | 75,222 images | [GitHub](https://github.com/xpwu95/IP102) |
| Custom Pest Collection | ~5,000 images | Internal collection |
| PlantDoc Deficiency | ~2,500 images | [GitHub](https://github.com/pratikkayal/PlantDoc-Dataset) |
| MALR Egypt Deficiency | ~1,800 images | Internal field collection |

### Module 5 — AgriChat Corpus

| Source | Language | Chunks |
|--------|----------|--------|
| FAO Crop Production & Plant Protection | English | ~4,200 |
| MALR Egypt Extension Manual | Arabic | ~3,100 |
| Integrated Pest Management Handbook | English+Arabic | ~2,400 |
| Soil Fertility and Fertilization Guide | Arabic | ~2,100 |
| Plant Pathology Reference (Arabic) | English | ~1,900 |
| FAOSTAT Technical Documentation | Arabic | ~1,800 |
| Irrigation and Water Management (Egypt) | English/Arabic | ~10,313 |
| **Total** | **Bilingual** | **28,613** |

### Module 4 — Fertilization

| Source | Records | Features |
|--------|---------|----------|
| Kaggle Crop Recommendation | 2,200 | N, P, K, temp, humidity, pH, rainfall |
| Kaggle Fertilizer Prediction | 99 | Soil + crop → fertilizer |
| Kaggle Fertilizer Recommendation | 26,741 | NPK + soil + fertilizer mapping |
| Mendeley Soil Dataset | 3,142 | Soil properties + recommendations |
| FAO Egypt | 1,958 | FAOSTAT-aligned Egyptian data |
| MALR Egypt Synthetic | 25,451 | Egyptian NPK + soil + crop |
| **Total** | **61,791** | **23 features** |

### Module 3 — Yield Prediction

| Dataset | Records | Years | Source |
|---------|---------|-------|--------|
| FAOSTAT Crop Production Egypt | 15,000+ | 1961–2024 | [FAO](https://www.fao.org/faostat) |
| FAO Temperature Anomaly | ~2,500 | 1961–2024 | [FAO](https://www.fao.org/faostat) |
| FAO Precipitation Data | ~2,500 | 1961–2024 | [FAO](https://www.fao.org/faostat) |
| FAO Pesticide Use Egypt | ~1,500 | 1990–2024 | [FAO](https://www.fao.org/faostat) |
| FAO Fertilizer Consumption | ~1,500 | 1990–2024 | [FAO](https://www.fao.org/faostat) |

### Module 6 — EWS-PA

| Data Type | Source | Coverage |
|-----------|--------|----------|
| NDVI Index | Landsat-8/9 + MODIS | 2010–2024, 31 PAs |
| Temperature | ERA5 Reanalysis | 2010–2024, monthly |
| Precipitation | ERA5 Reanalysis | 2010–2024, monthly |
| Soil Moisture | ERA5-Land | 2010–2024, monthly |
| Solar Radiation | ERA5 Reanalysis | 2010–2024, monthly |
| PA Boundaries | IUCN WDPA | 31 areas |

---

## 📈 Results & Performance

### Consolidated Module Performance

| Module | System | Primary Metric | Achieved | Target | Status |
|--------|--------|----------------|----------|--------|--------|
| M2 | AgriXAI CNN | Category Accuracy | **92.56%** | ≥ 90% | ✅ Exceeded |
| M2 | AgriXAI CNN | Category F1-Score | **0.9113** | ≥ 0.90 | ✅ Exceeded |
| M5 | AgriChat RAG | Hybrid RAG Score | **0.803** | ≥ 0.75 | ✅ Exceeded |
| M5 | AgriChat RAG | vs Vector Baseline | **+15.21%** | — | ✅ Exceeded |
| M4 | Agrivision LLM | ROUGE-1 F1 | **0.531** | ≥ 0.50 | ✅ Met |
| M4 | Agrivision LLM | Confidence Score | **86%** | ≥ 80% | ✅ Met |
| M3 | Egypt FAO Yield | R-squared (RF) | **0.9904** | ≥ 0.95 | ✅ Exceeded |
| M3 | Egypt FAO Yield | RMSE (RF) | **405 kg/ha** | < 500 | ✅ Met |
| M6 | EWS-PA v2.3 | PR-AUC | **0.6736** | ≥ 0.60 | ✅ Met |
| M6 | EWS-PA v2.3 | ROC-AUC | **0.8167** | ≥ 0.80 | ✅ Met |
| M1 | AgriXAI Cognitive | Test Pass Rate | **100%** (7/7) | 100% | ✅ Perfect |
| M1 | AgriXAI Cognitive | Pipeline Latency | **9.8ms** | < 15ms | ✅ Met |

### Agricultural Impact Projections (2025–2035)

| Metric | Expected Scenario | Optimistic Scenario |
|--------|-------------------|---------------------|
| Yield Increase | **+20%** | +35% |
| Crop Loss Reduction | **-32.5%** | — |
| Input Cost Savings | **-20%** | — |
| Water Efficiency | **+30%** | — |

---

## 📁 Project Structure

```
AI-AgriVision/
├── 📁 modules/
│   ├── m1_cognitive/          # AgriXAI Cognitive Reasoning Layer
│   │   ├── knowledge_graph/
│   │   ├── rule_engine/
│   │   ├── differential.py
│   │   └── app.py
│   │
│   ├── m2_cnn/                # AgriXAI v2 Plant Diagnosis
│   │   ├── models/
│   │   │   └── efficientnet_b3_dualhead.py
│   │   ├── training/
│   │   ├── xai/
│   │   │   ├── gradcam.py
│   │   │   └── saliency.py
│   │   └── app.py
│   │
│   ├── m3_yield/              # Egypt FAO Crop Yield Prediction
│   │   ├── data/
│   │   ├── models/
│   │   │   ├── random_forest.py
│   │   │   └── gradient_boosting.py
│   │   ├── climate_scenarios/
│   │   └── app.py
│   │
│   ├── m4_llm/                # AI Agrivision Fertilization LLM
│   │   ├── qlora/
│   │   ├── inference/
│   │   └── app.py
│   │
│   ├── m5_rag/                # AgriChat Hybrid RAG
│   │   ├── corpus/
│   │   │   └── s5_final.json
│   │   ├── embeddings/
│   │   ├── knowledge_graph/
│   │   │   └── knowledge_graph.json
│   │   ├── agents/
│   │   └── app.py
│   │
│   └── m6_ews/                # EWS-PA v2.3 Early Warning
│       ├── data/
│       ├── models/
│       │   ├── xgboost_model.py
│       │   ├── random_forest.py
│       │   └── logistic_regression.py
│       └── app.py
│
├── 📁 frontend/               # React.js Web Interface
│   ├── src/
│   ├── public/
│   └── package.json
│
├── 📁 docs/                   # Documentation
│   ├── images/
│   ├── API.md
│   ├── DATASETS.md
│   └── DEPLOYMENT.md
│
├── 📁 scripts/                # Utility Scripts
│   ├── download_datasets.py
│   ├── build_kg.py
│   └── evaluate_all.py
│
├── 📁 tests/                  # Test Suites
│   ├── unit/
│   ├── integration/
│   └── smoke/
│
├── 📁 notebooks/              # Jupyter Notebooks
│   ├── analysis/
│   └── visualization/
│
├── main.py                    # Central Platform Entry Point
├── config.yaml                # Global Configuration
├── requirements.txt           # Python Dependencies
├── Dockerfile                 # Container Configuration
├── docker-compose.yml         # Multi-Service Orchestration
└── README.md                  # This File
```

---

## 🛠️ Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **ML Framework** | PyTorch | 2.1+ | CNN training and inference |
| **LLM Inference** | Ollama | Latest | Local LLM serving |
| **LLM Framework** | LangChain / LangGraph | 0.1+ | Agent orchestration |
| **Vector Search** | FAISS (faiss-cpu) | 1.7+ | Semantic retrieval |
| **Graph Library** | NetworkX | 3.x | Knowledge Graph traversal |
| **Embeddings** | HuggingFace sentence-transformers | Latest | Multilingual embeddings |
| **Web Framework** | Flask 2.x / FastAPI | Latest | REST API serving |
| **Explainability** | SHAP (TreeExplainer) | Latest | Feature importance |
| **Data Processing** | Pandas + NumPy + Scikit-learn | Latest | ML pipelines |
| **Visualization** | Matplotlib + D3.js + Chart.js | Latest | Figures and dashboards |
| **Frontend** | React.js + Tailwind CSS | 18+ | Web interface |
| **Training Platform** | Google Colab (T4/A100 GPU) | — | Model training |
| **Deployment** | Docker + Ollama | — | Local deployment |

---

## 👥 Contributors

This project was developed by the AI AgriVision Team from the **Artificial Intelligence Engineering Program, Faculty of Engineering, Mansoura National University**:

| Name | Role | Contributions |
|------|------|---------------|
| **Ibrahim Mohamed Mohamed Amin** | Team Lead | System Architecture, Module Integration |
| **Mohamed Osama Kamel** | ML Engineer | Module 2 (CNN), Module 1 (Cognitive) |
| **Mohamed Mahmoud Ashraf Hosny Ellakany** | NLP Engineer | Module 5 (RAG), Module 4 (LLM) |
| **Mohamed Ashraf Fawzy Aldanin** | Data Engineer | Module 3 (Yield), Data Pipeline |
| **Mohamed Ali Ali Ail Shatla** | Backend Engineer | Module 6 (EWS), API Development |
| **Badr Islam Ibrahim Elewa** | Frontend Engineer | React.js Web Interface, UI/UX |

---

## 👨‍🏫 Supervisors

- **Dr. Mohamed Zaki** — Associate Professor, AI Engineering Program
- **Eng. Mennatallah Ouf** — Teaching Assistant, AI Engineering Program

---

## 🙏 Acknowledgments

We express our deepest gratitude to:

- **Prof. Dr. Ehab Hani Abdelhay** — Acting Dean, Faculty of Engineering, Mansoura National University
- **Faculty of Engineering, Mansoura National University** — For providing an exceptional academic environment
- **Food and Agriculture Organization (FAO)** — For maintaining the FAOSTAT database
- **Egyptian Ministry of Agriculture and Land Reclamation (MALR)** — For crop-specific fertilization guidelines
- **Open-Source Community** — PyTorch, Hugging Face Transformers, LangChain, Ollama, FAISS, NetworkX, Scikit-learn, XGBoost

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🔮 Future Work

### Short-Term (6–12 months)
- [ ] Expand AgriChat corpus with 20–30 additional agricultural reference books
- [ ] Collect 500+ additional stress-positive observations for EWS-PA
- [ ] Develop React Native mobile application with offline caching
- [ ] Implement CrossEncoder reranker for Knowledge Graph relations

### Medium-Term (1–2 years)
- [ ] Real-time IoT integration for EWS-PA (soil sensors, meteorological stations)
- [ ] Federated learning deployment across agricultural extension offices
- [ ] Image-integrated RAG (accept crop images alongside text queries)
- [ ] Arabic dialect expansion (Saidi, Alexandrian, etc.)

### Long-Term Research Directions
- [ ] Satellite time series integration (Sentinel-2 NDVI) for sub-field yield mapping
- [ ] Knowledge Graph alignment with FAO AGROVOC multilingual thesaurus
- [ ] Cross-border extension to Jordanian, Libyan, and Moroccan agriculture

---

## 📞 Contact

For questions, suggestions, or collaboration inquiries:

- 📧 **Email**: agrivision@mnu.edu.eg
- 🌐 **Website**: [https://agrivision.mnu.edu.eg](https://agrivision.mnu.edu.eg)
- 🐙 **GitHub**: [https://github.com/yourusername/AI-AgriVision](https://github.com/yourusername/AI-AgriVision)
- 📱 **LinkedIn**: [AI AgriVision Project](https://linkedin.com/company/agrivision)

---

<div align="center">

**Made with ❤️ in Egypt 🇪🇬 for Arab Farmers 🌾**

*"Bridging Technology & Traditional Agriculture"*

</div>
