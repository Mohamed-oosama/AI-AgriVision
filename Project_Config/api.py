import os
# Force offline mode for HuggingFace Transformers
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import sys
import shutil
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Add Models/Analyze a plant to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), "Models", "Analyze a plant"))
from inference import load_model_for_inference, predict
from interpretability import visualize

# Add Models/Yield Prediction to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), "Models", "Yield Prediction"))
from prediction_engine import get_crop_yield_prediction

# Add Models/agrixai_module6 to path
sys.path.append(os.path.join(os.path.dirname(__file__), "Models", "agrixai_module6"))
from module6 import AgriMasterController

# Add Models/EWS to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), "Models", "EWS"))
from ews_inference import get_ews_prediction, PROTECTED_AREAS

# Initialize the AgriMasterController
controller = AgriMasterController()

app = FastAPI()

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create output and upload directories
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount outputs so they can be accessed via URL
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Load model globally to avoid reloading on every request
print("Loading PyTorch model...")
try:
    model_path = os.path.join(os.path.dirname(__file__), "Models", "Analyze a plant", "best_model.pt")
    model, fine_class_names = load_model_for_inference(model_path)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Failed to load model: {e}")
    model, fine_class_names = None, []

# CLASS_MAP removed, using AgriMasterController instead

def format_disease_name(name: str) -> str:
    if not name:
        return name
    name = name.replace("___", " - ")
    name = name.replace("__", " - ")
    name = name.replace("_", " ")
    return name.title()


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    if model is None:
        return {"error": "Model not loaded"}
    
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Run prediction
        result = predict(model, str(file_path), fine_class_names, top_k=5)
        
        # Generate visualisations
        viz_path = visualize(model, str(file_path), fine_class_names, save_dir=OUTPUT_DIR, tag=file.filename.split('.')[0])
        viz_url = f"/outputs/{Path(viz_path).name}"
        
        # Convert result["top_k"] into format expected by AgriMasterController
        # top_k is a list of (raw_name, prob)
        top_k_for_module6 = result.get("top_k", [])
        
        # Execute the Expert System
        diagnosis_res = controller.diagnose(top_k=top_k_for_module6)
        
        # If the expert system fails to produce a result, fallback to top prediction
        if not diagnosis_res or not diagnosis_res.get("json", {}).get("decision"):
            top_pred = top_k_for_module6[0] if top_k_for_module6 else ("Unknown", 0.0)
            formatted_top_pred = format_disease_name(top_pred[0])
            return {
                "disease": formatted_top_pred,
                "diseaseAr": formatted_top_pred,
                "confidence": top_pred[1],
                "severity": "unknown",
                "treatment": "Standard agricultural care recommended.",
                "treatmentAr": "يوصى بالرعاية الزراعية القياسية.",
                "reasoning": [{"step": "Vision Agent", "node": "Detected raw visual features."}],
                "reasoningAr": [{"step": "وكيل الرؤية", "node": "تم الكشف عن سمات بصرية."}],
                "viz_url": viz_url,
                "predictions": [{"disease": format_disease_name(c), "diseaseAr": format_disease_name(c), "confidence": p} for c, p in top_k_for_module6],
                "report_en": "No detailed report available.",
                "report_ar": "لا يوجد تقرير مفصل."
            }

        decision = diagnosis_res["json"]["decision"]
        severity_info = diagnosis_res["json"].get("severity", {})
        
        disease_en = format_disease_name(decision.get("label_en", decision.get("class")))
        disease_ar = decision.get("label_ar", disease_en)
        severity = severity_info.get("level", "medium")
        
        # Extract treatment and controls from KG
        kg_info = diagnosis_res["json"].get("kg", {})
        controls = kg_info.get("controls", {})
        chemical_controls = controls.get("chemical", [])
        cultural_controls = controls.get("cultural", [])
        biological_controls = controls.get("biological", [])
        
        treatment_en_list = chemical_controls + cultural_controls + biological_controls
        treatment_en = " ".join(treatment_en_list) if treatment_en_list else "Standard agricultural care recommended."
        # For now, we reuse English for treatment_ar if we don't have translated treatments
        treatment_ar = treatment_en

        category = decision.get("category", "disease")
        category_map_ar = {
            "disease": "مرض",
            "pest": "آفة",
            "deficiency": "نقص عناصر"
        }
        category_ar = category_map_ar.get(category, "حالة زراعية")
        
        confidence_pct = f"{decision.get('confidence', 0.0) * 100:.1f}%"
        
        reasoning = [
            {"step": "Vision Agent", "node": f"Detected visual patterns matching {disease_en}."},
            {"step": "Graph-RAG Agent", "node": f"Traversed knowledge graph for {category} context."},
            {"step": "Expert System", "node": f"Reason: {decision.get('reason', 'N/A')}"},
            {"step": "Decision Agent", "node": f"Finalized diagnosis: {disease_en} (Confidence: {confidence_pct})."}
        ]
        
        reasoning_ar = [
            {"step": "وكيل الرؤية", "node": f"تم الكشف عن الأنماط البصرية المطابقة لـ {disease_ar}."},
            {"step": "وكيل Graph-RAG", "node": f"تم الانتقال في الرسم المعرفي لفئة {category_ar}."},
            {"step": "النظام الخبير", "node": f"السبب: {decision.get('reason', 'غير متاح')}"},
            {"step": "وكيل القرار", "node": f"التشخيص النهائي: {disease_ar} (درجة الثقة: {confidence_pct})."}
        ]
        
        top_predictions = []
        for raw_name, prob in top_k_for_module6:
            formatted_name = format_disease_name(raw_name)
            top_predictions.append({
                "disease": formatted_name,
                "diseaseAr": formatted_name, # Fallback
                "confidence": prob
            })

        return {
            "disease": disease_en,
            "diseaseAr": disease_ar,
            "confidence": decision.get("confidence", result["diagnosis_conf"]),
            "severity": severity,
            "treatment": treatment_en,
            "treatmentAr": treatment_ar,
            "reasoning": reasoning,
            "reasoningAr": reasoning_ar,
            "viz_url": viz_url,
            "predictions": top_predictions,
            "report_en": diagnosis_res["report"].get("text_en", ""),
            "report_ar": diagnosis_res["report"].get("text_ar", ""),
            "report_html": diagnosis_res["report"].get("html", "")
        }
    except Exception as e:
        return {"error": str(e)}

import requests

@app.post("/api/chat")
async def chat_proxy(request: Request):
    try:
        body = await request.json()
        message = body.get("message", "")
        query = body.get("query", message)
        session_id = body.get("session_id", "default")
        
        payload = {
            "query": query,
            "session_id": session_id
        }
        
        resp = requests.post("http://127.0.0.1:5000/query", json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "reply": data.get("answer", ""),
                "answer": data.get("answer", ""),
                "confidence": data.get("confidence", 0.0),
                "explanation": data.get("explanation", ""),
                "agent_path": data.get("agent_path", []),
                "latency_ms": data.get("latency_ms", 0.0)
            }
        else:
            return {"error": f"Chatbot server returned error status: {resp.status_code}", "detail": resp.text}
    except Exception as e:
        return {"error": f"Failed to connect to Chatbot server: {str(e)}"}

@app.post("/api/yield/predict")
async def yield_predict(request: Request):
    try:
        body = await request.json()
        crop = body.get("crop", "Wheat")
        year = body.get("year", 2026)
        custom_inputs = body.get("inputs", None)
        
        result = get_crop_yield_prediction(crop, year, custom_inputs)
        return result
    except Exception as e:
        return {"error": f"Failed to run yield prediction: {str(e)}"}

# Add Models/Soil Analysis to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), "Models", "Soil Analysis"))
from soil_inference import get_soil_recommendation

@app.get("/api/soil/crops")
async def get_soil_crops():
    try:
        import json
        stats_path = os.path.join(os.path.dirname(__file__), "Models", "Soil Analysis", "webapp", "crop_stats.json")
        if os.path.exists(stats_path):
            with open(stats_path, "r", encoding="utf-8") as f:
                all_stats = json.load(f)
            # Capitalize each crop key for clean frontend options
            crops = [c.capitalize() for c in all_stats.keys()]
            crops.sort()
            return crops
        else:
            return ["Tomato", "Wheat", "Corn", "Cotton", "Potato", "Rice", "Banana"]
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/soil/predict")
async def soil_predict(request: Request):
    try:
        body = await request.json()
        result = get_soil_recommendation(body)
        return result
    except Exception as e:
        return {"error": f"Failed to run soil analysis: {str(e)}"}

@app.get("/api/ews/areas")
async def get_ews_areas():
    try:
        areas = [{"id": k, "name": v} for k, v in PROTECTED_AREAS.items()]
        areas.sort(key=lambda x: x["id"])
        return areas
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/ews/predict")
async def ews_predict(request: Request):
    try:
        body = await request.json()
        result = get_ews_prediction(body)
        return result
    except Exception as e:
        return {"error": f"Failed to run EWS prediction: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
