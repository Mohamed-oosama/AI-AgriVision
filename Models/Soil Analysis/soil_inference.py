import math
import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADAPTER_PATH = os.path.join(BASE_DIR, "TRAINNIG", "final")
STATS_PATH = os.path.join(BASE_DIR, "webapp", "crop_stats.json")

CROP_ARABIC = {
    "Tomato": "الطماطم",
    "Wheat": "القمح",
    "Corn": "الذرة",
    "Cotton": "القطن",
    "Potato": "البطاطس",
    "Rice": "الأرز",
    "Banana": "الموز"
}

SOIL_ARABIC = {
    "Loamy": "اللومية (الطفيلية)",
    "Clay": "الطينية",
    "Sandy": "الرملية",
    "Silty": "الغرينية",
    "Peaty": "الخثية"
}

SEASON_ARABIC = {
    "Summer": "الصيف",
    "Spring": "الربيع",
    "Autumn": "الخريف",
    "Winter": "الشتاء"
}

# Global variables for model
model = None
tokenizer = None
crop_data = {}

def load_soil_model_and_stats():
    global model, tokenizer, crop_data
    
    # 1. Load Stats
    try:
        if os.path.exists(STATS_PATH):
            with open(STATS_PATH, "r", encoding="utf-8") as f:
                crop_data = json.load(f)
            print(f"Loaded Soil statistics for {len(crop_data)} crops.")
    except Exception as e:
        print(f"Error loading crop_stats.json: {e}")
        
    # 2. Load Model
    print("Loading Soil QLoRA model tokenizer...")
    try:
        user_home = os.path.expanduser("~")
        cache_dir = os.path.join(user_home, ".cache", "huggingface", "hub")
        
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            cache_dir=cache_dir,
            trust_remote_code=True,
            use_fast=False
        )
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = 'right'
        
        print("Loading Soil base model in 4-bit...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type='nf4',
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        
        base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            cache_dir=cache_dir,
            quantization_config=bnb_config,
            device_map='auto',
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
        )
        
        print(f"Loading Soil LoRA weights from {ADAPTER_PATH}...")
        model = PeftModel.from_pretrained(
            base_model,
            ADAPTER_PATH,
        )
        model.eval()
        print("Soil QLoRA Model loaded successfully and ready!")
    except Exception as e:
        print(f"Failed to load Soil QLoRA model: {e}. Running in rule-based fallback mode.")

# Load stats and model at module import time
load_soil_model_and_stats()


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


def get_soil_recommendation(data: dict) -> dict:
    global model, tokenizer, crop_data
    
    crop = data.get("crop", "Tomato")
    season = data.get("season", "Summer")
    n_val = float(data.get("n_val", 0))
    p_val = float(data.get("p_val", 0))
    k_val = float(data.get("k_val", 0))
    ph_val = float(data.get("ph_val", 7.0))
    soil_type = data.get("soil_type", "Loamy")

    # Map crop name to lowercase key in JSON
    crop_key = crop.lower()
    if crop_key == "corn":
        crop_key = "maize"
        
    crop_stats = crop_data.get(crop_key, {})
    n_avg = crop_stats.get('nitrogen', 100.0)
    p_avg = crop_stats.get('phosphorus', 50.0)
    k_avg = crop_stats.get('potassium', 80.0)
    ph_avg = crop_stats.get('ph', 6.5)

    # If LLM model is not loaded, fall back to rule-based template
    if model is None or tokenizer is None:
        print("Using rule-based fallback mode for soil recommendations.")
        return get_soil_recommendation_fallback(data, crop_stats)

    try:
        # Run QLoRA inference
        n_directive, n_amount = calculate_fertilizer("Nitrogen", n_val, n_avg, "Urea", 46.0)
        p_directive, p_amount = calculate_fertilizer("Phosphorus", p_val, p_avg, "Single Super Phosphate (SSP)", 15.5)
        k_directive, k_amount = calculate_fertilizer("Potassium", k_val, k_avg, "Muriate of Potash (MOP)", 60.0)
        
        ph_diff = ph_val - ph_avg
        if ph_diff > 1.0:
            ph_directive = "Soil is too alkaline for this crop. Recommend applying agricultural sulfur or acidifying fertilizers."
        elif ph_diff < -1.0:
            ph_directive = "Soil is too acidic for this crop. Recommend applying agricultural lime."
        else:
            ph_directive = "Soil pH is within an acceptable range."

        season_warning = ""
        season_key = f"season_{season.lower()}"
        
        # Check if the requested season is known to be sub-optimal (mean < 0.1) for this crop
        if season_key in crop_stats and crop_stats[season_key] < 0.1:
            season_warning = (
                f"CRITICAL WARNING: The user has selected the {season} season for {crop}. "
                f"However, this is NOT the optimal season for this crop based on historical data. "
                f"You MUST include a polite but strong warning to the farmer about the high risks (e.g., heat stress or frost) "
                f"of growing this crop in the {season} season. Strongly recommend that if they must proceed, "
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
            f"Crop: {crop}, Soil: {soil_type}, pH: {ph_val}\n"
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
        inputs = tokenizer(prompt, return_tensors='pt', truncation=True, max_length=512).to('cuda')
        
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=400,
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
            
        # Get Arabic report from fallback to provide a bilingual interface
        fallback_res = get_soil_recommendation_fallback(data, crop_stats)
        arabic_part = fallback_res["recommendation"].split("=======================")[0].strip()
        
        combined_report = f"{arabic_part}\n\n=======================\n\n{generated_text}"
        
        return {
            "recommendation": combined_report,
            "n_target": n_avg,
            "p_target": p_avg,
            "k_target": k_avg,
            "ph_target": ph_avg
        }
    except Exception as e:
        print(f"Error during QLoRA inference: {e}. Falling back to rule-based.")
        return get_soil_recommendation_fallback(data, crop_stats)


def get_soil_recommendation_fallback(data: dict, stats: dict) -> dict:
    crop = data.get("crop", "Tomato")
    season = data.get("season", "Summer")
    n_val = float(data.get("n_val", 0))
    p_val = float(data.get("p_val", 0))
    k_val = float(data.get("k_val", 0))
    ph_val = float(data.get("ph_val", 7.0))
    soil_type = data.get("soil_type", "Loamy")

    n_avg = stats.get("nitrogen", 100.0)
    p_avg = stats.get("phosphorus", 50.0)
    k_avg = stats.get("potassium", 80.0)
    ph_avg = stats.get("ph", 6.5)

    # Arabic translated names
    crop_ar = CROP_ARABIC.get(crop, crop)
    soil_ar = SOIL_ARABIC.get(soil_type, soil_type)
    season_ar = SEASON_ARABIC.get(season, season)

    # Plural English name for warnings
    plural_crop = crop.lower() + "s"
    if crop.lower() == "tomato":
        plural_crop = "tomatoes"
    elif crop.lower() == "potato":
        plural_crop = "potatoes"

    # --- 1. Nitrogen (Urea 46%) ---
    n_deficit = n_avg - n_val
    if n_deficit > 0:
        n_amount = math.ceil((n_deficit / 46.0) * 100)
        if n_amount > 200:
            part = round(n_amount / 3, 1)
            n_en = (
                f"1. {crop} crop requires nitrogen supplementation. Apply a TOTAL of {n_amount} kg/ha of Urea (46.0% concentration) in three equal parts:\n"
                f"   - Application 1: Basal application at planting ({part} kg/ha)\n"
                f"   - Application 2: Side-dressing approximately 4-6 weeks after transplanting ({part} kg/ha)\n"
                f"   - Application 3: Split application before flowering ({part} kg/ha)\n"
                f"   This approach ensures optimal nutrient uptake while minimizing potential plant toxicity and stress."
            )
            n_ar = (
                f"1. يتطلب محصول {crop_ar} تزويداً بالنيتروجين. أضف إجمالي {n_amount} كجم/هكتار من اليوريا (تركيز 46.0%) مقسمة على ثلاث دفعات متساوية:\n"
                f"   - الدفعة الأولى: إضافة أساسية أثناء الزراعة ({part} كجم/هكتار)\n"
                f"   - الدفعة الثانية: تسميد جانبي بعد حوالي 4-6 أسابيع من نقل الشتلات ({part} كجم/هكتار)\n"
                f"   - الدفعة الثالثة: إضافة مجزأة قبل التزهير ({part} كجم/هكتار)\n"
                f"   يضمن هذا الأسلوب امتصاصاً مثالياً للعناصر الغذائية مع تقليل السمية والإجهاد المحتمل للنبات."
            )
        else:
            n_en = f"1. {crop} crop requires nitrogen supplementation. Apply exactly {n_amount} kg/ha of Urea (46.0% concentration) to meet the optimal requirement."
            n_ar = f"1. يتطلب محصول {crop_ar} تزويداً بالنيتروجين. أضف بالضبط {n_amount} كجم/هكتار من اليوريا (تركيز 46.0%) لتلبية المتطلبات المثالية."
    else:
        n_en = f"1. Nitrogen levels in the {soil_type.lower()} soil are sufficient or high. No Urea addition is required."
        n_ar = f"1. مستويات النيتروجين في التربة {soil_ar} كافية أو مرتفعة. لا يلزم إضافة اليوريا."

    # --- 2. Phosphorus (SSP 15.5%) ---
    p_deficit = p_avg - p_val
    if p_deficit > 0:
        p_amount = math.ceil((p_deficit / 15.5) * 100)
        p_en = f"2. Phosphorus deficiency detected. Add {p_amount} kg/ha of Single Super Phosphate (SSP) (15.5% concentration)."
        p_ar = f"2. تم الكشف عن نقص في الفسفور. أضف {p_amount} كجم/هكتار من السوبر فوسفات الأحادي (SSP) (تركيز 15.5%)."
    else:
        p_en = f"2. Phosphorus levels in the {soil_type.lower()} soil are sufficient or high. No Single Super Phosphate (SSP) addition is required."
        p_ar = f"2. مستويات الفسفور في التربة {soil_ar} كافية أو مرتفعة. لا يلزم إضافة السوبر فوسفات الأحادي (SSP)."

    # --- 3. Potassium (MOP 60%) ---
    k_deficit = k_avg - k_val
    if k_deficit > 0:
        k_amount = math.ceil((k_deficit / 60.0) * 100)
        k_en = f"3. Potassium deficiency identified. Supplement with {k_amount} kg/ha of Muriate of Potash (MOP) (60.0% concentration)."
        k_ar = f"3. تم تحديد نقص في البوتاسيوم. أضف {k_amount} كجم/هكتار من سلفات البوتاسيوم (MOP) (تركيز 60.0%)."
    else:
        k_en = f"3. Potassium levels in the {soil_type.lower()} soil are sufficient or high. No Muriate of Potash (MOP) addition is necessary."
        k_ar = f"3. مستويات البوتاسيوم في التربة {soil_ar} كافية أو مرتفعة. لا يلزم إضافة سلفات البوتاسيوم (MOP)."

    # --- 4. pH ---
    ph_diff = ph_val - ph_avg
    if ph_diff > 1.0:
        ph_en = f"4. Soil is too alkaline for this crop (pH: {ph_val:.1f}). Recommend applying agricultural sulfur or acidifying fertilizers."
        ph_ar = f"4. التربة قلوية جداً لهذا المحصول (pH: {ph_val:.1f}). يوصى بإضافة الكبريت الزراعي أو الأسمدة الحمضية."
    elif ph_diff < -1.0:
        ph_en = f"4. Soil is too acidic for this crop (pH: {ph_val:.1f}). Recommend applying agricultural lime."
        ph_ar = f"4. التربة حمضية جداً لهذا المحصول (pH: {ph_val:.1f}). يوصى بإضافة الجير الزراعي (كربونات الكالسيوم)."
    else:
        ph_en = f"4. Soil pH for {crop.lower()} cultivation in a {soil_type.lower()} texture is within the acceptable range of {ph_avg:.1f} (Current pH: {ph_val:.1f})."
        ph_ar = f"4. درجة حموضة التربة لزراعة {crop_ar} في التربة {soil_ar} تقع في النطاق المقبول وهو {ph_avg:.1f} (درجة الحموضة الحالية: {ph_val:.1f})."

    # --- Season Warning ---
    season_warning_en = ""
    season_warning_ar = ""
    season_key = f"season_{season.lower()}"
    if season_key in stats and stats[season_key] < 0.1:
        season_warning_en = (
            f"Important Note: Growing {plural_crop} during the {season.lower()} season in this region carries significant risks due to potential heat stress or frost damage. "
            f"It is strongly recommended that farmers consider starting their crops as indoor seedlings (greenhouse/nursery) to mitigate these risks."
        )
        season_warning_ar = (
            f"ملاحظة هامة: زراعة {crop_ar} خلال موسم {season_ar} في هذه المنطقة تنطوي على مخاطر كبيرة بسبب الإجهاد الحراري أو الصقيع المحتمل. "
            f"يوصى بشدة أن يبدأ المزارعون زراعة محاصيلهم كشتلات داخلية (الصوب/المشاتل) للتخفيف من هذه المخاطر."
        )

    # Build report text
    report_lines_en = [
        "CULTIVATION DIRECTIVES:\n",
        n_en,
        p_en,
        k_en,
        ph_en,
    ]
    if season_warning_en:
        report_lines_en.append(f"\n{season_warning_en}")
    report_en = "\n".join(report_lines_en)

    report_lines_ar = [
        "توجيهات الزراعة وتجهيز التربة:\n",
        n_ar,
        p_ar,
        k_ar,
        ph_ar,
    ]
    if season_warning_ar:
        report_lines_ar.append(f"\n{season_warning_ar}")
    report_ar = "\n".join(report_lines_ar)

    full_report = f"{report_ar}\n\n=======================\n\n{report_en}"
    return {
        "recommendation": full_report,
        "n_target": n_avg,
        "p_target": p_avg,
        "k_target": k_avg,
        "ph_target": ph_avg
    }
