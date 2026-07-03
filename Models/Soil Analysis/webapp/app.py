import os
import torch
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pandas as pd
import math
import re
app = FastAPI(title="Soil Recommendation Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
PARENT_DIR = os.path.dirname(BASE_DIR)
ADAPTER_PATH = os.path.join(PARENT_DIR, "final")
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

model = None
tokenizer = None
crop_data = {}

def load_dataset():
    global crop_data
    try:
        csv_path = r"C:\Users\BADR ISLAM ELEWA\Downloads\merged_dataset_enriched.csv"
        df = pd.read_csv(csv_path)
        grouped = df.groupby('crop')[['nitrogen', 'phosphorus', 'potassium', 'ph', 'temperature', 'humidity', 'rainfall', 'season_spring', 'season_summer', 'season_winter']].mean()
        crop_data = grouped.to_dict('index')
        print(f"Loaded statistics for {len(crop_data)} crops.")
    except Exception as e:
        print(f"Error loading dataset: {e}")

def load_model():
    global model, tokenizer
    print("Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            cache_dir=r"C:\Users\BADR ISLAM ELEWA\.cache\huggingface\hub",
            trust_remote_code=True,
            use_fast=False
        )
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = 'right'
        
        print("Loading base model in 4-bit...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type='nf4',
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        
        base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            cache_dir=r"C:\Users\BADR ISLAM ELEWA\.cache\huggingface\hub",
            quantization_config=bnb_config,
            device_map='auto',
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            attn_implementation='eager'
        )
        base_model.config.use_cache = False
        base_model.config.pretraining_tp = 1
        
        print(f"Loading LoRA weights from {ADAPTER_PATH}...")
        model = PeftModel.from_pretrained(
            base_model,
            ADAPTER_PATH,
        )
        model.eval()
        print("Model ready!")
    except Exception as e:
        print(f"Error loading model: {e}")

class SoilData(BaseModel):
    crop: str
    season: str
    n_val: float
    p_val: float
    k_val: float
    ph_val: float
    soil_type: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None

@app.on_event("startup")
async def startup_event():
    load_dataset()
    load_model()

@app.get("/api/crops")
async def get_crops():
    crops = [{"id": c, "name": c.capitalize()} for c in crop_data.keys()]
    crops.sort(key=lambda x: x["name"])
    return crops

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

def calculate_fertilizer(element_name, user_val, avg_val, fertilizer_name, concentration_pct, max_per_app=200):
    if avg_val == 0:
        return f"{element_name} requirement is unknown for this crop.", 0
    
    deficit = avg_val - user_val
    if deficit > 0:
        amount_needed = math.ceil((deficit / concentration_pct) * 100)
        if amount_needed > max_per_app:
            splits = math.ceil(amount_needed / max_per_app)
            directive = f"{element_name} is highly deficient. Instruct the farmer to add a TOTAL of {amount_needed} kg/ha of {fertilizer_name} ({concentration_pct}% concentration), but it MUST be split evenly across {splits} applications (e.g., basal and top dressing) to prevent plant toxicity and stress."
        else:
            directive = f"{element_name} is deficient. Instruct the farmer to add exactly {amount_needed} kg/ha of {fertilizer_name} ({concentration_pct}% concentration) to meet the optimal requirement."
        return directive, amount_needed
    else:
        return f"{element_name} levels are sufficient or high. No {fertilizer_name} addition is needed.", 0

@app.post("/predict")
async def predict(data: SoilData):
    global model, tokenizer
    
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model is currently loading or failed to load.")
        
    crop_stats = crop_data.get(data.crop, {})
    n_avg = crop_stats.get('nitrogen', 0)
    p_avg = crop_stats.get('phosphorus', 0)
    k_avg = crop_stats.get('potassium', 0)
    ph_avg = crop_stats.get('ph', 0)
    t_avg = crop_stats.get('temperature', 0)
    h_avg = crop_stats.get('humidity', 0)
    r_avg = crop_stats.get('rainfall', 0)

    t_val = data.temperature if data.temperature is not None else t_avg
    h_val = data.humidity if data.humidity is not None else h_avg
    r_val = data.rainfall if data.rainfall is not None else r_avg

    np_ratio = round(data.n_val / data.p_val, 2) if data.p_val > 0 else "Undefined (P=0)"
    kp_ratio = round(data.k_val / data.p_val, 2) if data.p_val > 0 else "Undefined (P=0)"
    nk_ratio = round(data.n_val / data.k_val, 2) if data.k_val > 0 else "Undefined (K=0)"

    # Calculate commercial fertilizer amounts
    # N -> Urea (46%)
    # P -> Single Super Phosphate SSP (15.5%)
    # K -> Muriate of Potash MOP (60%)
    n_directive, n_amount = calculate_fertilizer("Nitrogen", data.n_val, n_avg, "Urea", 46.0)
    p_directive, p_amount = calculate_fertilizer("Phosphorus", data.p_val, p_avg, "Single Super Phosphate (SSP)", 15.5)
    k_directive, k_amount = calculate_fertilizer("Potassium", data.k_val, k_avg, "Muriate of Potash (MOP)", 60.0)
    
    ph_diff = data.ph_val - ph_avg
    if ph_diff > 1.0:
        ph_directive = "Soil is too alkaline for this crop. Recommend applying agricultural sulfur or acidifying fertilizers."
    elif ph_diff < -1.0:
        ph_directive = "Soil is too acidic for this crop. Recommend applying agricultural lime."
    else:
        ph_directive = "Soil pH is within an acceptable range."

    season_warning = ""
    season_key = f"season_{data.season.lower()}"
    
    # Check if the requested season is known to be sub-optimal (mean < 0.1) for this crop
    if season_key in crop_stats and crop_stats[season_key] < 0.1:
        season_warning = (
            f"CRITICAL WARNING: The user has selected the {data.season} season for {data.crop}. "
            f"However, this is NOT the optimal season for this crop based on historical data. "
            f"You MUST include a polite but strong warning to the farmer about the high risks (e.g., heat stress or frost) "
            f"of growing this crop in the {data.season} season. Strongly recommend that if they must proceed, "
            f"they should start with indoor seedlings (greenhouse/nursery) and follow the soil directives strictly.\n\n"
        )

    instruction = (
        f"### ROLE\n"
        f"You are an expert Agronomist Data Processor. Your ONLY task is to rephrase the provided raw technical directives "
        f"into a professional, concise, and structured agricultural report.\n\n"
        f"### CONSTRAINTS (STRICT)\n"
        f"- DO NOT recalculate or modify the numbers provided in the directives.\n"
        f"- DO NOT add external advice not found in the provided directives.\n"
        f"- Use an authoritative, scientific tone. NO greetings.\n"
        f"- If the calculated ratio is outside optimal ranges, state it as a fact, not a possibility.\n\n"
        f"### INPUT DATA\n"
        f"Crop: {data.crop}, Soil: {data.soil_type}, pH: {data.ph_val}\n"
        f"Warning: {season_warning}\n\n"
        f"### DIRECTIVES TO REPHRASE\n"
        f"1. {n_directive}\n"
        f"2. {p_directive}\n"
        f"3. {k_directive}\n"
        f"4. {ph_directive}\n\n"
        f"### REQUIRED OUTPUT FORMAT\n"
        f"Present the report in a clear list format starting with 'CULTIVATION DIRECTIVES:' followed by the numbered list. "
        f"Before providing the final report, verify that the numbers in the final text exactly match the numbers in the 'DIRECTIVES TO REPHRASE' section."
    )
                   
    prompt = f"[INST] {instruction} [/INST]"
    
    try:
        inputs = tokenizer(
            prompt, return_tensors='pt',
            truncation=True, max_length=512
        ).to('cuda')
        
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=600,
                temperature=0.1,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
            )
            
        generated_text = tokenizer.decode(
            out[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        ).strip()
        
        # Agro-Logic Sanity Check
        is_valid = True
        if n_amount > 0 and str(n_amount) not in generated_text:
            is_valid = False
        if p_amount > 0 and str(p_amount) not in generated_text:
            is_valid = False
        if k_amount > 0 and str(k_amount) not in generated_text:
            is_valid = False
            
        if not is_valid:
            correction = "\n\n---\n**⚠️ Agro-Logic Sanity Check Alert:**\n"
            correction += "The AI generation lacked precision in listing exact quantities. Please follow these exact calculated requirements:\n"
            if n_amount > 0: correction += f"- **Nitrogen (Urea):** {n_amount} kg/ha\n"
            if p_amount > 0: correction += f"- **Phosphorus (SSP):** {p_amount} kg/ha\n"
            if k_amount > 0: correction += f"- **Potassium (MOP):** {k_amount} kg/ha\n"
            generated_text += correction
            
        return {"recommendation": generated_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
