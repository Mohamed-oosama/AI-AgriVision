"""
xai_report.py
=============
Bilingual (Arabic / English) Deep Reasoning Reports for AgriXAI.

Produces three artifacts from a finalized diagnosis:
  1. report_text_en  -- plain-text English narrative
  2. report_text_ar  -- plain-text Arabic narrative (Egyptian-friendly diction)
  3. report_html     -- a self-contained Jinja2-rendered HTML page with both
                        languages side-by-side, KG path, counterfactual,
                        and intervention list.

The narrative format (per requirements):

    "Detected Xylotrechus with 92% confidence.
     KG path: Pests -> Wood Borers -> Xylotrechus -> Host: Grape.
     Counterfactual: Without systemic insecticide treatment, the internal
     structure of the vine will suffer 40% irreversible damage within 15 days."

Counterfactuals are generated from the KG's `damage_pct_untreated_15d` and the
class's recommended intervention list — no LLM required, fully deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from jinja2 import Environment, BaseLoader, select_autoescape
    _HAS_JINJA = True
except ImportError:  # pragma: no cover
    _HAS_JINJA = False


# ---------------------------------------------------------------------------
# Data carrier
# ---------------------------------------------------------------------------

@dataclass
class ReportPayload:
    """Everything the report needs in one place."""
    class_name: str
    label_en: str
    label_ar: str
    confidence: float
    category: str                          # disease | pest | deficiency
    kg_path_en: List[str]                  # e.g. ["AgriXAI KG", "Pest", "Vitaceae", ...]
    pathogens: List[str] = field(default_factory=list)
    triggers: Dict[str, Any] = field(default_factory=dict)
    biological_controls: List[str] = field(default_factory=list)
    chemical_controls: List[str] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    predators: List[str] = field(default_factory=list)
    damage_pct_15d: float = 0.0
    severity: str = "info"
    differential_explanation: List[str] = field(default_factory=list)
    yield_rationale: str = ""
    weather_summary: str = ""


# ---------------------------------------------------------------------------
# Narrative builders
# ---------------------------------------------------------------------------

def _kg_path_string(path: List[str]) -> str:
    if not path:
        return "(no path)"
    # Drop the very first "AgriXAI KG" root for readability
    if path and path[0].lower().startswith("agrixai"):
        path = path[1:]
    return " → ".join(path)


def build_text_en(p: ReportPayload) -> str:
    lines = []
    lines.append(f"Detected {p.label_en} with {p.confidence:.0%} confidence.")
    lines.append(f"KG path: {_kg_path_string(p.kg_path_en)}.")
    if p.pathogens:
        lines.append(f"Causal agent: {', '.join(p.pathogens)}.")
    if p.triggers:
        t = p.triggers
        trig_parts = []
        if t.get("temp_c"):
            lo, hi = t["temp_c"]
            trig_parts.append(f"temperature {lo}–{hi}°C")
        if t.get("humidity_pct_min") is not None and t.get("humidity_pct_min") > 0:
            trig_parts.append(f"humidity ≥ {t['humidity_pct_min']}%")
        if t.get("season"):
            trig_parts.append(f"season {'/'.join(t['season'])}")
        if trig_parts:
            lines.append("Environmental triggers: " + ", ".join(trig_parts) + ".")
    if p.weather_summary:
        lines.append(f"Current conditions: {p.weather_summary}")

    if p.damage_pct_15d > 0:
        primary_treatment = (p.chemical_controls or p.biological_controls or ["recommended treatment"])[0]
        lines.append(
            f"Counterfactual: Without {primary_treatment}, the affected crop will "
            f"suffer ~{p.damage_pct_15d:.0f}% damage within 15 days."
        )
    if p.severity:
        lines.append(f"Economic severity: {p.severity.upper()}. {p.yield_rationale}")
    if p.differential_explanation:
        lines.append("Differential reasoning:")
        lines.extend(f"  • {b}" for b in p.differential_explanation)
    if p.biological_controls:
        lines.append("Recommended biological controls: " + "; ".join(p.biological_controls) + ".")
    if p.chemical_controls:
        lines.append("Recommended chemical controls: " + "; ".join(p.chemical_controls) + ".")
    if p.cultural_controls:
        lines.append("Cultural practices: " + "; ".join(p.cultural_controls) + ".")
    if p.predators:
        lines.append("Natural predators / biological allies: " + ", ".join(p.predators) + ".")
    return "\n".join(lines)


import re

AR_TRANSLATIONS = {
    # Pathogens
    "Unknown Pathogen/Agent": "عامل ممرض / مسبب غير معروف",
    
    # Predators
    "Anastatus orientalis (egg parasitoid)": "طفيلي البيض Anastatus orientalis",
    "Cyrtorhinus lividipennis": "البق النافع Cyrtorhinus lividipennis",
    "Lycosa pseudoannulata": "العنكبوت الذئبي Lycosa pseudoannulata",
    "Parasitic wasps (Braconidae)": "الدبابير الطفيلية (Braconidae)",
    "Praying mantis": "فرس النبي (سرعوف)",
    "Spiders (Lycosidae)": "عناكب Lycosidae",
    "Trichogramma japonicum": "دبابير Trichogramma japonicum",
    "Woodpeckers": "نقار الخشب",

    # Cultural Controls
    "Address potassium deficiency": "علاج نقص البوتاسيوم",
    "Avoid excess nitrogen": "تجنب التسميد النيتروجيني الزائد",
    "Avoid excessive K and Mg fertilization": "تجنب التسميد المفرط بالبوتاسيوم والمغنيسيوم",
    "Avoid late nitrogen application": "تجنب إضافة النيتروجين في وقت متأخر",
    "Balanced N fertilization": "التسميد النيتروجيني المتوازن",
    "Crop rotation": "الدورة الزراعية",
    "Drain field for 3-4 days": "تجفيف الحقل لمدة 3-4 أيام",
    "Drip irrigation (avoid overhead)": "الري بالتنقيط (تجنب الري العلوي)",
    "Early sowing": "التبكير في الزراعة",
    "Egg-mass scraping in winter": "كشط كتل البيض في الشتاء",
    "Eradicate barberry near wheat fields": "استئصال نبات البربري بالقرب من حقول القمح",
    "Lower soil pH with elemental sulfur": "خفض حموضة التربة (pH) باستخدام الكبريت الزراعي",
    "Lower-leaf removal": "إزالة الأوراق السفلية",
    "Maintain field sanitation": "الحفاظ على نظافة وتطهير الحقل",
    "Mulch with coffee pulp": "التغطية بمخلفات البن",
    "Mulching": "التغطية (المالتش)",
    "Prune and burn infested wood": "تقليم وحرق الخشب المصاب",
    "Remove tree-of-heaven hosts": "إزالة أشجار السماء (العائل الحشري)",
    "Remove volunteer wheat": "إزالة نباتات القمح العشوائية",
    "Seed certification programs": "برامج اعتماد التقاوي",
    "Soil drainage improvement": "تحسين صرف التربة",
    "Soil pH correction toward 5.5-6.5": "تعديل درجة حموضة التربة لتكون 5.5-6.5",
    "Stubble destruction post-harvest": "تدمير بقايا المحاصيل بعد الحصاد",
    "Stubble management (burning or burial)": "إدارة بقايا المحاصيل (الحرق أو الدفن)",
    "Synchronous sowing": "الزراعة المتزامنة",
    "Whitewash trunks": "طلاء الجذوع بالبياض (الجير)",
    "Wide row spacing": "زيادة المسافات بين الصفوف",

    # Biological Controls
    "Acidifying organic matter (pine bark mulch)": "المادة العضوية المحمضة (تغطية بقلف الصنوبر)",
    "Anastatus orientalis releases": "إطلاق طفيليات Anastatus orientalis",
    "Bacillus subtilis biofungicides": "المبيدات الفطرية الحيوية من بكتيريا Bacillus subtilis",
    "Balanced potassium nutrition": "التغذية البوتاسية المتوازنة",
    "Beauveria bassiana": "فطر البيوفاريا باسيانا (Beauveria bassiana)",
    "Bone meal incorporation": "دمج مسحوق العظام في التربة",
    "Certified disease-free seed": "استخدام بذور معتمدة خالية من الأمراض",
    "Compost with high-boron content (kelp)": "سماد عضوي غني بالبورون (أعشاب بحرية)",
    "Conserve mirid bug populations": "الحفاظ على مجتمعات بق الميريد النافع",
    "Crop rotation away from wheat residue": "الدورة الزراعية بعيداً عن مخلفات القمح",
    "Entomopathogenic nematodes": "النيماتودا الممرضة للحشرات",
    "Leguminous cover crops (Crotalaria)": "محاصيل التغطية البقولية (كروتالاريا)",
    "Pheromone traps": "المصائد الفرمونية",
    "Reduce broad-spectrum sprays": "تقليل رش المبيدات واسعة المدى لحماية المفترسات النافعة",
    "Resistant cultivars": "زراعة أصناف مقاومة",
    "Resistant cultivars (Misr 1, Sakha 95)": "أصناف مقاومة (مصر 1، سخا 95)",
    "Resistant cultivars (Sakha 101, 102)": "أصناف مقاومة (سخا 101، سخا 102)",
    "Resistant cultivars (Sr genes)": "أصناف مقاومة تحتوي على جينات Sr",
    "Trichoderma harzianum applications": "معاملة بفطر الترايكوديرما هارزيانوم",
    "Trichogramma releases (1-2 lakh/ha/week)": "إطلاق دبابير الترايكوجراما بمعدل 100-200 ألف/هكتار/أسبوعياً",

    # Chemical Controls
    "Ammonium sulfate": "كبريتات الأمونيوم",
    "Apply Bacillus thuringiensis (Bt) or pyrethroid sprays. Avoid contact due to stinging spines.": "رش بكتيريا Bacillus thuringiensis (Bt) أو المبيدات البيريثرويدية. تجنب الملامسة بسبب الأشواك اللادغة.",
    "Apply Bacillus thuringiensis (Bt) or spinosad. Handpick larvae if infestation is localized.": "رش بكتيريا Bacillus thuringiensis (Bt) أو سبينوساد. جمع اليرقات يدوياً إذا كانت الإصابة موضعية.",
    "Apply Beauveria bassiana spores or chemical insecticides in bait formulations.": "رش جراثيم Beauveria bassiana أو استخدام مبيدات كيميائية في صورة طعوم.",
    "Apply balanced citrus NPK fertilizer with chelated micronutrients (Zinc, Iron, Manganese).": "إضافة سماد NPK متوازن للموالح مع العناصر الصغرى المخلبية (زنك، حديد، منجنيز).",
    "Apply beneficial nematodes (Steinernema carpocapsae) or apply granular insecticides in late spring.": "استخدم النيماتودا النافعة (Steinernema carpocapsae) أو حبيبات المبيدات الحشرية في أواخر الربيع.",
    "Apply chlorothalonil or copper fungicides. Prune lower leaves to reduce soil splash.": "رش مبيد كلوروثالونيل أو مبيدات نحاسية. تقليم الأوراق السفلية للحد من ترطيش التربة.",
    "Apply foliar fungicides, manage crop residue, and rotate with non-host crops.": "رش المبيدات الفطرية على الأوراق، وإدارة بقايا المحصول، واتباع دورة زراعية مع محاصيل غير عائلة للمرض.",
    "Apply fungicides like strobilurins or triazoles if rust appears early. Plant resistant hybrids.": "رش مبيدات فطرية مثل الاستروبيلورين أو التريازول عند ظهور الصدأ مبكراً. زراعة الهجن المقاومة.",
    "Apply microbial control agents like NPV or Bt. Use pheromone traps to monitor adult flight.": "استخدم عوامل المكافحة الميكروبية مثل فيروس NPV أو بكتيريا Bt. استخدم المصائد الفرمونية لمراقبة طيران الحشرات البالغة.",
    "Apply potassium sulfate or muriate of potash. Ensure well-drained soil conditions.": "إضافة كبريتات البوتاسيوم أو كلوريد البوتاسيوم. التأكد من جودة الصرف بالتربة.",
    "Apply superphosphate or DAP fertilizer at root zone. Correct soil pH if highly acidic.": "إضافة سماد السوبر فوسفات أو DAP في منطقة الجذور. تعديل درجة حموضة التربة إذا كانت شديدة الحموضة.",
    "Apply zinc sulfate fertilizer to the soil or spray zinc chelates onto foliage.": "إضافة سماد كبريتات الزنك للتربة أو رش الزنك المخلبي على الأوراق.",
    "Avoid excess nitrogen. Apply tricyclazole or systemic fungicides at first signs.": "تجنب النيتروجين الزائد. رش الترايسيكلازول أو مبيدات فطرية جهازية عند أول بادرة للإصابة.",
    "Azoxystrobin": "أزوكسي ستروبين",
    "Bifenthrin (contact)": "بايفرين (بالملامسة)",
    "Buprofezin 25% SC": "بوبروفيزين 25% مركز قابل للانتشار",
    "Calcium nitrate foliar": "رش نترات الكالسيوم على الأوراق",
    "Carboxin seed treatment": "معالجة التقاوي بالكاربوكسين",
    "Cartap hydrochloride 4G": "كارتاب هيدروكلوريد 4G (محبب)",
    "Chlorantraniliprole 0.4G": "كلورانترانيليبرول 0.4G",
    "Chlorothalonil": "كلوروثالونيل",
    "Chlorpyrifos painting on trunk": "طلاء الجذع بالكلوربيريفوس",
    "Control green leafhoppers using insecticidal sprays, and plant resistant rice varieties.": "مكافحة نطاطات الأوراق الخضراء بالرش الحشري وزراعة أصناف الأرز المقاومة.",
    "Control silverleaf whitefly vector with insecticides, use yellow sticky traps, and protect seedlings.": "مكافحة الذبابة البيضاء الناقلة للفيروس بالمبيدات الحشرية، واستخدم المصائد الصفراء اللاصقة واحمي الشتلات.",
    "Control the Asian citrus psyllid vector, remove infected trees, and apply nutritional sprays.": "مكافحة حشرة بسيلا الموالح الآسيوية الناقلة للمرض، وإزالة الأشجار المصابة، ورش المغذيات الورقية.",
    "Cymoxanil + Famoxadone": "سيموكسانيل + فاموكسادون",
    "Dinotefuran (systemic)": "دينوتيفوران (جهازي)",
    "Fe-EDDHA chelate soil drench": "ري التربة بالحديد المخلبي Fe-EDDHA",
    "Ferrous sulfate foliar 0.5%": "رش كبريتات الحديدوز 0.5% على الأوراق",
    "Foliar borax 0.2% during flowering": "رش البوراكس 0.2% على الأوراق أثناء التزهير",
    "Gypsum soil amendment": "إضافة الجبس الزراعي لتحسين التربة",
    "Handpick with heavy gloves (do not touch bare skin), spray spinosad if populations are large.": "جمع يدوي بقفازات سميكة (لا تلمس الحشرات بالجلد المكشوف)، ورش مبيد سبينوساد إذا كانت الأعداد كبيرة.",
    "Imidacloprid trunk injection": "حقن الجذع بمادة إيميداكلوبريد",
    "Improve canopy microclimate to reduce moisture. Apply copper fungicides after harvest.": "تحسين المناخ الدقيق للمجموع الخضري لتقليل الرطوبة. رش مبيدات نحاسية بعد الحصاد.",
    "Inject systemic insecticides like imidacloprid into trunks, prune infested branches and burn them.": "حقن الجذوع بمبيدات جهازية مثل إيميداكلوبريد، وتقليم الأفرع المصابة وحرقها.",
    "Introduce beneficial predators, control weeds hosting the bugs, spray pyrethrins if necessary.": "إدخال المفترسات النافعة، ومكافحة الحشائش العائلة للبق، ورش البيرثرين عند الضرورة.",
    "Isoprothiolane": "إيسوبروثيولان",
    "Mancozeb + Metalaxyl": "مانكوزيب + ميتالاكسيل",
    "Mancozeb 75% WP": "مانكوزيب 75% مسحوق قابل للبلل",
    "No action needed. Ensure adequate nitrogen levels during growth stages.": "لا حاجة لاتخاذ إجراء. تأكد من مستويات النيتروجين الكافية خلال مراحل النمو.",
    "No action needed. Ensure consistent soil moisture to prevent fruit cracking.": "لا حاجة لاتخاذ إجراء. تأكد من رطوبة التربة المنتظمة لمنع تشقق الثمار.",
    "No action needed. Keep fields free of competing weeds.": "لا حاجة لاتخاذ إجراء. حافظ على الحقول خالية من الحشائش المنافسة.",
    "No action needed. Keep monitoring leaf color and maintain balanced irrigation.": "لا حاجة لاتخاذ إجراء. استمر في مراقبة لون الأوراق وحافظ على ري متوازن.",
    "No action needed. Maintain proper calcium levels to prevent blossom end rot.": "لا حاجة لاتخاذ إجراء. حافظ على مستويات الكالسيوم المناسبة لمنع تعفن الطرف الزهري.",
    "No action needed. Maintain proper pruning and seasonal fertilization.": "لا حاجة لاتخاذ إجراء. حافظ على التقليم المناسب والتسميد الموسمي.",
    "No action needed. Maintain proper water level in the paddy.": "لا حاجة لاتخاذ إجراء. حافظ على مستوى الماء المناسب في حقول الأرز.",
    "No treatment needed. Maintain optimal watering, weeding, and nutrient supply.": "لا حاجة للعلاج. حافظ على الري والتعشيب وتوفير العناصر الغذائية بشكل مثالي.",
    "Picoxystrobin": "بيكوكسي ستروبين",
    "Plant Bt-corn varieties, spray insecticides like chlorantraniliprole during egg hatch.": "زراعة أصناف الذرة المقاومة Bt، ورش مبيدات مثل كلورانترانيليبرول أثناء فقس البيض.",
    "Plant resistant cassava varieties and control whitefly vectors using neem oil or insecticidal soaps.": "زراعة أصناف الكسافا المقاومة ومكافحة الذبابة البيضاء الناقلة للمرض باستخدام زيت النيم أو الصابون الحشري.",
    "Plant resistant cultivars and apply triazole fungicides at the first detection of pustules.": "زراعة أصناف مقاومة ورش مبيدات التريازول عند أول ظهور لبثور الصدأ.",
    "Plant resistant cultivars, destroy infected cassava plants, and control the whitefly vector.": "زراعة أصناف مقاومة، وإعدام نباتات الكسافا المصابة، ومكافحة الذبابة البيضاء الناقلة للمرض.",
    "Propiconazole": "بروبيكونازول",
    "Propiconazole 25% EC": "بروبيكونازول 25% مركز قابل للاستحلاب",
    "Protect pruning wounds with sealants. Remove badly infected vines to avoid spreading.": "حماية جروح التقليم بمواد عازلة. إزالة كرمات العنب المصابة بشدة لتجنب انتشار المرض.",
    "Prune mummy berries and diseased canes, keep fruit off the ground, and apply fungicides early in spring.": "تقليم الثمار المحنطة والقصبات المريضة، وإبعاد الثمار عن الأرض، ورش المبيدات الفطرية في وقت مبكر من الربيع.",
    "Pymetrozine 50% WG": "bيمتروزين 50% حبيبات قابلة للانتشار",
    "Reduce crop density, clear weeds, and spray validamycin or hexaconazole.": "تقليل كثافة المحصول، وإزالة الحشائش، ورش فاليدامايسين أو هيكساكونازول.",
    "Release Trichogramma wasps, spray cartap hydrochloride or chlorantraniliprole.": "إطلاق دبابير الترايكوجراما، ورش كارتاب هيدروكلوريد أو كلورانترانيليبرول.",
    "Release natural predators like ladybugs, spray with neem oil, or apply strong water stream.": "إطلاق المفترسات الطبيعية مثل أبو العيد، أو الرش بزيت النيم، أو استخدام تيار ماء قوي.",
    "Scrap egg masses off trunks, use sticky bands around trees, apply dinotefuran or bifenthrin.": "كشط كتل البيض من الجذوع، واستخدام أحزمة لاصقة حول الأشجار، ورش دينوتيفوران أو بيفنثرين.",
    "Side-dress with urea or ammonium nitrate. Apply organic compost.": "إضافة سماد اليوريا أو نترات الأمونيوم كدفعات بجانب النبات. إضافة السماد العضوي.",
    "Solubor sprays": "رش سماد سوليوبور البورون",
    "Spray copper-based bactericides preventively, prune infected twigs, and wash tools thoroughly.": "رش مبيدات بكتيرية نحاسية وقائياً، وتقليم الأغصان المصابة، وغسل الأدوات جيداً.",
    "Spray with neem oil, sulfur-based fungicides, or biofungicides at weekly intervals.": "الرش بزيت النيم أو المبيدات الكبريتية أو الفطرية الحيوية على فترات أسبوعية.",
    "Tebuconazole + Trifloxystrobin": "تيبوكونازول + تريفلوكسي ستروبين",
    "Tebuconazole 250 g/L EC": "تيبوكونازول 250 جم/لتر مركز قابل للاستحلاب",
    "Tebuconazole seed dressing": "معاملة البذور بالتيبوكونازول",
    "Triadimefon 25% WP": "ترياديميفون 25% مسحوق قابل للبلل",
    "Tricyclazole 75% WP": "ترايسيكلازول 75% مسحوق قابل للبلل",
    "Urea 46% split applications": "إضافة اليوريا 46% على دفعات مجزأة",
    "Use certified clean propagation stems, practice strict sanitation, and control insect vectors.": "استخدام عقل إكثار معتمدة ونظيفة، وممارسة إجراءات تطهير صارمة، ومكافحة الحشرات الناقلة للمرض.",
    "Use certified pathogen-free seed, treat seeds with carboxin or tebuconazole before sowing.": "استخدام بذور معتمدة خالية من الأمراض، ومعالجة البذور بمبيد الكاربوكسين أو التيبوكونازول قبل البذر.",
    "Use copper sprays during dormancy and oxytetracycline during the growing season.": "رش النحاس خلال فترة السكون، والأوكسي تتراسايكلين خلال موسم النمو.",
    "Use disease-free planting materials, remove infected plants immediately, and practice crop rotation.": "استخدام مواد زراعة خالية من الأمراض، وإزالة النباتات المصابة فوراً، وممارسة الدورة الزراعية.",
    "Use insecticidal soaps, pyrethrins, or reflective mulches to deter adults.": "استخدام الصابون الحشري أو البيرثرينات أو المالتش العاكس لطرد الحشرات البالغة.",
}

def _translate_weather_summary(summary: str) -> str:
    if not summary:
        return ""
    seasons_ar = {"spring": "الربيع", "summer": "الصيف", "autumn": "الخريف", "winter": "الشتاء", "any": "أي موسم", "unknown": "غير معروف"}
    parts = [p.strip() for p in summary.split(",")]
    translated_parts = []
    for p in parts:
        if p.endswith("°C"):
            translated_parts.append(p.replace("°C", "°م"))
        elif p.endswith("% RH"):
            translated_parts.append(p.replace("RH", "رطوبة نسبية"))
        else:
            translated_parts.append(seasons_ar.get(p.lower(), p))
    return ", ".join(translated_parts)

def _translate_yield_rationale(text: str) -> str:
    if not text:
        return ""
    # Expected damage 25.0% vs ET 12.0%; loss $375/ha vs cost $70/ha (BCR=5.36); confidence 97% ≥ alert threshold 55%.
    match = re.match(r"Expected damage ([\d.]+)% vs ET ([\d.]+)%; loss \$([\d.,]+)/ha vs cost \$([\d.,]+)/ha \(BCR=([\d.]+)\); confidence ([\d.]+)%\s+([≥<])\s+alert threshold ([\d.]+)%\.", text)
    if match:
        dmg, et, loss, cost, bcr, conf, op, thresh = match.groups()
        op_ar = "أكبر من أو يساوي" if op == "≥" else "أقل من"
        return (
            f"الضرر المتوقع {dmg}% مقابل حد الضرر الاقتصادي (ET) {et}%؛ "
            f"الخسارة المتوقعة {loss} دولار/هكتار مقابل تكلفة المكافحة {cost} دولار/هكتار (نسبة العائد للتكلفة BCR={bcr})؛ "
            f"نسبة الثقة {conf}% {op_ar} عتبة التنبيه {thresh}%."
        )
    # Simple search & replace fallbacks
    text = text.replace("Expected damage", "الضرر المتوقع")
    text = text.replace("vs ET", "مقابل عتبة الضرر الاقتصادي")
    text = text.replace("loss", "الخسارة")
    text = text.replace("vs cost", "مقابل تكلفة")
    text = text.replace("confidence", "درجة الثقة")
    text = text.replace("alert threshold", "عتبة التنبيه")
    return text

def _translate_differential_bullet(bullet: str) -> str:
    if not bullet:
        return ""
    # CNN initially favored class (X%); siblings in dispute: class2, class3.
    match1 = re.match(r"CNN initially favored ([a-zA-Z_:]+___[a-zA-Z_:]+|[a-zA-Z_:]+)\s*\(([\d.]+%)\);\s*siblings in dispute:\s*(.+)\.", bullet)
    if match1:
        top_cls, conf, sibs = match1.groups()
        return f"فضل نموذج الرؤية (CNN) في البداية {top_cls} بنسبة ثقة {conf}؛ الحالات المتنافسة: {sibs}."
    
    # Weather snapshot: T=X°C, RH=Y%, season=Z.
    match2 = re.match(r"Weather snapshot:\s*T=([\d.]+)°C,\s*RH=([\d.]+)%,\s*season=(.+)\.", bullet)
    if match2:
        t, rh, season = match2.groups()
        seasons_ar = {"spring": "الربيع", "summer": "الصيف", "autumn": "الخريف", "winter": "الشتاء", "unknown": "غير معروف"}
        season_ar = seasons_ar.get(season.strip().lower(), season)
        return f"حالة الطقس الحالية: درجة الحرارة={t}°م، الرطوبة النسبيّة={rh}%، الموسم={season_ar}."
    
    # Blend weight α=X (lower α = more KG authority).
    match3 = re.match(r"Blend weight α=([\d.]+)\s*\(lower α = more KG authority\)\.", bullet)
    if match3:
        alpha = match3.group(1)
        return f"وزن الدمج α={alpha} (كلما قلّت α زادت صلاحية الرسم المعرفي KG)."
    
    # class_name: trigger window T=[X, Y], RH≥Z, season=[A, B] -> env fit W, final V.
    match4 = re.match(r"([a-zA-Z0-9_:]+): trigger window T=(.+), RH≥(.+), season=(.+)\s*->\s*env fit ([\d.]+),\s*final ([\d.]+)\.", bullet)
    if match4:
        cls, t_win, rh_win, season_win, env_fit, final_score = match4.groups()
        return f"{cls}: الظروف المحفزة (الحرارة={t_win}، الرطوبة≥{rh_win}، الموسم={season_win}) -> الملاءمة البيئية={env_fit}، النتيجة النهائية={final_score}."
        
    # Decision: re-ranked from X to Y -- environmental conditions favor the latter.
    match5 = re.match(r"Decision: re-ranked from (.+) to (.+)\s*--\s*environmental conditions favor the latter\.", bullet)
    if match5:
        from_cls, to_cls = match5.groups()
        return f"القرار: تم تغيير الترتيب من {from_cls} إلى {to_cls} -- الظروف البيئية تدعم الأخير."
        
    # Decision: X confirmed (CNN and KG agree).
    match6 = re.match(r"Decision: (.+)\s*confirmed\s*\(CNN\s*and\s*KG\s*agree\)\.", bullet)
    if match6:
        cls = match6.group(1)
        return f"القرار: تم تأكيد {cls} (اتفاق نموذج الرؤية والرسم المعرفي)."
        
    return bullet

def build_text_ar(p: ReportPayload) -> str:
    """Arabic narrative. Phrasing is intentionally Modern Standard Arabic
    (fasīḥ) so it's understandable in MENA broadly, with vocabulary that
    Egyptian agronomists will recognise."""
    label = p.label_ar or p.label_en
    lines = []
    lines.append(f"تم اكتشاف: {label} بثقة {p.confidence:.0%}.")
    lines.append(f"مسار الرسم المعرفي: {_kg_path_string(p.kg_path_en)}.")
    if p.pathogens:
        translated_pathogens = [AR_TRANSLATIONS.get(x, x) for x in p.pathogens]
        lines.append(f"المُسبب: {'، '.join(translated_pathogens)}.")
    if p.triggers:
        t = p.triggers
        parts = []
        if t.get("temp_c"):
            lo, hi = t["temp_c"]
            parts.append(f"درجة حرارة {lo}–{hi}°م")
        if t.get("humidity_pct_min") is not None and t.get("humidity_pct_min") > 0:
            parts.append(f"رطوبة ≥ {t['humidity_pct_min']}%")
        if t.get("season"):
            seasons_ar = {"spring": "الربيع", "summer": "الصيف",
                          "autumn": "الخريف", "winter": "الشتاء", "any": "أي موسم"}
            parts.append("الموسم " + "/".join(seasons_ar.get(s, s) for s in t["season"]))
        if parts:
            lines.append("المحفزات البيئية: " + "، ".join(parts) + ".")
    if p.weather_summary:
        lines.append(f"الظروف الحالية: {_translate_weather_summary(p.weather_summary)}")

    if p.damage_pct_15d > 0:
        primary_treatment = (p.chemical_controls or p.biological_controls or ["العلاج الموصى به"])[0]
        translated_treatment = AR_TRANSLATIONS.get(primary_treatment, primary_treatment)
        lines.append(
            f"السيناريو البديل: بدون {translated_treatment}، يُتوقع أن يُصاب المحصول "
            f"بأضرار تقارب {p.damage_pct_15d:.0f}% خلال 15 يومًا."
        )
    severity_ar = {"info": "للعلم", "watch": "مراقبة", "warning": "تحذير", "critical": "حرج"}
    if p.severity:
        lines.append(f"درجة الخطورة الاقتصادية: {severity_ar.get(p.severity, p.severity).upper()}. {_translate_yield_rationale(p.yield_rationale)}")
    if p.differential_explanation:
        lines.append("التشخيص التفريقي:")
        lines.extend(f"  • {_translate_differential_bullet(b)}" for b in p.differential_explanation)
    if p.biological_controls:
        translated_bio = [AR_TRANSLATIONS.get(x, x) for x in p.biological_controls]
        lines.append("المكافحة الحيوية: " + "؛ ".join(translated_bio) + ".")
    if p.chemical_controls:
        translated_chem = [AR_TRANSLATIONS.get(x, x) for x in p.chemical_controls]
        lines.append("المكافحة الكيميائية: " + "؛ ".join(translated_chem) + ".")
    if p.cultural_controls:
        translated_cult = [AR_TRANSLATIONS.get(x, x) for x in p.cultural_controls]
        lines.append("الممارسات الزراعية: " + "؛ ".join(translated_cult) + ".")
    if p.predators:
        translated_pred = [AR_TRANSLATIONS.get(x, x) for x in p.predators]
        lines.append("الأعداء الحيوية: " + "، ".join(translated_pred) + ".")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML (Jinja2)
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AgriXAI Diagnosis: {{ p.label_en }}</title>
<style>
  :root {
    --bg: #0f1419;
    --card: #1a2027;
    --ink: #e8edf2;
    --muted: #8b95a1;
    --accent: #4ade80;
    --warn: #fbbf24;
    --crit: #f87171;
    --info: #60a5fa;
    --border: #2a3540;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: var(--bg); color: var(--ink); line-height: 1.55;
  }
  .wrap { max-width: 1100px; margin: 0 auto; }
  header { display: flex; align-items: baseline; justify-content: space-between;
           border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 16px; }
  header h1 { margin: 0; font-size: 22px; font-weight: 600; }
  .subtle { color: var(--muted); font-size: 13px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .panel { background: var(--card); border: 1px solid var(--border); border-radius: 10px;
           padding: 16px; }
  .panel h2 { margin: 0 0 10px; font-size: 14px; text-transform: uppercase;
              letter-spacing: 0.5px; color: var(--muted); font-weight: 600; }
  .ar { direction: rtl; text-align: right; font-family: "Tahoma", "Arial", sans-serif; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 999px;
           font-size: 11px; font-weight: 700; text-transform: uppercase;
           letter-spacing: 0.5px; }
  .b-info { background: rgba(96,165,250,0.15); color: var(--info); }
  .b-watch { background: rgba(96,165,250,0.15); color: var(--info); }
  .b-warning { background: rgba(251,191,36,0.15); color: var(--warn); }
  .b-critical { background: rgba(248,113,113,0.15); color: var(--crit); }
  .meta { font-family: ui-monospace, "SF Mono", Menlo, monospace;
          font-size: 12px; color: var(--muted); margin: 4px 0; }
  .kg-path { font-family: ui-monospace, monospace; font-size: 13px;
             color: var(--accent); word-break: break-word; }
  ul { padding-left: 18px; margin: 6px 0; }
  .ar ul { padding-left: 0; padding-right: 18px; }
  pre { white-space: pre-wrap; margin: 0; font-family: inherit; }
  .full { grid-column: 1 / -1; }
  .row { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 8px; }
  .stat { font-size: 13px; }
  .stat strong { color: var(--ink); }
  .counterfactual { border-left: 3px solid var(--warn); padding-left: 12px; margin: 6px 0; }
  @media (max-width: 720px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>{{ p.label_en }} <span class="subtle">/ {{ p.label_ar }}</span></h1>
      <div class="subtle">AgriXAI Module 6 — Cognitive Layer Report</div>
    </div>
    <span class="badge b-{{ p.severity }}">{{ p.severity }}</span>
  </header>

  <div class="panel full">
    <div class="row">
      <div class="stat"><strong>Confidence:</strong> {{ "%.0f"|format(p.confidence*100) }}%</div>
      <div class="stat"><strong>Category:</strong> {{ p.category }}</div>
      <div class="stat"><strong>Class:</strong> <code>{{ p.class_name }}</code></div>
      {% if p.weather_summary %}<div class="stat"><strong>Weather:</strong> {{ p.weather_summary }}</div>{% endif %}
    </div>
    <div class="meta">KG path: <span class="kg-path">{{ kg_path_str }}</span></div>
    {% if p.damage_pct_15d %}
    <div class="counterfactual">
      <strong>Counterfactual (15-day horizon):</strong>
      Without intervention, expected damage ≈ <strong>{{ "%.0f"|format(p.damage_pct_15d) }}%</strong>.
    </div>
    {% endif %}
  </div>

  <div class="grid">
    <div class="panel">
      <h2>Reasoning (English)</h2>
      <pre>{{ text_en }}</pre>
    </div>
    <div class="panel ar">
      <h2>التحليل (العربية)</h2>
      <pre>{{ text_ar }}</pre>
    </div>
  </div>

  {% if p.differential_explanation %}
  <div class="panel full" style="margin-top:16px;">
    <h2>Differential Diagnosis Trace</h2>
    <ul>
      {% for line in p.differential_explanation %}
      <li>{{ line }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}

  <div class="grid" style="margin-top:16px;">
    <div class="panel full">
      <h2>Recommended Controls</h2>
      {% if p.biological_controls %}
      <strong>Biological:</strong>
      <ul>{% for c in p.biological_controls %}<li>{{ c }}</li>{% endfor %}</ul>
      {% endif %}
      {% if p.chemical_controls %}
      <strong>Chemical:</strong>
      <ul>{% for c in p.chemical_controls %}<li>{{ c }}</li>{% endfor %}</ul>
      {% endif %}
      {% if p.cultural_controls %}
      <strong>Cultural:</strong>
      <ul>{% for c in p.cultural_controls %}<li>{{ c }}</li>{% endfor %}</ul>
      {% endif %}
    </div>
  </div>

  <footer class="subtle" style="margin-top:24px; text-align:center;">
    Generated by AgriXAI Module 6 (Cognitive Layer). Predictions are advisory.
  </footer>
</div>
</body>
</html>
""".strip()


def build_html(p: ReportPayload, text_en: str, text_ar: str) -> str:
    if not _HAS_JINJA:
        # Fallback: a minimal HTML wrapper if Jinja2 isn't available.
        return (f"<html><body><h1>{p.label_en}</h1>"
                f"<pre>{text_en}</pre>"
                f"<pre dir='rtl'>{text_ar}</pre></body></html>")
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape(["html", "xml"]))
    tpl = env.from_string(HTML_TEMPLATE)
    return tpl.render(
        p=p,
        text_en=text_en,
        text_ar=text_ar,
        kg_path_str=_kg_path_string(p.kg_path_en),
    )


def render_full_report(p: ReportPayload) -> Dict[str, str]:
    """Convenience: build all three at once."""
    en = build_text_en(p)
    ar = build_text_ar(p)
    html = build_html(p, en, ar)
    return {"text_en": en, "text_ar": ar, "html": html}
