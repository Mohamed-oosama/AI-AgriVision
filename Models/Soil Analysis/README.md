# 🌱 AI Agrivision — Soil Fertilization Recommendation System

> **Graduation Project | 2024–2025**
> Fine-tuning Mistral-7B with QLoRA for intelligent crop & fertilizer recommendations tailored to Egyptian agriculture

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Mistral-7B](https://img.shields.io/badge/Model-Mistral--7B--Instruct-orange)
![QLoRA](https://img.shields.io/badge/Fine--tuning-QLoRA%204bit-green)
![Colab](https://img.shields.io/badge/Platform-Google%20Colab-F9AB00?logo=googlecolab&logoColor=white)
![License](https://img.shields.io/badge/License-Academic%20Use%20Only-red)

---

## 📌 Project Overview

AI Agrivision is an AI-powered soil recommendation system that helps Egyptian farmers make data-driven decisions about crop selection and fertilizer usage. The system fine-tunes **Mistral-7B-Instruct** using **QLoRA (4-bit quantization)** on a curated dataset of **61,791 agricultural records** spanning **78 crop types** and **7 data sources** — including official Egyptian Ministry of Agriculture (MALR) data.

The model receives soil analysis inputs (N, P, K, pH, temperature, humidity, rainfall, soil type) and returns structured **Arabic-language recommendations** tailored to Egyptian agricultural conditions.

---

## 📁 Repository Structure

```
Soil-Firltlization-project-/
│
├── EDA/                                    # Exploratory Data Analysis
│   └── soil_EDA_en.ipynb                   # Full EDA notebook (English)
│
├── TRAINNIG/                               # Model Fine-tuning
│   └── mistral_qlora_soil_fresh.ipynb      # QLoRA training pipeline (Google Colab)
│
├── data cleaning/                          # Data Preprocessing
│   └── data_cleaning.ipynb                 # Cleaning, merging & balancing pipeline
│
├── webapp_updated.rar                      # Web Application (Flask + Arabic UI)
│
└── README.md
```

> **Note:** Dataset files (`train.jsonl`, `val.jsonl`, `test.jsonl`) are stored on Google Drive due to size — see [Getting Started](#-getting-started-google-colab).

---

## 📊 Dataset

### Overview

| Property        | Value                                 |
|-----------------|---------------------------------------|
| Total Records   | 61,791                                |
| Crop Types      | 78                                    |
| Data Sources    | 5 (merged from 7 original)            |
| Features        | 12 raw + 11 engineered                |
| Missing Values  | 0 (complete dataset)                  |
| Class Imbalance | ×6 (after balancing, down from ×129)  |

### Data Sources

| Source | Records | Type | Notes |
|--------|---------|------|-------|
| Kaggle – Fertilizer Recommendation | 26,694 | Global | Largest source |
| MALR Egypt (Ministry of Agriculture) | 24,783 | 🇪🇬 Egyptian Official | Core Egyptian context |
| Kaggle – Crop Recommendation | 6,561 | Global (India-based) | Foundation source |
| Kaggle – Fertilizer Prediction | 1,914 | Global | Fertilizer diversity |
| Kaggle – Soil Nutrients | 1,839 | Global | Nutrient variety |

> Egyptian data represents ~40% of the dataset — ensuring the model is grounded in local agricultural context while maintaining broad global coverage.

### Feature Columns

| Column | Type | Description |
|--------|------|-------------|
| `nitrogen` | float | N content in soil (kg/ha) |
| `phosphorus` | float | P content in soil (kg/ha) |
| `potassium` | float | K content in soil (kg/ha) |
| `ph` | float | Soil pH (0–14) |
| `temperature` | float | Temperature (°C) |
| `humidity` | float | Relative humidity (%) |
| `rainfall` | float | Annual rainfall (mm) |
| `moisture` | float | Soil moisture (%) |
| `crop` | string | Target crop type |
| `fertilizer` | string | Recommended fertilizer |
| `soil_type` | string | Soil texture class |
| `source` | string | Data origin tag |

---

## 🔬 EDA — Key Findings

Full technical details in [`EDA/soil_EDA_en.ipynb`](./EDA/).

### 1. NPK Correlations (The Golden Triangle)

| Pair  | Correlation (r) | Interpretation |
|-------|-----------------|----------------|
| N ↔ P | +0.63 | Soils rich in N tend to be rich in P |
| P ↔ K | +0.57 | Compound fertilizers (NPK, DAP) raise both together |
| N ↔ K | +0.48 | Lower correlation — K depends more on parent rock type |

### 2. Feature Importance (Random Forest)

| Rank | Feature | Importance | Cumulative |
|------|---------|------------|------------|
| 1 | Nitrogen (N) | 0.220 | 22.0% |
| 2 | Potassium (K) | 0.175 | 39.5% |
| 3 | Phosphorus (P) | 0.166 | 56.1% |
| 4 | Humidity | 0.116 | 67.7% |
| 5 | Temperature | 0.111 | 78.8% |
| 6 | Rainfall | 0.085 | 87.3% |
| 7 | Soil pH | 0.073 | 94.6% |
| 8 | Soil Moisture | 0.053 | 100% |

> pH ranks 7th in importance but acts as a **fertility gatekeeper** — high pH (> 7.5) can nullify the effect of all elements above it in alkaline Egyptian soils.

### 3. Engineered Features (11 derived)

| Category | Feature | Formula |
|----------|---------|---------|
| NPK Ratios | `n_p_ratio`, `n_k_ratio`, `k_p_ratio` | N÷P, N÷K, K÷P |
| Fertility | `total_npk`, `fertility_index` | N+P+K, weighted score |
| Climate | `heat_index`, `water_stress` | Temp×Humidity, Rainfall÷(Temp×2+1) |
| Season | `season_winter`, `season_summer`, `season_spring` | Binary flags (28/35/15 crops) |

---

## 🤖 Model Fine-Tuning

### Architecture

| Component | Value |
|-----------|-------|
| Base Model | `mistralai/Mistral-7B-Instruct-v0.2` |
| Fine-tuning Method | QLoRA (4-bit NF4 quantization) |
| LoRA Rank (r) | 16 |
| LoRA Alpha | 32 |
| LoRA Dropout | 0.05 |
| Target Modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Trainable Parameters | ~41M out of 7B total (0.59%) |

### Training Configuration

| Hyperparameter | Value |
|----------------|-------|
| Epochs | 3 |
| Batch Size | 4 (A100) / 2 (T4) — auto-detected |
| Gradient Accumulation | 4 / 8 → effective batch = 16 |
| Learning Rate | 2e-4 (cosine scheduler) |
| Warmup Ratio | 0.05 |
| Max Sequence Length | 512 tokens |
| Weight Decay | 0.01 |
| Gradient Clipping | 1.0 |
| Precision | bf16 (A100) / fp16 (T4) |
| Checkpointing | Every 200 steps → Google Drive |

### Prompt Format

```
[INST] {instruction}

{input} [/INST]
{output}</s>
```

**Example:**
```
[INST] لدي تربة زراعية اريد زراعة قمح فيها في الموسم الشتوي.
التحليل: N=100 kg/ha, P=25 kg/ha, K=0 kg/ha, pH=7.8
نوع التربة: طينية لومية. اعداد ورقة توصية. [/INST]
```

---

## 🚀 Getting Started (Google Colab)

### Prerequisites

- Google account with Google Drive access
- Hugging Face account with access to `mistralai/Mistral-7B-Instruct-v0.2`
- Colab GPU runtime (T4 minimum, A100 recommended)
- HuggingFace token saved in Colab Secrets as `HF_TOKEN`

### Steps

**1. Upload dataset to Google Drive**

Place these files in `MyDrive/finetune_data/`:
```
MyDrive/
└── finetune_data/
    ├── train.jsonl
    ├── val.jsonl
    └── test.jsonl
```

**2. Open the training notebook**

Open `TRAINNIG/mistral_qlora_soil_fresh.ipynb` in Google Colab and run all cells top to bottom (Steps 0–14).

**3. What the notebook does automatically:**
- ✅ Installs all required libraries
- ✅ Mounts Google Drive and copies data locally
- ✅ Logs into Hugging Face via Colab Secrets
- ✅ Detects your GPU and adjusts batch size accordingly
- ✅ Loads Mistral-7B in 4-bit and applies QLoRA from scratch
- ✅ Saves checkpoints to Drive every 200 steps
- ✅ Evaluates with ROUGE scores and plots training curves

**4. Inference example**

```python
model.eval()

def ask(instruction, max_new_tokens=512):
    prompt = f"[INST] {instruction} [/INST]"
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=400).to("cuda")
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.1,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
        )
    return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

print(ask("تحليل تربة قصب السكر صيفي: N=180 P=50 K=80 pH=7.2. ما التوصية؟"))
```

---

## 🌐 Web Application

The project includes a full web application (`webapp_updated.rar`) with an Arabic-language interface for farmers to enter soil analysis data and receive fertilizer recommendations.

### Extract & Run

```bash
# Extract the archive
unrar x webapp_updated.rar

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Then open `http://localhost:5000` in your browser.

---

## 📈 Evaluation

The model is evaluated using **ROUGE scores** on a 50-sample held-out test set:

| Metric | Measures |
|--------|----------|
| ROUGE-1 | Unigram overlap with reference output |
| ROUGE-2 | Bigram overlap (phrase-level accuracy) |
| ROUGE-L | Longest common subsequence (structural similarity) |

Training curves (loss vs. steps) are automatically saved to `training_curves.png` in the output directory on Drive.

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| Base Model | Mistral-7B-Instruct-v0.2 |
| Fine-tuning | QLoRA via PEFT + TRL |
| Quantization | BitsAndBytes (4-bit NF4) |
| Training Framework | Hugging Face Transformers + SFTTrainer |
| Data Processing | Pandas, NumPy |
| EDA & Visualization | Matplotlib, Seaborn, Plotly |
| Web App | Flask + Arabic UI |
| Compute | Google Colab (T4 / A100 / L4) |
| Storage | Google Drive |
| Evaluation | ROUGE Score |

### Key Library Versions

```
numpy          1.26.4
transformers   4.44.2
peft           0.12.0
trl            0.9.6
accelerate     0.33.0
datasets       2.20.0
bitsandbytes   latest (nvidia index)
```

---

## ⚠️ Important Notes

**On outliers:** High NPK values for crops like sugarcane (N=380 kg/ha) and banana (N=1,070 kg/ha) are **not data errors** — they reflect genuine agronomic requirements and must remain in the dataset.

**On Egyptian alkaline soils:** Most Egyptian soils have pH 7.0–8.0. Nutrients may be *present* but *unavailable* at high pH — the model accounts for this when generating recommendations.

**On class balancing:** Original dataset had ×129 class imbalance. After balancing: ×6 — acceptable for LLM fine-tuning.

**On training from scratch:** The notebook (`mistral_qlora_soil_fresh.ipynb`) always starts fresh from the base Mistral-7B model. There is no dependency on any pre-existing checkpoint.

---

## 📄 License

This project is a graduation thesis submission for the AI Agrivision Project (2024–2025).
**Academic use only — not for commercial distribution.**

---

## 👥 Authors

**AI Agrivision Team** — Graduation Project 2024–2025

---

*"The data is ready. The model is trained. The farmer is empowered."*
