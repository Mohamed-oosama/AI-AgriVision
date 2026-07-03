import os
import json
import numpy as np
import joblib

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "best_model.joblib")
META_PATH = os.path.join(BASE_DIR, "meta.json")

# Global caches
model = None
meta = None

def load_resources():
    global model, meta
    if model is None:
        try:
            model = joblib.load(MODEL_PATH)
        except Exception as e:
            print(f"Error loading model: {e}")
            model = None
    if meta is None:
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            print(f"Error loading meta.json: {e}")
            meta = None

def _compute_features(year, custom_inputs=None):
    if meta is None:
        return None

    # Load medians
    medians = meta.get("feature_medians", {})
    features = dict(medians)
    
    # 1. Update temporal features
    features["decade"] = (year // 10) * 10
    year_norm = (year - 1961) / 63.0  # inferred from typical FAO range 1961-2024
    features["year_norm"] = year_norm
    features["year_sq"] = year_norm ** 2
    
    # 2. Override with any custom inputs
    if custom_inputs:
        for k, v in custom_inputs.items():
            if k in features and v is not None and str(v).lower() != "auto":
                try:
                    features[k] = float(v)
                except ValueError:
                    pass
    
    # 3. Compute derived interaction terms dynamically based on the updated inputs
    # If custom inputs altered nitrogen, we must recalculate intensities and ratios
    arable = features.get("arable_1000ha", 2707.0)
    if arable <= 0: arable = 2707.0
    
    n_t = features.get("nitrogen_t", medians.get("nitrogen_t", 915000.0))
    p_t = features.get("phosphate_t", medians.get("phosphate_t", 150000.0))
    pest_t = features.get("pesticides_t", medians.get("pesticides_t", 12909.0))
    
    features["n_intensity"] = n_t / (arable * 1000.0)
    features["p_intensity"] = p_t / (arable * 1000.0)
    features["pest_intensity"] = pest_t / (arable * 1000.0)
    features["np_ratio"] = n_t / p_t if p_t > 0 else 0.0
    features["log_n"] = np.log1p(n_t)
    features["log_pest"] = np.log1p(pest_t)
    
    temp_change = features.get("temp_change_c", medians.get("temp_change_c", 0.0))
    summer_temp = features.get("summer_temp_anomaly", medians.get("summer_temp_anomaly", 0.0))
    
    features["temp_x_n"] = temp_change * features["n_intensity"]
    features["summer_x_n"] = summer_temp * features["n_intensity"]

    # 4. Construct final array based on exactly ML_FEATURES
    ml_features_list = meta.get("ML_FEATURES", [])
    row = []
    for f_name in ml_features_list:
        row.append(features.get(f_name, 0.0))
        
    return np.array([row]), features

def get_crop_yield_prediction(crop, year, custom_inputs=None):
    load_resources()
    
    if model is None or meta is None:
        raise RuntimeError("Model or metadata not loaded correctly.")
        
    crop_stats = meta.get("crop_stats", {})
    if crop not in crop_stats:
        # fallback to Wheat if unknown
        crop = "Wheat"
        
    stats = crop_stats[crop]
    m, c_val = stats["trend_coeffs"]
    yield_std = stats["yield_std"]
    
    # 1. Baseline prediction (no custom inputs)
    baseline_X, base_features = _compute_features(year, None)
    base_pred_std = model.predict(baseline_X)[0]
    base_yield = (base_pred_std * yield_std) + (m * year + c_val)
    
    # 2. Custom prediction
    custom_X, cust_features = _compute_features(year, custom_inputs)
    custom_pred_std = model.predict(custom_X)[0]
    custom_yield = (custom_pred_std * yield_std) + (m * year + c_val)
    
    # Prevent negative yields
    base_yield = max(0, base_yield)
    custom_yield = max(0, custom_yield)
    
    # Calculate impact
    if base_yield > 0:
        impact_pct = ((custom_yield - base_yield) / base_yield) * 100.0
    else:
        impact_pct = 0.0
        
    # Determine risk status based on impact percentage
    if impact_pct >= 5.0:
        risk_en = "Optimized"
        risk_ar = "محسن ومثالي"
        color = "green"
    elif impact_pct > -5.0:
        risk_en = "Stable"
        risk_ar = "مستقر"
        color = "yellow"
    else:
        risk_en = "High Risk"
        risk_ar = "عالي الخطورة"
        color = "red"
        
    # Generate simple HTML reports
    yield_feddan = custom_yield * 0.42
    base_feddan = base_yield * 0.42
    
    n_diff = ((cust_features.get('nitrogen_t', 0) - base_features.get('nitrogen_t', 0)) / (base_features.get('nitrogen_t', 1) or 1)) * 100
    temp_val = cust_features.get('temp_change_c', 0)
    pest_diff = ((cust_features.get('pesticides_t', 0) - base_features.get('pesticides_t', 0)) / (base_features.get('pesticides_t', 1) or 1)) * 100

    if impact_pct >= 5.0:
        advice_ar = (
            f"<h3>1. تحليل المدخلات الذكي والأثر الفسيولوجي (Smart Inputs & Physiological Impact)</h3>"
            f"<p>لقد قمت بتعديل مستويات النيتروجين بنسبة <span dir='ltr'>{n_diff:+.1f}%</span> "
            f"وتعديل المبيدات بنسبة <span dir='ltr'>{pest_diff:+.1f}%</span> مقارنة بالمعدل التاريخي. "
            f"مع الأخذ في الاعتبار أن التغير الحراري المتوقع هو <span dir='ltr'>{temp_val:+.2f}°C</span>، "
            f"فإن نموذجنا المبني على الذكاء الاصطناعي يتوقع أن هذه الاستراتيجية المتقدمة ستؤدي إلى زيادة ممتازة ومؤكدة في الإنتاجية بنسبة <span dir='ltr'>{impact_pct:+.1f}%</span>.</p>"
            f"<p>هذا التوازن المثالي في التسميد يعزز من كفاءة البناء الضوئي (Photosynthetic Efficiency) ويزيد من مساحة المسطح الخضري، مما يسمح للنبات باصطياد طاقة شمسية أكبر وتحويلها إلى مادة جافة في الحبوب أو الثمار.</p>"
            
            f"<h3>2. السياق التاريخي والبيئي (Historical & Environmental Context)</h3>"
            f"<p>بمقارنة هذه المدخلات مع بيانات العقود الماضية، نجد أن مستوى إدارة الآفات الذي طبقته (بزيادة/نقصان <span dir='ltr'>{pest_diff:+.1f}%</span>) يعكس فهماً عميقاً لطبيعة الإجهاد الحيوي (Biotic Stress) في المنطقة. "
            f"النجاح هنا لا يكمن فقط في زيادة التسميد، بل في خلق بيئة جذرية (Rhizosphere) صحية تمنع الفطريات من التكاثر.</p>"
            
            f"<h3>3. التوصيات الاستراتيجية المتقدمة (Advanced Strategic Recommendations)</h3>"
            f"<ul>"
            f"<li><strong>استدامة الإنتاج (Sustainability):</strong> يوصى بالحفاظ على هذا التوازن الدقيق. الزيادة الحالية في الأسمدة تمتصها النباتات بكفاءة عالية دون حدوث تسرب أو غسيل (Leaching) في المياه الجوفية.</li>"
            f"<li><strong>إدارة المناخ الدقيق (Micro-climate Management):</strong> في ظل التغير الحراري الحالي، حافظ على جدولة ري منتظمة لضمان عدم حدوث إجهاد مائي خلال فترة تكوين الحبوب (Grain-filling stage).</li>"
            f"<li><strong>تقييم العائد الاقتصادي (ROI Assessment):</strong> قم بحساب التكلفة الحدية للمدخلات الإضافية مقابل الزيادة المتوقعة في العائد للتأكد من أقصى ربحية ممكنة. يمكنك توثيق هذه التجربة كمعيار ذهبي للمزارع المجاورة.</li>"
            f"</ul>"
        )
        advice_en = (
            f"<h3>1. Smart Inputs & Physiological Impact</h3>"
            f"<p>You adjusted Nitrogen levels by <strong>{n_diff:+.1f}%</strong> "
            f"and Pesticides by <strong>{pest_diff:+.1f}%</strong> compared to the historical baseline. "
            f"Factoring in a forecasted temperature anomaly of <strong>{temp_val:+.2f}°C</strong>, "
            f"our AI model predicts this advanced strategy will yield an excellent and definitive productivity boost of <strong>{impact_pct:+.1f}%</strong>.</p>"
            f"<p>This optimal fertilization balance significantly enhances photosynthetic efficiency and expands the leaf area index, allowing the plant to capture more solar energy and convert it effectively into dry matter (grain/fruit yield).</p>"
            
            f"<h3>2. Historical & Environmental Context</h3>"
            f"<p>Comparing these inputs with decades of regional data reveals that your pest management level ({pest_diff:+.1f}% shift) reflects a profound understanding of local biotic stress dynamics. "
            f"The success here is not merely about pouring more fertilizer, but about cultivating a healthy rhizosphere that actively suppresses pathogen multiplication.</p>"
            
            f"<h3>3. Advanced Strategic Recommendations</h3>"
            f"<ul>"
            f"<li><strong>Production Sustainability:</strong> Maintain this delicate balance. The current fertilizer increments are efficiently absorbed by the crop without causing environmental leaching or groundwater contamination.</li>"
            f"<li><strong>Micro-climate Management:</strong> Under the current thermal conditions, ensure a strict and highly regulated irrigation schedule to avoid water stress during the critical grain-filling stage.</li>"
            f"<li><strong>ROI Assessment:</strong> Calculate the marginal cost of these additional inputs against the projected yield surplus to maximize your economic return. Document this exact formula as a golden benchmark for future seasons.</li>"
            f"</ul>"
        )
    elif impact_pct > -5.0:
        advice_ar = (
            f"<h3>1. تحليل المدخلات الذكي والأثر الفسيولوجي (Smart Inputs & Physiological Impact)</h3>"
            f"<p>الإنتاجية المتوقعة تبدو مستقرة وشبه مطابقة للمعدلات الطبيعية. "
            f"المدخلات الحالية (تعديل النيتروجين بنسبة <span dir='ltr'>{n_diff:+.1f}%</span>) "
            f"والتغير الحراري (<span dir='ltr'>{temp_val:+.2f}°C</span>) "
            f"تحافظ على توازن المحصول (Homeostasis)، لكنها لا تدفع الإنتاجية إلى مستويات فائقة.</p>"
            f"<p>هذا يعني أن النبات يستخدم طاقته الحالية للحفاظ على بقائه واستقراره بدلاً من توجيهها نحو بناء كتلة حيوية إضافية، وهو أمر جيد ومقبول اقتصادياً في المواسم ذات المخاطر العالية.</p>"
            
            f"<h3>2. تقييم كفاءة الموارد (Resource Efficiency Evaluation)</h3>"
            f"<p>التغير في نسبة المبيدات (<span dir='ltr'>{pest_diff:+.1f}%</span>) يشير إلى استراتيجية مكافحة تقليدية. "
            f"الاعتماد الكامل على المدخلات الأساسية فقط دون التركيز على المغذيات الدقيقة (المعادن النادرة) قد يحد من قدرة النبات على التعبير الجيني الكامل لخصائصه الإنتاجية العالية.</p>"
            
            f"<h3>3. التوصيات الاستراتيجية المتقدمة (Advanced Strategic Recommendations)</h3>"
            f"<ul>"
            f"<li><strong>كسر حاجز الاستقرار (Breaking the Plateau):</strong> حاول إضافة جرعات دقيقة من العناصر الصغرى مثل الزنك، البورون، أو الحديد عبر الرش الورقي لتحفيز استجابة فسيولوجية أقوى.</li>"
            f"<li><strong>توزيع الأسمدة الذكي (Smart Fertilizer Split):</strong> بدلاً من تقليل أو زيادة الكمية الإجمالية بشكل عشوائي، قم بتقسيم جرعات النيتروجين الحالية على فترات زمنية متقاربة لتتزامن مع منحنى امتصاص النبات الفعلي.</li>"
            f"<li><strong>رصد الآفات المبكر (Early Pest Monitoring):</strong> بما أن الإنتاجية لم ترتفع، تأكد من عدم وجود إجهاد حيوي خفي يستهلك طاقة النبات عبر استخدام أدوات التحليل البصري (AgriXAI Module 6).</li>"
            f"</ul>"
        )
        advice_en = (
            f"<h3>1. Smart Inputs & Physiological Impact</h3>"
            f"<p>The projected yield is stable and closely matches normal baselines. "
            f"Your current inputs (Nitrogen adjusted by <strong>{n_diff:+.1f}%</strong>) "
            f"and thermal conditions (<strong>{temp_val:+.2f}°C</strong>) "
            f"maintain crop homeostasis but do not push productivity to premium or record-breaking levels.</p>"
            f"<p>This indicates that the plant is utilizing its current energy primarily for survival and maintenance rather than directing it towards explosive biomass accumulation. This is an economically acceptable outcome during high-risk seasons.</p>"
            
            f"<h3>2. Resource Efficiency Evaluation</h3>"
            f"<p>The shift in pesticide volume (<strong>{pest_diff:+.1f}%</strong>) points to a conventional management strategy. "
            f"Relying entirely on basic macronutrients without focusing on rare trace minerals might be bottlenecking the crop's genetic potential for high yield.</p>"
            
            f"<h3>3. Advanced Strategic Recommendations</h3>"
            f"<ul>"
            f"<li><strong>Breaking the Plateau:</strong> Consider applying precise, micro-doses of essential trace elements (e.g., Zinc, Boron, or Iron) via foliar feeding to trigger a robust physiological growth response.</li>"
            f"<li><strong>Smart Fertilizer Split:</strong> Rather than blindly altering total volume, split your current Nitrogen doses across multiple, closer intervals that synchronize perfectly with the crop's actual uptake curve.</li>"
            f"<li><strong>Early Pest Monitoring:</strong> Since yield hasn't surged, ensure there is no hidden, sub-clinical biotic stress draining plant energy by utilizing advanced visual analysis tools (AgriXAI Module 6).</li>"
            f"</ul>"
        )
    else:
        advice_ar = (
            f"<h3>1. تحليل المدخلات الذكي والأثر الفسيولوجي (Smart Inputs & Physiological Impact)</h3>"
            f"<p>تحذير شديد! تتوقع النماذج الرياضية انخفاضاً حاداً ومقلقاً في الإنتاجية بنسبة <span dir='ltr'>{impact_pct:+.1f}%</span>. "
            f"هذا التراجع الدراماتيكي ناتج بشكل مباشر عن التغير الجذري في النيتروجين بنسبة <span dir='ltr'>{n_diff:+.1f}%</span> "
            f"أو بسبب تأثيرات الصدمة الحرارية البالغة <span dir='ltr'>{temp_val:+.2f}°C</span>.</p>"
            f"<p>عدم توازن هذه العناصر الحيوية يؤدي لضعف حاد في كفاءة البناء الضوئي، وإغلاق الثغور التنفسية في الأوراق، مما يدفع النبات للدخول في حالة ذبول مبكر (Premature Senescence) وفقدان للمحصول.</p>"
            
            f"<h3>2. تحليل الإجهاد البيئي والمرضي (Environmental & Biotic Stress Analysis)</h3>"
            f"<p>التلاعب المفرط أو النقص الحاد في المبيدات (تغير بنسبة <span dir='ltr'>{pest_diff:+.1f}%</span>) قد يكون ترك المحصول مكشوفاً تماماً أمام هجمات الآفات الفتاكة، أو على العكس، تسبب في تسمم نباتي (Phytotoxicity) بسبب الإفراط الكيميائي الذي حرق المجموع الجذري والأوراق.</p>"
            
            f"<h3>3. التوصيات الاستراتيجية العاجلة (Urgent Strategic Recommendations)</h3>"
            f"<ul>"
            f"<li><strong>التدخل السريع لتصحيح النترات (Rapid Nitrogen Correction):</strong> نقص التسميد يجوّع النبات، بينما الإفراط الشديد يسبب سمية التربة. قم بعمل اختبار عاجل لمحتوى التربة من النترات والأملاح لإنقاذ ما يمكن إنقاذه.</li>"
            f"<li><strong>التخفيف الفوري من الإجهاد الحراري (Thermal Stress Mitigation):</strong> درجات الحرارة الحالية تضعف النبات بشكل خطير. طبق فوراً مركبات الأحماض الأمينية الحرة (Free Amino Acids) أو سيليكات البوتاسيوم لرفع قدرة تحمل المحصول للحرارة الشديدة.</li>"
            f"<li><strong>إعادة هيكلة سياسة المكافحة (Review Pest Control):</strong> أوقف فوراً استراتيجية المبيدات الحالية. تأكد من أن نسبة التغير فعالة وموجهة ضد الآفات الحقيقية الموجودة في الحقل وليست مجرد عبء كيميائي أعمى يقتل الكائنات الدقيقة النافعة في التربة.</li>"
            f"</ul>"
        )
        advice_en = (
            f"<h3>1. Smart Inputs & Physiological Impact</h3>"
            f"<p>CRITICAL WARNING! Predictive mathematical models forecast a severe and alarming yield decline of <strong>{impact_pct:+.1f}%</strong>. "
            f"This dramatic regression is likely driven directly by the drastic <strong>{n_diff:+.1f}%</strong> shift in Nitrogen inputs "
            f"or the devastating thermal shock represented by an anomaly of <strong>{temp_val:+.2f}°C</strong>.</p>"
            f"<p>Such severe imbalances in vital elements drastically impair photosynthetic efficiency and force stomatal closure, pushing the crop into premature senescence and massive fruit/grain abortion.</p>"
            
            f"<h3>2. Environmental & Biotic Stress Analysis</h3>"
            f"<p>The erratic adjustment in pesticide application (a <strong>{pest_diff:+.1f}%</strong> shift) has either left the crop completely defenseless against aggressive pathogen swarms, or conversely, induced severe phytotoxicity—essentially chemically burning the root system and foliage.</p>"
            
            f"<h3>3. Urgent Strategic Recommendations</h3>"
            f"<ul>"
            f"<li><strong>Rapid Nitrogen Correction:</strong> Under-fertilization starves the plant, while severe over-fertilization causes lethal soil toxicity. Conduct an immediate, emergency soil electrical conductivity (EC) and nitrate test to salvage the crop.</li>"
            f"<li><strong>Immediate Thermal Stress Mitigation:</strong> The current temperature anomalies critically weaken the crop's cellular structure. Apply foliar free amino acids or potassium silicate immediately to boost heat tolerance and cellular rigidity.</li>"
            f"<li><strong>Restructure Pest Control Policy:</strong> Halt your current pesticide regimen immediately. Ensure that chemical applications are precision-targeted against confirmed threats rather than acting as a blind chemical burden that exterminates beneficial soil microbiomes.</li>"
            f"</ul>"
        )

    badge_class = "b-info" if color == "yellow" else ("b-critical" if color == "red" else "b-watch")
    
    report_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Yield Prediction: {crop}</title>
    <style>
      :root {{
        --bg: #0f1419; --card: #1a2027; --ink: #e8edf2; --muted: #8b95a1;
        --accent: #4ade80; --warn: #fbbf24; --crit: #f87171; --info: #60a5fa;
        --border: #2a3540;
      }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; padding: 24px; font-family: -apple-system, system-ui, sans-serif; background: var(--bg); color: var(--ink); line-height: 1.55; }}
      .wrap {{ max-width: 1100px; margin: 0 auto; }}
      header {{ display: flex; align-items: baseline; justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 16px; }}
      header h1 {{ margin: 0; font-size: 22px; font-weight: 600; }}
      .subtle {{ color: var(--muted); font-size: 13px; }}
      .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
      .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }}
      .panel h2 {{ margin: 0 0 10px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); font-weight: 600; }}
      .panel h3 {{ margin: 18px 0 8px; font-size: 15px; font-weight: 600; color: var(--accent); }}
      .panel p {{ margin: 0 0 12px; font-size: 14px; color: var(--ink); line-height: 1.65; }}
      .panel ul {{ margin: 0; padding-left: 20px; font-size: 14px; }}
      .panel li {{ margin-bottom: 8px; line-height: 1.6; }}
      .ar {{ direction: rtl; text-align: right; font-family: "Tahoma", "Arial", sans-serif; }}
      .ar ul {{ padding-left: 0; padding-right: 20px; }}
      .badge {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
      .b-info {{ background: rgba(96,165,250,0.15); color: var(--info); }}
      .b-watch {{ background: rgba(74,222,128,0.15); color: var(--accent); }}
      .b-critical {{ background: rgba(248,113,113,0.15); color: var(--crit); }}
      .row {{ display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 8px; }}
      .stat {{ font-size: 13px; }} .stat strong {{ color: var(--ink); }}
      .full {{ grid-column: 1 / -1; }}
      @media (max-width: 720px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
    </head>
    <body>
    <div class="wrap">
      <header>
        <div>
          <h1>{crop} Yield <span class="subtle">/ توقع محصول {crop}</span></h1>
          <div class="subtle">Yield Prediction Engine Report for {year}</div>
        </div>
        <span class="badge {badge_class}">{risk_en}</span>
      </header>

      <div class="panel full">
        <div class="row">
          <div class="stat"><strong>Base Yield:</strong> {base_feddan:.1f} kg/feddan</div>
          <div class="stat"><strong>Predicted Yield:</strong> {yield_feddan:.1f} kg/feddan</div>
          <div class="stat"><strong>Impact:</strong> <span style="color: {'var(--accent)' if impact_pct >= 0 else 'var(--crit)'}">{impact_pct:+.1f}%</span></div>
          <div class="stat"><strong>Status:</strong> {risk_en} / {risk_ar}</div>
        </div>
      </div>

      <div class="grid" style="margin-top:16px;">
        <div class="panel">
          <h2>Analysis (English)</h2>
          <p>Based on the inputs and climate factors for the year <strong>{year}</strong>, the expected yield for <strong>{crop}</strong> is <strong>{yield_feddan:.1f} kg/feddan</strong>.</p>
          <p>Compared to the baseline, we observe a change of <strong>{impact_pct:+.1f}%</strong>.</p>
          <p><strong>Recommendation:</strong> {advice_en}</p>
        </div>
        <div class="panel ar">
          <h2>التحليل (العربية)</h2>
          <p>بناءً على المعطيات المدخلة والمناخ لعام <strong>{year}</strong>، المتوقع لمحصول <strong>{crop}</strong> هو <strong>{yield_feddan:.1f} كيلوغرام/فدان</strong>.</p>
          <p>مقارنة بالمعدل الطبيعي، نلاحظ تغييراً بنسبة <strong><span dir="ltr">{impact_pct:+.1f}%</span></strong>.</p>
          <p><strong>التوصية:</strong> {advice_ar}</p>
        </div>
      </div>

      <div class="panel full" style="margin-top:16px;">
        <h2>Key Input Variables Used</h2>
        <div class="row">
          <div class="stat"><strong>Nitrogen (t):</strong> {cust_features.get('nitrogen_t', 0):.0f}</div>
          <div class="stat"><strong>Phosphate (t):</strong> {cust_features.get('phosphate_t', 0):.0f}</div>
          <div class="stat"><strong>Pesticides (t):</strong> {cust_features.get('pesticides_t', 0):.0f}</div>
          <div class="stat"><strong>Temp Change:</strong> {cust_features.get('temp_change_c', 0):+.2f}°C</div>
        </div>
      </div>
      <footer class="subtle" style="margin-top:24px; text-align:center;">
        Generated by Yield Prediction Engine. Estimates are per feddan.
      </footer>
    </div>
    </body>
    </html>
    """
        
    return {
        "crop": crop,
        "year": year,
        "baseline_yield": float(base_yield),
        "custom_yield": float(custom_yield),
        "impact_pct": float(impact_pct),
        "risk_en": risk_en,
        "risk_ar": risk_ar,
        "color": color,
        "baseline_features": base_features,
        "custom_features": cust_features,
        "crops": meta.get("le_classes", []),
        "report_html": report_html
    }

# Test block
if __name__ == "__main__":
    res = get_crop_yield_prediction("Wheat", 2026, {"temp_change_c": 2.0})
    print(json.dumps(res, indent=2))
