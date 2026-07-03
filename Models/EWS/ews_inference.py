import os
import json
import logging
import datetime as dt
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np
import joblib
import shap

from ews_report import EwsReportPayload, render_full_report

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EWSInference")

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
BASELINES_PATH = os.path.join(BASE_DIR, "baselines.json")
LOG_FILE = os.path.join(os.path.dirname(BASE_DIR), "..", "outputs", "ews_predictions.jsonl")

# Protected Areas mapping
PROTECTED_AREAS = {
    0 : 'محمية أشتوم الجميل',
    1 : 'محمية البرلس',
    2 : 'محمية الجزر الشمالية للبحر الأحمر',
    3 : 'محمية الجلف الكبير',
    4 : 'محمية الدبابية',
    5 : 'محمية الزرانيق',
    6 : 'محمية الصحراء البيضاء',
    7 : 'محمية العميد',
    8 : 'محمية الغابة المتحجرة',
    9 : 'محمية الواحات البحرية – الجزء الشرقي',
    10: 'محمية الواحات البحرية – الجزء الغربي',
    11: 'محمية الواحات البحرية – الجزء الوسطي',
    12: 'محمية رأس محمد',
    13: 'محمية سالوجا وغزال',
    14: 'محمية سانت كاثرين',
    15: 'محمية سيوة – القطاع الأوسط الجنوبي',
    16: 'محمية سيوة – القطاع الغربي',
    17: 'محمية سيوة – القطاع الشرقي',
    18: 'محمية طابا',
    19: 'محمية علبة',
    20: 'محمية قارون',
    21: 'محمية قبة الحسنة',
    22: 'محمية كهف سنور',
    23: 'محمية نبق',
    24: 'محمية نيزك جبل كامل',
    25: 'محمية وادي الأسيوطي',
    26: 'محمية وادي الجمال',
    27: 'محمية وادي الريان',
    28: 'محمية وادي العلاقي',
    29: 'محمية وادي دجلة',
    30: 'محمية أبو جالوم',
}
AREA_IDX = {v: k for k, v in PROTECTED_AREAS.items()}

# Global variables loaded at startup
ENSEMBLE = {}
DECISION_THRESHOLD = 0.69138677431065  # fallback
SAFETY_THRESHOLD = 0.021793145663303454  # fallback
FEATURE_NAMES = []
SHAP_EXPLAINER = None

# Baseline Dictionaries
AREA_PRECIP_BASELINES = {}
AREA_PRECIP_STDS = {}
AREA_SOILMOIST_P20 = {}

# Climate thresholds
VEG_STRESS = dict(
    temp_opt_low    = 15.0,    # °C
    temp_opt_high   = 35.0,    # °C
    temp_critical   = 42.0,    # °C
    soil_moist_low  = 0.05,    # m³/m³
    precip_dry      = 1.0,     # mm/day
    radiation_high  = 25.0,    # MJ/m²
    evap_stress     = 5.0,     # mm/day
    ndvi_healthy    = 0.3,
    ndvi_stressed   = 0.15,
)

NDVI_STRESS = dict(
    rolling_window   = 30,
    stress_threshold = 1.5,
    min_ndvi_valid   = -0.1,
    max_ndvi_valid   =  0.9,
    noise_rate       = 0.03,
)

# Rule-based (v1) risk settings
RISK_LEVELS = ['Low', 'Moderate', 'High', 'Critical']
ACTIONS = {
    'Low'     : 'Routine monitoring. Vegetation appears healthy.',
    'Moderate': 'Increase monitoring frequency. Investigate potential stressors.',
    'High'    : 'Alert protected area management. Initiate field inspection immediately.',
    'Critical': 'Emergency response required. Notify EEAA (Egyptian Environmental Affairs Agency).'
}
ACTIONS_AR = {
    'Low'     : 'مراقبة روتينية. يبدو الغطاء النباتي صحياً.',
    'Moderate': 'زيادة وتيرة المراقبة. التحقيق في المسببات المحتملة للإجهاد.',
    'High'    : 'تنبيه إدارة المحمية الطبيعية. البدء في الفحص الميداني فوراً.',
    'Critical': 'الاستجابة لحالات الطوارئ مطلوبة. إخطار جهاز شؤون البيئة المصري (EEAA).'
}

V1_WEIGHTS = dict(
    ndvi_stressed   = 20,
    ndvi_subhealthy = 8,
    ndvi_anomaly    = 25,
    water_stress    = 10,
    drought         = 8,
    heat_stress     = 12,
    evap_stress     = 7,
    composite_bonus = 10,
)

V1_THRESHOLDS = dict(
    critical = 80,
    high     = 52,
    moderate = 26,
)

# Fusion logic parameters
THRESH_HIGH_CONF  = 0.55
THRESH_LOW_CONF   = 0.10
ENSEMBLE_DISAGREE = 0.10

ENSEMBLE_WEIGHTS = {
    'xgb': 0.5,
    'rf' : 0.3,
    'lr' : 0.2,
}

REQUIRED_COLUMNS = [
    'ndvi_mean', 'savi', 'evi', 'vegetation_percent',
    'temperature_2m', 'total_precipitation_sum',
    'volumetric_soil_water_layer_1', 'volumetric_soil_water_layer_2',
    'volumetric_soil_water_layer_3', 'volumetric_soil_water_layer_4',
    'surface_solar_radiation_downwards_sum',
    'u_component_of_wind_10m', 'v_component_of_wind_10m',
]

@dataclass
class ProtectedAreaQuery:
    query_id : str
    area_id  : int
    data_row : pd.Series

def load_ews_resources():
    global ENSEMBLE, DECISION_THRESHOLD, SAFETY_THRESHOLD, FEATURE_NAMES, SHAP_EXPLAINER
    global AREA_PRECIP_BASELINES, AREA_PRECIP_STDS, AREA_SOILMOIST_P20

    # 1. Load config.json
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            DECISION_THRESHOLD = cfg.get("decision_threshold", DECISION_THRESHOLD)
            SAFETY_THRESHOLD = cfg.get("safety_threshold", SAFETY_THRESHOLD)
            FEATURE_NAMES = cfg.get("feature_names", [])
            logger.info(f"Loaded config from {CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")

    # 2. Load baselines.json
    try:
        if os.path.exists(BASELINES_PATH):
            with open(BASELINES_PATH, "r", encoding="utf-8") as f:
                baselines = json.load(f)
            # Keys in JSON are strings, convert back to integer for lookups
            AREA_PRECIP_BASELINES = {int(k): v for k, v in baselines.get("precip_baselines", {}).items()}
            AREA_PRECIP_STDS = {int(k): v for k, v in baselines.get("precip_stds", {}).items()}
            AREA_SOILMOIST_P20 = {int(k): v for k, v in baselines.get("soilmoist_p20", {}).items()}
            logger.info(f"Loaded climate baselines for {len(AREA_PRECIP_BASELINES)} areas.")
    except Exception as e:
        logger.error(f"Failed to load baselines: {e}")

    # 3. Load Models
    for name in ['xgb', 'rf', 'lr']:
        mp = os.path.join(BASE_DIR, f"{name}_model.joblib")
        cp = os.path.join(BASE_DIR, f"{name}_cols.json")
        if os.path.exists(mp):
            try:
                with open(cp, "r") as fh:
                    cols = json.load(fh)
                ENSEMBLE[name] = {'model': joblib.load(mp), 'cols': cols}
                logger.info(f"Loaded EWS {name} model.")
            except Exception as e:
                logger.error(f"Failed to load {name} model: {e}")

    # 4. Init SHAP
    if 'xgb' in ENSEMBLE:
        try:
            xgb_cal = ENSEMBLE['xgb']['model']
            if hasattr(xgb_cal, "calibrated_classifiers_") and len(xgb_cal.calibrated_classifiers_) > 0:
                _xgb_base = xgb_cal.calibrated_classifiers_[0].estimator
                SHAP_EXPLAINER = shap.TreeExplainer(_xgb_base)
                logger.info("SHAP TreeExplainer initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to initialize SHAP TreeExplainer: {e}")

# Load resources when module is imported
load_ews_resources()

def engineer_features_protected(row: pd.Series) -> Dict[str, float]:
    f: Dict[str, float] = {}

    # ── NDVI features
    f['ndvi_mean']         = float(row.get('ndvi_mean', 0.0) or 0.0)
    f['savi']              = float(row.get('savi', 0.0) or 0.0)
    f['evi']               = float(row.get('evi', 0.0) or 0.0)
    f['vegetation']        = float(row.get('vegetation_percent', 0.0) or 0.0)
    f['ndvi_rolling_mean'] = float(row.get('ndvi_rolling_mean', f['ndvi_mean']) or f['ndvi_mean'])
    f['ndvi_rolling_std']  = float(row.get('ndvi_rolling_std', 0.05) or 0.05)
    f['ndvi_anomaly']      = float(row.get('ndvi_anomaly', 0.0) or 0.0)
    f['ndvi_anomaly_z']    = float(row.get('ndvi_anomaly_z', 0.0) or 0.0)

    f['ndvi_below_healthy'] = max(0.0, VEG_STRESS['ndvi_healthy'] - f['ndvi_mean'])
    f['ndvi_stressed_flag'] = float(f['ndvi_mean'] < VEG_STRESS['ndvi_stressed'])
    f['ndvi_savi_diff']     = f['ndvi_mean'] - f['savi']
    f['ndvi_evi_ratio']     = f['ndvi_mean'] / (f['evi'] + 1e-6)
    f['ndvi_cv']            = f['ndvi_rolling_std'] / (f['ndvi_rolling_mean'] + 1e-6)

    # ── Temperature features — Convert Kelvin to Celsius
    temp_k   = float(row.get('temperature_2m',          298.0) or 298.0)
    skin_k   = float(row.get('skin_temperature',        temp_k) or temp_k)
    dew_k    = float(row.get('dewpoint_temperature_2m', temp_k - 10) or temp_k - 10)
    st1_k    = float(row.get('soil_temperature_level_1', temp_k) or temp_k)
    st4_k    = float(row.get('soil_temperature_level_4', temp_k) or temp_k)

    temp   = temp_k  - 273.15
    skin_t = skin_k  - 273.15
    dew_t  = dew_k   - 273.15
    st1    = st1_k   - 273.15
    st4    = st4_k   - 273.15

    f['temperature_2m']      = temp
    f['skin_temperature']    = skin_t
    f['dewpoint_temp']       = dew_t
    f['temp_dew_spread']     = temp - dew_t
    f['temp_skin_diff']      = skin_t - temp
    f['temp_above_critical'] = max(0.0, temp - VEG_STRESS['temp_critical'])
    f['temp_in_opt']         = float(VEG_STRESS['temp_opt_low'] <= temp <= VEG_STRESS['temp_opt_high'])
    f['soil_temp_l1']        = st1
    f['soil_temp_gradient']  = st1 - st4

    # ── Precipitation & Hydrology
    precip = float(row.get('total_precipitation_sum', 0.0) or 0.0)
    runoff = float(row.get('runoff_sum', 0.0) or 0.0)
    surf_r = float(row.get('surface_runoff_sum', 0.0) or 0.0)
    sub_r  = float(row.get('sub_surface_runoff_sum', 0.0) or 0.0)
    evap   = float(row.get('total_evaporation_sum', 0.0) or 0.0)

    f['precip']            = precip
    f['precip_log']        = float(np.log1p(precip))
    f['runoff']            = runoff
    f['surface_runoff']    = surf_r
    f['subsurface_runoff'] = sub_r
    f['evaporation']       = evap
    f['precip_minus_evap'] = precip - abs(evap)
    f['evap_stress_flag']  = float(abs(evap) > VEG_STRESS['evap_stress'])

    # Anomaly-based drought flag
    area_id = int(row.get('area_id', -1))
    _precip_median  = AREA_PRECIP_BASELINES.get(area_id, VEG_STRESS['precip_dry'])
    _precip_std     = AREA_PRECIP_STDS.get(area_id, 1e-4)
    _precip_z       = (precip - _precip_median) / (_precip_std + 1e-9)
    f['precip_zscore']  = float(_precip_z)
    f['drought_flag']   = float(_precip_z < -1.5)

    # ── Soil moisture (4 layers)
    sm1 = float(row.get('volumetric_soil_water_layer_1', 0.1) or 0.1)
    sm2 = float(row.get('volumetric_soil_water_layer_2', 0.1) or 0.1)
    sm3 = float(row.get('volumetric_soil_water_layer_3', 0.1) or 0.1)
    sm4 = float(row.get('volumetric_soil_water_layer_4', 0.1) or 0.1)

    f['soil_moisture_l1']      = sm1
    f['soil_moisture_l2']      = sm2
    f['soil_moisture_l3']      = sm3
    f['soil_moisture_l4']      = sm4
    f['soil_moisture_mean']    = float(np.mean([sm1, sm2, sm3, sm4]))
    f['soil_moisture_profile'] = sm1 - sm4

    # Percentile-based soil moisture thresholds
    _sm_p20 = AREA_SOILMOIST_P20.get(area_id, VEG_STRESS['soil_moist_low'])
    f['soil_moisture_p20_thresh'] = float(_sm_p20)
    f['water_stress_flag'] = float(sm1 < _sm_p20)
    f['area_sm_p20'] = float(_sm_p20)

    # ── Radiation
    rad = float(row.get('surface_solar_radiation_downwards_sum', 15.0) or 15.0)
    f['solar_radiation']       = rad
    f['radiation_stress_flag'] = float(rad > VEG_STRESS['radiation_high'])
    f['rad_x_temp']            = rad * temp / 100.0

    # ── Wind
    u_wind = float(row.get('u_component_of_wind_10m', 0.0) or 0.0)
    v_wind = float(row.get('v_component_of_wind_10m', 0.0) or 0.0)
    f['wind_speed'] = float(np.sqrt(u_wind**2 + v_wind**2))
    f['wind_u']     = u_wind
    f['wind_v']     = v_wind

    # ── Pressure (Convert Pa to kPa)
    f['surface_pressure'] = float(row.get('surface_pressure', 101325.0) or 101325.0) / 1000.0

    # ── Interaction features
    f['temp_x_soil_moisture'] = temp * f['soil_moisture_mean']
    f['ndvi_x_soil_moisture'] = f['ndvi_mean'] * f['soil_moisture_mean']
    f['radiation_x_moisture'] = rad * f['soil_moisture_mean']
    f['stress_composite']     = (
        f['water_stress_flag'] + f['drought_flag'] +
        f['radiation_stress_flag'] + f['ndvi_stressed_flag'] +
        f['evap_stress_flag']
    ) / 5.0

    # ── Temporal / Seasonality
    day = float(row.get('day_count', 0.0) or 0.0)
    f['day_count']  = day
    day_of_year     = day % 365
    f['season_sin'] = float(np.sin(2.0 * np.pi * day_of_year / 365.0))
    f['season_cos'] = float(np.cos(2.0 * np.pi * day_of_year / 365.0))

    # ── Area encoding
    f['area_idx'] = float(area_id)

    return f

def _compute_v1_risk_score_protected(features: Dict[str, float]) -> Tuple[float, List[str], List[str]]:
    score   = 0.0
    reasons = []
    reasons_ar = []

    ndvi = features.get('ndvi_mean', 0.3)
    if ndvi < VEG_STRESS['ndvi_stressed']:
        score += V1_WEIGHTS['ndvi_stressed']
        reasons.append(f'NDVI {ndvi:.3f} below stress threshold ({VEG_STRESS["ndvi_stressed"]}) [+{V1_WEIGHTS["ndvi_stressed"]}]')
        reasons_ar.append(f'مؤشر NDVI ({ndvi:.3f}) أقل من حد الإجهاد ({VEG_STRESS["ndvi_stressed"]}) [+{V1_WEIGHTS["ndvi_stressed"]}]')
    elif ndvi < VEG_STRESS['ndvi_healthy']:
        score += V1_WEIGHTS['ndvi_subhealthy']
        reasons.append(f'NDVI {ndvi:.3f} below healthy threshold ({VEG_STRESS["ndvi_healthy"]}) [+{V1_WEIGHTS["ndvi_subhealthy"]}]')
        reasons_ar.append(f'مؤشر NDVI ({ndvi:.3f}) أقل من الحد الصحي ({VEG_STRESS["ndvi_healthy"]}) [+{V1_WEIGHTS["ndvi_subhealthy"]}]')

    anomaly_z = features.get('ndvi_anomaly_z', 0)
    if anomaly_z < -NDVI_STRESS['stress_threshold']:
        score += V1_WEIGHTS['ndvi_anomaly']
        reasons.append(f'NDVI anomaly z={anomaly_z:.2f} (below baseline by {abs(anomaly_z):.1f} σ) [+{V1_WEIGHTS["ndvi_anomaly"]}]')
        reasons_ar.append(f'شذوذ مؤشر NDVI المعياري z={anomaly_z:.2f} (أقل من الخط المرجعي بمقدار {abs(anomaly_z):.1f} انحراف) [+{V1_WEIGHTS["ndvi_anomaly"]}]')

    if features.get('water_stress_flag', 0):
        score += V1_WEIGHTS['water_stress']
        area_sm_p20 = features.get('area_sm_p20', VEG_STRESS['soil_moist_low'])
        reasons.append(f'Soil moisture {features["soil_moisture_l1"]:.3f} m³/m³ below area baseline (P20={area_sm_p20:.3f}) [+{V1_WEIGHTS["water_stress"]}]')
        reasons_ar.append(f'رطوبة التربة ({features["soil_moisture_l1"]:.3f} م³/م³) أقل من المعدل المرجعي للمحمية (P20={area_sm_p20:.3f}) [+{V1_WEIGHTS["water_stress"]}]')

    if features.get('drought_flag', 0):
        score += V1_WEIGHTS['drought']
        reasons.append(f'Precipitation {features["precip"]:.4f} mm below dry threshold [+{V1_WEIGHTS["drought"]}]')
        reasons_ar.append(f'معدل هطول الأمطار ({features["precip"]:.4f} مم) أقل من حد الجفاف [+{V1_WEIGHTS["drought"]}]')

    temp_c = features.get('temperature_2m', 25.0)
    if features.get('temp_above_critical', 0) > 0:
        score += V1_WEIGHTS['heat_stress']
        reasons.append(f'Temperature {temp_c:.1f}°C exceeds critical threshold ({VEG_STRESS["temp_critical"]}°C) [+{V1_WEIGHTS["heat_stress"]}]')
        reasons_ar.append(f'درجة الحرارة ({temp_c:.1f}°C) تتجاوز الحد الحرج للنباتات الصحراوية ({VEG_STRESS["temp_critical"]}°C) [+{V1_WEIGHTS["heat_stress"]}]')

    if features.get('evap_stress_flag', 0):
        score += V1_WEIGHTS['evap_stress']
        reasons.append(f'High evaporation rate [+{V1_WEIGHTS["evap_stress"]}]')
        reasons_ar.append(f'معدل تبخر مرتفع [+{V1_WEIGHTS["evap_stress"]}]')

    composite = features.get('stress_composite', 0)
    if composite >= 0.6:
        score += V1_WEIGHTS['composite_bonus']
        reasons.append(f'Multi-stress co-occurrence (composite={composite:.2f}) [+{V1_WEIGHTS["composite_bonus"]}]')
        reasons_ar.append(f'تزامن وتداخل ضغوط بيئية متعددة (المركب={composite:.2f}) [+{V1_WEIGHTS["composite_bonus"]}]')

    # --- Dynamic Continuous Scaling (Makes UI sliders feel responsive instantly) ---
    continuous_score = 0.0
    
    # Temperature dynamic penalty (starts above 28C)
    if temp_c > 28.0 and features.get('temp_above_critical', 0) == 0:
        penalty = (temp_c - 28.0) * 0.8  # e.g., 35C -> +5.6 points
        continuous_score += penalty
        
    # Soil moisture dynamic penalty (starts below 0.25)
    sm1 = features.get('soil_moisture_l1', 0.1)
    if sm1 < 0.25 and not features.get('water_stress_flag', 0):
        penalty = (0.25 - sm1) * 40.0    # e.g., 0.15 -> +4.0 points
        continuous_score += penalty
        
    # NDVI dynamic penalty (starts below 0.6)
    if ndvi < 0.6 and ndvi >= VEG_STRESS['ndvi_healthy']:
        penalty = (0.6 - ndvi) * 15.0    # e.g., 0.4 -> +3.0 points
        continuous_score += penalty
        
    if continuous_score > 0:
        score += continuous_score
        # We don't add reasoning for micro-adjustments to avoid cluttering the UI

    return min(score, 100.0), reasons, reasons_ar

def predict_risk_v1_protected(features: Dict[str, float]) -> Dict[str, Any]:
    score, reasons, reasons_ar = _compute_v1_risk_score_protected(features)
    if   score >= V1_THRESHOLDS['critical']: level = 'Critical'
    elif score >= V1_THRESHOLDS['high']:     level = 'High'
    elif score >= V1_THRESHOLDS['moderate']: level = 'Moderate'
    else:                                    level = 'Low'
    return {
        'risk_level': level,
        'risk_score': round(score, 1),
        'action': ACTIONS[level],
        'action_ar': ACTIONS_AR[level],
        'reasons': reasons,
        'reasons_ar': reasons_ar,
        'model': 'EWS-PA-v1-rules-v2.3'
    }

def ensemble_stats(ensemble: Dict, X_row: pd.DataFrame) -> Dict[str, Any]:
    individual = {}
    for name, info in ensemble.items():
        # Ensure correct columns order
        cols = info['cols']
        individual[name] = float(info['model'].predict_proba(X_row[cols])[:, 1][0])
    
    names   = list(individual.keys())
    probs   = np.array([individual[n] for n in names])
    weights = np.array([ENSEMBLE_WEIGHTS.get(n, 1.0/3.0) for n in names])
    weights /= weights.sum()
    
    mean    = float(probs @ weights)
    std     = float(probs.std())
    conf    = float(np.clip(1.0 - std / (mean + 1e-9), 0.0, 1.0))
    return {
        'mean_prob'       : round(mean, 4),
        'std_prob'        : round(std, 4),
        'confidence'      : round(conf, 4),
        'model_agreement' : std < ENSEMBLE_DISAGREE,
        'individual_probs': {k: round(v, 4) for k, v in individual.items()}
    }

def ml_to_risk_schema(prob: float, threshold: float = DECISION_THRESHOLD) -> Dict:
    if   prob >= 0.75: level = 'Critical'
    elif prob >= 0.55: level = 'High'
    elif prob >= 0.35: level = 'Moderate'
    else:              level = 'Low'
    return {'risk_level': level, 'risk_score': round(prob * 100, 1),
            'action': ACTIONS[level], 'action_ar': ACTIONS_AR[level], 'model': 'EWS-PA-v2-ml'}

def fuse_v1_v2_protected(
    v1_result : Dict,
    v2_stats  : Dict,
    threshold : float = DECISION_THRESHOLD
) -> Dict:
    mean_prob  = v2_stats['mean_prob']
    confidence = v2_stats['confidence']
    agreement  = v2_stats['model_agreement']

    v1_reasoning = v1_result.get('reasons', [])
    v1_reasoning_ar = v1_result.get('reasons_ar', [])
    
    # Convert V1 score to probability
    v1_prob = v1_result['risk_score'] / 100.0

    # Branch 1: high confidence ML (mean_prob ≥ 0.55 AND models agree)
    if mean_prob >= THRESH_HIGH_CONF and agreement:
        # Keep mostly ML, but blend 15% V1 so sliders always trigger a micro-response
        reactive_prob = 0.85 * mean_prob + 0.15 * v1_prob
        schema = ml_to_risk_schema(reactive_prob, threshold)
        return {**schema,
                'stress_probability': round(reactive_prob, 4),
                'stress_predicted'  : reactive_prob >= threshold,
                'confidence'        : confidence,
                'fusion_branch'     : 'v2_high_confidence (Reactive)',
                'human_review'      : False,
                'v1_risk_level'     : v1_result['risk_level'],
                'reasoning'         : v1_reasoning,
                'reasoning_ar'      : v1_reasoning_ar}

    # Branch 2: low confidence → fallback to v1
    if mean_prob <= THRESH_LOW_CONF or not agreement:
        # Rely heavily on V1 score since ML is uncertain
        reactive_prob = 0.2 * mean_prob + 0.8 * v1_prob
        v1_positive = reactive_prob >= threshold
        schema = ml_to_risk_schema(reactive_prob, threshold)
        return {**schema,
                'stress_probability': round(reactive_prob, 4),
                'stress_predicted'  : v1_positive,
                'confidence'        : confidence,
                'fusion_branch'     : 'v1_fallback (Reactive)',
                'human_review'      : True,
                'reasoning'         : v1_reasoning,
                'reasoning_ar'      : v1_reasoning_ar}

    # Branch 3: blend + human review (0.10 < mean_prob < 0.55)
    blend_prob = 0.5 * mean_prob + 0.5 * v1_prob
    schema     = ml_to_risk_schema(blend_prob, threshold)
    return {**schema,
            'stress_probability': round(blend_prob, 4),
            'stress_predicted'  : blend_prob >= threshold,
            'confidence'        : confidence,
            'fusion_branch'     : 'blended (Reactive)',
            'human_review'      : True,
            'v1_risk_level'     : v1_result['risk_level'],
            'reasoning'         : v1_reasoning,
            'reasoning_ar'      : v1_reasoning_ar}

def explain_prediction(X_row: pd.DataFrame, top_n: int = 10) -> Dict[str, Any]:
    if SHAP_EXPLAINER is None or 'xgb' not in ENSEMBLE:
        return {'feature_impacts': [], 'base_value': 0.0}
    try:
        cols = ENSEMBLE['xgb']['cols']
        shap_vals = SHAP_EXPLAINER.shap_values(X_row[cols])
        sv        = shap_vals[1][0] if isinstance(shap_vals, list) else shap_vals[0]
        feats     = cols
        impacts   = sorted(
            [{'feature': f, 'shap_value': round(float(s), 5),
              'feature_value': round(float(X_row[f].iloc[0]), 4)}
             for f, s in zip(feats, sv)],
            key=lambda x: abs(x['shap_value']), reverse=True
        )[:top_n]
        base_val = SHAP_EXPLAINER.expected_value
        if isinstance(base_val, list): base_val = base_val[1]
        return {'feature_impacts': impacts, 'base_value': round(float(base_val), 5)}
    except Exception as e:
        logger.warning(f"SHAP explanation computation failed: {e}")
        return {'feature_impacts': [], 'base_value': 0.0}

def predict_stress(
    query     : ProtectedAreaQuery,
    ensemble  : Optional[Dict]  = None,
    threshold : Optional[float] = None,
    mode      : str             = 'production'
) -> Dict[str, Any]:
    if ensemble is None: ensemble = ENSEMBLE
    if threshold is None:
        threshold = SAFETY_THRESHOLD if mode == 'safety_audit' else DECISION_THRESHOLD

    t_start = dt.datetime.now()

    feats = engineer_features_protected(query.data_row)
    
    # Construct input dataframe matching model features
    X_infer = pd.DataFrame([feats])
    for col in FEATURE_NAMES:
        if col not in X_infer.columns:
            X_infer[col] = 0.0
    X_infer = X_infer[FEATURE_NAMES]

    v1_result = predict_risk_v1_protected(feats)
    stats     = ensemble_stats(ensemble, X_infer)
    final     = fuse_v1_v2_protected(v1_result, stats, threshold)

    explanation = explain_prediction(X_infer)
    elapsed_ms = (dt.datetime.now() - t_start).total_seconds() * 1000

    payload = EwsReportPayload(
        area_name=PROTECTED_AREAS.get(query.area_id, '?'),
        area_id=query.area_id,
        risk_level=final['risk_level'],
        stress_probability=float(final['stress_probability']),
        action=final['action'],
        action_ar=final.get('action_ar', ''),
        reasoning=final.get('reasoning', []),
        reasoning_ar=final.get('reasoning_ar', []),
        shap_explanation=explanation
    )
    report_outputs = render_full_report(payload)

    return {
        'query_id'           : query.query_id,
        'timestamp'          : dt.datetime.utcnow().isoformat() + 'Z',
        'area_id'            : query.area_id,
        'area_name'          : PROTECTED_AREAS.get(query.area_id, '?'),
        'mode'               : mode,
        'stress_predicted'   : bool(final['stress_predicted']),
        'stress_probability' : float(final['stress_probability']),
        'risk_level'         : final['risk_level'],
        'risk_score'         : float(final['risk_score']),
        'action'             : final['action'],
        'action_ar'          : final.get('action_ar', ''),
        'confidence'         : float(final['confidence']),
        'human_review'       : bool(final['human_review']),
        'fusion_branch'      : final['fusion_branch'],
        'individual_probs'   : stats['individual_probs'],
        'reasoning'          : final.get('reasoning', []),
        'reasoning_ar'       : final.get('reasoning_ar', []),
        'shap_explanation'   : explanation,
        'inference_ms'       : round(elapsed_ms, 1),
        'model_version'      : 'EWS-PA-v2.3',
        'report_en'          : report_outputs['text_en'],
        'report_ar'          : report_outputs['text_ar'],
        'report_html'        : report_outputs['html']
    }

def validate_query_input(query: ProtectedAreaQuery) -> Dict[str, Any]:
    report = {'valid': True, 'warnings': [], 'flags': []}
    row    = query.data_row

    if query.area_id not in PROTECTED_AREAS:
        raise ValueError(
            f'area_id={query.area_id} is not valid. '
            f'Must be one of: {sorted(PROTECTED_AREAS.keys())}'
        )

    if isinstance(row, pd.Series):
        available = set(row.index)
    else:
        available = set(row.keys())

    missing = [c for c in REQUIRED_COLUMNS if c not in available]
    if missing:
        raise ValueError(
            f'Missing required columns for query {query.query_id}: {missing}'
        )

    nulls = [c for c in REQUIRED_COLUMNS if pd.isna(row.get(c, None))]
    if nulls:
        raise ValueError(
            f'NaN values in required columns for query {query.query_id}: {nulls}'
        )

    temp_k = float(row.get('temperature_2m', 295.0))
    if not (250.0 <= temp_k <= 330.0):
        msg = (
            f'[{query.query_id}] temperature_2m={temp_k:.1f} K is outside '
            f'expected range [250, 330] K — possible unit error or sensor fault'
        )
        logger.warning(msg)
        report['warnings'].append(msg)
        report['flags'].append('temperature_out_of_range')

    ndvi = float(row.get('ndvi_mean', 0.0))
    if not (-0.5 <= ndvi <= 1.0):
        msg = (
            f'[{query.query_id}] ndvi_mean={ndvi:.4f} is outside '
            f'valid range [-0.5, 1.0] — possible satellite artifact'
        )
        logger.warning(msg)
        report['warnings'].append(msg)
        report['flags'].append('ndvi_out_of_range')

    sm1 = float(row.get('volumetric_soil_water_layer_1', 0.0))
    if not (-0.01 <= sm1 <= 1.0):
        msg = (
            f'[{query.query_id}] soil_moisture_l1={sm1:.4f} is outside '
            f'valid range [0, 1] m³/m³'
        )
        logger.warning(msg)
        report['warnings'].append(msg)
        report['flags'].append('soil_moisture_out_of_range')

    report['valid'] = True
    return report

def log_prediction(
    result       : Dict[str, Any],
    validation   : Dict[str, Any],
    ground_truth : Optional[int] = None
) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        record = {
            'query_id'           : result.get('query_id'),
            'timestamp'          : result.get('timestamp'),
            'model_version'      : result.get('model_version'),
            'area_id'            : result.get('area_id'),
            'area_name'          : result.get('area_name'),
            'mode'               : result.get('mode'),
            'stress_predicted'   : result.get('stress_predicted'),
            'stress_probability' : result.get('stress_probability'),
            'risk_level'         : result.get('risk_level'),
            'risk_score'         : result.get('risk_score'),
            'fusion_branch'      : result.get('fusion_branch'),
            'human_review'       : result.get('human_review'),
            'confidence'         : result.get('confidence'),
            'prob_xgb'           : result.get('individual_probs', {}).get('xgb'),
            'prob_rf'            : result.get('individual_probs', {}).get('rf'),
            'prob_lr'            : result.get('individual_probs', {}).get('lr'),
            'inference_ms'       : result.get('inference_ms'),
            'validation_warnings': validation.get('warnings', []),
            'validation_flags'   : validation.get('flags', []),
            'ground_truth'       : ground_truth,
        }
        with open(LOG_FILE, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception as exc:
        logger.error('Failed to log prediction %s: %s', result.get('query_id'), exc)

def predict_stress_safe(
    query        : ProtectedAreaQuery,
    ensemble     : Optional[Dict]  = None,
    threshold    : Optional[float] = None,
    mode         : str             = 'production',
    ground_truth : Optional[int]   = None,
    do_log       : bool            = True,
) -> Dict[str, Any]:
    try:
        validation = validate_query_input(query)
    except ValueError as ve:
        logger.error('Input validation FAILED for %s: %s', query.query_id, ve)
        return {
            'query_id'   : query.query_id,
            'area_id'    : query.area_id,
            'timestamp'  : dt.datetime.utcnow().isoformat() + 'Z',
            'status'     : 'validation_error',
            'error'      : str(ve),
            'stress_predicted' : None,
        }

    try:
        result = predict_stress(
            query     = query,
            ensemble  = ensemble,
            threshold = threshold,
            mode      = mode,
        )
        result['status'] = 'ok'
    except Exception as exc:
        logger.error('Inference FAILED for %s: %s', query.query_id, exc, exc_info=True)
        return {
            'query_id'   : query.query_id,
            'area_id'    : query.area_id,
            'timestamp'  : dt.datetime.utcnow().isoformat() + 'Z',
            'status'     : 'inference_error',
            'error'      : str(exc),
            'stress_predicted' : None,
        }

    if do_log:
        log_prediction(result, validation, ground_truth)

    return result

def get_ews_prediction(inputs: dict, mode: str = "production") -> dict:
    """
    Main entry point for web API calls.
    inputs: dictionary containing area_id and all REQUIRED_COLUMNS values.
    """
    area_id = int(inputs.get("area_id", 0))
    query_id = inputs.get("query_id", f"API-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    # If area_name is provided, map to area_id
    if "area_name" in inputs and inputs["area_name"] in AREA_IDX:
        area_id = AREA_IDX[inputs["area_name"]]
        
    data_row = pd.Series(inputs)
    data_row['area_id'] = area_id
    
    query = ProtectedAreaQuery(query_id=query_id, area_id=area_id, data_row=data_row)
    return predict_stress_safe(query, mode=mode)
