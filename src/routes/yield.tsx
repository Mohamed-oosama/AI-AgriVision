import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LineChart, Wand2, CheckCircle2, Leaf, Sun, FlaskConical, ChevronDown, Layers, Loader2, Thermometer, CloudSnow, Bug, Calendar, AlertTriangle } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from "recharts";
import { CropVisual } from "./soil";

// List of crops supported by Yield Prediction
const CROPS = [
  "Wheat", "Maize", "Rice", "Barley", "Cotton", "Seed Cotton",
  "Oranges", "Lemons", "Tangerines", "Mangoes", "Bananas", "Dates",
  "Apples", "Figs", "Grapes", "Strawberries", "Tomatoes", "Peppers (green)",
  "Potatoes", "Onions", "Eggplants", "Cucumbers", "Watermelons", "Cabbages", 
  "Carrots", "Okra", "Artichokes", "Broad Beans (dry)", "Lentils", "Chickpeas",
  "Groundnuts", "Sesame", "Sunflower", "Olives", "Sugar beet", "Sugar cane", "Sweet Potatoes"
];

// Arabic translations for crop names
const CROP_TRANSLATIONS_AR: Record<string, string> = {
  "Apples": "التفاح",
  "Artichokes": "الخرشوف",
  "Bananas": "الموز",
  "Barley": "الشعير",
  "Broad Beans (dry)": "الفول العريض (الجاف)",
  "Cabbages": "الكرنب",
  "Carrots": "الجزر",
  "Chickpeas": "الحمص",
  "Cucumbers": "الخيار",
  "Dates": "البلح",
  "Eggplants": "الباذنجان",
  "Figs": "التين",
  "Grapes": "العنب",
  "Groundnuts": "الفول السوداني",
  "Lemons": "الليمون",
  "Lentils": "العدس",
  "Maize": "الذرة",
  "Mangoes": "المانجو",
  "Okra": "البامية",
  "Olives": "الزيتون",
  "Onions": "البصل",
  "Oranges": "البرتقال",
  "Peppers (green)": "الفلفل الأخضر",
  "Potatoes": "البطاطس",
  "Rice": "الأرز",
  "Seed Cotton": "بذور القطن",
  "Sesame": "السمسم",
  "Strawberries": "الفراولة",
  "Sugar beet": "بنغر السكر",
  "Sugar cane": "قصب السكر",
  "Sunflower": "دوار الشمس",
  "Sweet Potatoes": "البطاطا الحلوة",
  "Tangerines": "اليوسفي",
  "Tomatoes": "الطماطم",
  "Watermelons": "البطاطس", // note: original translation had "البطاطس" for watermelon too, or we can keep it as original
  "Wheat": "القمح",
  "Cotton": "القطن"
};

export const Route = createFileRoute("/yield")({
  head: () => ({
    meta: [
      { title: "Egypt Crop Yield Explorer — AI AgriVision" },
      { name: "description", content: "Predict crop yield changes under climate change and fertilizer inputs in Egypt." }
    ]
  }),
  component: YieldPage
});

interface FeatureDetails {
  temp_change_c: number;
  summer_temp_anomaly: number;
  winter_temp_anomaly: number;
  nitrogen_t: number;
  phosphate_t: number;
  pesticides_t: number;
  arable_1000ha: number;
  precip_mm: number;
  summer_hot_days: number;
}

interface PredictionResponse {
  crop: string;
  year: number;
  baseline_yield: number;
  custom_yield: number;
  impact_pct: number;
  risk_en: string;
  risk_ar: string;
  color: string;
  baseline_features: FeatureDetails;
  custom_features: FeatureDetails;
  crops: string[];
  report_ar?: string;
  report_en?: string;
  report_html?: string;
}

// Validation bounds
const BOUNDS = {
  temp_change_c: { min: -2.0, max: 5.0, step: 0.1 },
  summer_temp_anomaly: { min: -3.0, max: 5.0, step: 0.1 },
  winter_temp_anomaly: { min: -3.0, max: 5.0, step: 0.1 },
  nitrogen_t: { min: 0, max: 1000, step: 1 },
  phosphate_t: { min: 0, max: 500, step: 1 },
  pesticides_t: { min: 0, max: 50, step: 0.1 },
  arable_1000feddan: { min: 1000, max: 25000, step: 10 },
  precip_mm: { min: 0, max: 500, step: 1 },
  summer_hot_days: { min: 0, max: 365, step: 1 }
};

interface YieldInputBlockProps {
  label: string;
  fieldKey: keyof typeof BOUNDS;
  value: string;
  onChange: (val: string) => void;
  baseVal: number;
  unit: string;
  icon?: React.ReactNode;
}

// Sub-component for individual slider + input block
const YieldInputBlock = ({
  label,
  fieldKey,
  value,
  onChange,
  baseVal,
  unit,
  icon
}: YieldInputBlockProps) => {
  const { lang } = useI18n();
  const bounds = BOUNDS[fieldKey];
  const isAuto = value.toLowerCase().trim() === "auto";

  const [error, setError] = useState("");

  const validate = (val: string) => {
    if (val.toLowerCase().trim() === "auto" || val.trim() === "") {
      setError("");
      return true;
    }
    const num = parseFloat(val);
    if (isNaN(num)) {
      setError(lang === "ar" ? "يجب أن يكون رقماً أو Auto" : "Must be a number or Auto");
      return false;
    }
    if (num < bounds.min || num > bounds.max) {
      setError(lang === "ar" 
        ? `يجب أن يكون بين ${bounds.min.toLocaleString()} و ${bounds.max.toLocaleString()}` 
        : `Must be between ${bounds.min.toLocaleString()} and ${bounds.max.toLocaleString()}`
      );
      return false;
    }
    setError("");
    return true;
  };

  const handleTextChange = (txt: string) => {
    onChange(txt);
    validate(txt);
  };

  const handleSliderChange = (num: number) => {
    onChange(num.toString());
    setError("");
  };

  const toggleAuto = () => {
    if (isAuto) {
      onChange(baseVal.toFixed(fieldKey.includes("temp") ? 2 : 0));
      setError("");
    } else {
      onChange("Auto");
      setError("");
    }
  };

  const sliderVal = isAuto ? baseVal : (parseFloat(value) || baseVal);

  return (
    <div className="flex flex-col gap-2 p-4 rounded-2xl bg-white/20 dark:bg-zinc-950/20 border border-border/40 backdrop-blur shadow-sm hover:border-border/60 transition-all">
      <div className="flex items-center justify-between w-full">
        {/* Left side: text input + Auto button */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            disabled={isAuto}
            value={value}
            onChange={(e) => handleTextChange(e.target.value)}
            className={`w-24 rounded-xl border px-2.5 py-1.5 text-xs text-center font-bold text-foreground bg-white/60 dark:bg-zinc-900/60 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 ${
              error ? "border-rose-500 focus:ring-rose-500/50" : "border-border/60"
            } disabled:opacity-60 disabled:cursor-not-allowed`}
          />
          <button
            onClick={toggleAuto}
            className={`px-2 py-1.5 rounded-lg text-[10px] font-bold cursor-pointer transition-all ${
              isAuto
                ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 shadow-soft"
                : "bg-zinc-500/15 text-zinc-500 border border-zinc-500/20"
            }`}
          >
            {isAuto ? (lang === "ar" ? "تلقائي" : "Auto") : (lang === "ar" ? "مخصص" : "Custom")}
          </button>
        </div>

        {/* Right side: Icon + Label */}
        <div className="flex items-center gap-2 text-foreground font-semibold text-xs">
          <span>{label}</span>
          {icon}
        </div>
      </div>

      {/* Slider running underneath */}
      <input
        type="range"
        disabled={isAuto}
        min={bounds.min}
        max={bounds.max}
        step={bounds.step}
        value={sliderVal}
        onChange={(e) => handleSliderChange(Number(e.target.value))}
        className="w-full accent-emerald-500 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed mt-1"
      />

      {/* Helper Range details */}
      <div className="flex justify-between text-[9px] text-muted-foreground">
        <span>{bounds.min.toLocaleString()} {unit}</span>
        <span>{lang === "ar" ? "الافتراضي:" : "Default:"} {baseVal.toLocaleString()} {unit}</span>
        <span>{bounds.max.toLocaleString()} {unit}</span>
      </div>

      {/* Error message */}
      {error && (
        <span className="text-[10px] text-rose-500 font-bold block mt-1">{error}</span>
      )}
    </div>
  );
};

function YieldPage() {
  const { t, lang } = useI18n();
  const [crop, setCrop] = useState("Wheat");
  const [year, setYear] = useState(2026);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<PredictionResponse | null>(null);

  // Form Inputs (absolute values)
  const [tempChange, setTempChange] = useState("Auto");
  const [summerTemp, setSummerTemp] = useState("Auto");
  const [winterTemp, setWinterTemp] = useState("Auto");
  const [nitrogen, setNitrogen] = useState("Auto");
  const [phosphate, setPhosphate] = useState("Auto");
  const [pesticides, setPesticides] = useState("Auto");
  const [arable, setArable] = useState("Auto");
  const [precip, setPrecip] = useState("Auto");
  const [summerHotDays, setSummerHotDays] = useState("Auto");

  const fetchPredictions = async () => {
    setLoading(true);
    try {
      const arableVal = arable.toLowerCase().trim() === "auto" ? "Auto" : (parseFloat(arable) * 0.42).toString();
      const arable_kfed = arable.toLowerCase().trim() === "auto" ? 6445 : parseFloat(arable);

      const payload = {
        crop,
        year,
        inputs: {
          temp_change_c: tempChange,
          summer_temp_anomaly: summerTemp,
          winter_temp_anomaly: winterTemp,
          nitrogen_t: nitrogen.toLowerCase().trim() === "auto" ? "Auto" : (parseFloat(nitrogen) * arable_kfed).toString(),
          phosphate_t: phosphate.toLowerCase().trim() === "auto" ? "Auto" : (parseFloat(phosphate) * arable_kfed).toString(),
          pesticides_t: pesticides.toLowerCase().trim() === "auto" ? "Auto" : (parseFloat(pesticides) * arable_kfed).toString(),
          arable_1000ha: arableVal,
          precip_mm: precip,
          summer_hot_days: summerHotDays
        }
      };

      const response = await fetch("/api/yield/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (data.error) {
        console.error("API error:", data.error);
      } else {
        // Convert to Feddan values
        const toFeddan = (ha: number) => ha / 0.42;
        const toKgFeddan = (kgHa: number) => kgHa * 0.42;
        
        data.baseline_yield = toKgFeddan(data.baseline_yield);
        data.custom_yield = toKgFeddan(data.custom_yield);
        
        const arable_base = toFeddan(data.baseline_features.arable_1000ha);
        const arable_cust = toFeddan(data.custom_features.arable_1000ha);
        
        data.baseline_features.arable_1000ha = arable_base;
        data.custom_features.arable_1000ha = arable_cust;

        data.baseline_features.nitrogen_t = data.baseline_features.nitrogen_t / arable_base;
        data.custom_features.nitrogen_t = data.custom_features.nitrogen_t / arable_cust;
        
        data.baseline_features.phosphate_t = data.baseline_features.phosphate_t / arable_base;
        data.custom_features.phosphate_t = data.custom_features.phosphate_t / arable_cust;

        data.baseline_features.pesticides_t = data.baseline_features.pesticides_t / arable_base;
        data.custom_features.pesticides_t = data.custom_features.pesticides_t / arable_cust;

        setResults(data);
      }
    } catch (err) {
      console.error("Failed to fetch predictions:", err);
    } finally {
      setLoading(false);
    }
  };

  // Run on initial mount & whenever crop or year changes
  useEffect(() => {
    fetchPredictions();
  }, [crop, year]);

  // Format yield numbers
  const formatYield = (val: number) => {
    return val.toLocaleString(lang === "ar" ? "ar-EG" : "en-US", {
      maximumFractionDigits: 1
    });
  };

  const getCropName = (cropKey: string) => {
    return lang === "ar" ? (CROP_TRANSLATIONS_AR[cropKey] || cropKey) : cropKey;
  };

  // Chart data comparing Baseline vs Custom Yield
  const chartData = results ? [
    {
      name: lang === "ar" ? "خط الأساس (الافتراضي)" : "Baseline (Default)",
      Yield: results.baseline_yield,
      color: "#3b82f6"
    },
    {
      name: lang === "ar" ? "المخصص (المدخلات الحالية)" : "Custom (Your Inputs)",
      Yield: results.custom_yield,
      color: results.impact_pct >= 0 ? "#10b981" : "#f43f5e"
    }
  ] : [];

  // Features mapping for the comparison table
  const getFeatureList = () => {
    if (!results) return [];
    
    const baseF = results.baseline_features;
    const custF = results.custom_features;

    const u_t = lang === "ar" ? "كجم/فدان" : "kg/fed";
    const u_kha = lang === "ar" ? "ألف فدان" : "k feddan";
    const u_mm = lang === "ar" ? "مم" : "mm";
    const u_days = lang === "ar" ? "يوم" : "days";

    return [
      {
        label: t("yield.tempChange"),
        base: `${baseF.temp_change_c.toFixed(2)} °C`,
        cust: `${custF.temp_change_c.toFixed(2)} °C`,
        isChanged: baseF.temp_change_c !== custF.temp_change_c
      },
      {
        label: t("yield.summerTemp"),
        base: `${baseF.summer_temp_anomaly.toFixed(2)} °C`,
        cust: `${custF.summer_temp_anomaly.toFixed(2)} °C`,
        isChanged: baseF.summer_temp_anomaly !== custF.summer_temp_anomaly
      },
      {
        label: t("yield.winterTemp"),
        base: `${baseF.winter_temp_anomaly.toFixed(2)} °C`,
        cust: `${custF.winter_temp_anomaly.toFixed(2)} °C`,
        isChanged: baseF.winter_temp_anomaly !== custF.winter_temp_anomaly
      },
      {
        label: t("yield.nitrogen"),
        base: `${formatYield(baseF.nitrogen_t)} ${u_t}`,
        cust: `${formatYield(custF.nitrogen_t)} ${u_t}`,
        isChanged: baseF.nitrogen_t !== custF.nitrogen_t
      },
      {
        label: t("yield.phosphate"),
        base: `${formatYield(baseF.phosphate_t)} ${u_t}`,
        cust: `${formatYield(custF.phosphate_t)} ${u_t}`,
        isChanged: baseF.phosphate_t !== custF.phosphate_t
      },
      {
        label: t("yield.pesticides"),
        base: `${formatYield(baseF.pesticides_t)} ${u_t}`,
        cust: `${formatYield(custF.pesticides_t)} ${u_t}`,
        isChanged: baseF.pesticides_t !== custF.pesticides_t
      },
      {
        label: t("yield.arable"),
        base: `${formatYield(baseF.arable_1000ha)} ${u_kha}`,
        cust: `${formatYield(custF.arable_1000ha)} ${u_kha}`,
        isChanged: baseF.arable_1000ha !== custF.arable_1000ha
      },
      {
        label: lang === "ar" ? "هطول الأمطار" : "Precipitation",
        base: `${formatYield(baseF.precip_mm)} ${u_mm}`,
        cust: `${formatYield(custF.precip_mm)} ${u_mm}`,
        isChanged: baseF.precip_mm !== custF.precip_mm
      },
      {
        label: lang === "ar" ? "الأيام شديدة الحرارة صيفاً" : "Summer Hot Days",
        base: `${formatYield(baseF.summer_hot_days)} ${u_days}`,
        cust: `${formatYield(custF.summer_hot_days)} ${u_days}`,
        isChanged: baseF.summer_hot_days !== custF.summer_hot_days
      }
    ];
  };

  // Parent validation check
  const isValid = (key: string, val: string) => {
    if (val.toLowerCase().trim() === "auto" || val.trim() === "") return true;
    const num = parseFloat(val);
    if (isNaN(num)) return false;
    const bounds = BOUNDS[key as keyof typeof BOUNDS];
    return num >= bounds.min && num <= bounds.max;
  };

  const hasErrors = !(
    isValid("temp_change_c", tempChange) &&
    isValid("summer_temp_anomaly", summerTemp) &&
    isValid("winter_temp_anomaly", winterTemp) &&
    isValid("nitrogen_t", nitrogen) &&
    isValid("phosphate_t", phosphate) &&
    isValid("pesticides_t", pesticides) &&
    isValid("arable_1000feddan", arable) &&
    isValid("precip_mm", precip) &&
    isValid("summer_hot_days", summerHotDays)
  );

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 relative">
      {/* Background glow orb */}
      <div className="absolute top-0 right-1/4 w-96 h-96 -z-10 gradient-mesh opacity-20 blur-[100px] rounded-full" />

      {/* Header section with badge */}
      <div className="flex items-center gap-4 mb-8">
        <div className="size-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 shadow-glow flex items-center justify-center shrink-0 dark:bg-emerald-500/20">
          <LineChart className="size-7" />
        </div>
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight text-foreground">{t("yield.title")}</h1>
          <p className="text-muted-foreground text-sm mt-1">{t("yield.sub")}</p>
        </div>
      </div>

      {/* Inputs Main Form Card */}
      <div className="glass rounded-3xl p-6 sm:p-8 shadow-elegant border border-border/40 bg-white/40 dark:bg-black/20 backdrop-blur-md mb-8">
        
        {/* Core selectors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 pb-6 border-b border-border/20">
          {/* Target Crop */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <Leaf className="size-4 text-emerald-500" />
              {t("yield.crop")}
            </label>
            <div className="flex gap-3 items-center">
              <div className="relative flex-1">
                <select
                  value={crop}
                  onChange={(e) => setCrop(e.target.value)}
                  className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all cursor-pointer appearance-none text-foreground pr-10"
                >
                  {CROPS.map((c) => (
                    <option key={c} value={c}>
                      {getCropName(c)}
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                  <ChevronDown className="size-4" />
                </div>
              </div>
              <div className="size-[46px] flex items-center justify-center rounded-2xl bg-white/40 dark:bg-zinc-900/40 border border-border/40 shrink-0 shadow-soft">
                <CropVisual crop={crop === "Cotton" || crop === "Seed Cotton" ? "Cotton" : crop} className="size-8" />
              </div>
            </div>
          </div>

          {/* Target Year */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <Calendar className="size-4 text-amber-500" />
              {t("yield.year")}
            </label>
            <div className="relative">
              <select
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all cursor-pointer appearance-none pr-10 text-foreground"
              >
                {Array.from({ length: 25 }, (_, i) => 2026 + i).map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                <ChevronDown className="size-4" />
              </div>
            </div>
          </div>
        </div>

        {/* Inputs Sliders Grid */}
        {results?.baseline_features ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            
            {/* Temperature Change */}
            <YieldInputBlock
              label={t("yield.tempChange")}
              fieldKey="temp_change_c"
              value={tempChange}
              onChange={setTempChange}
              baseVal={results.baseline_features.temp_change_c}
              unit="°C"
              icon={<Thermometer className="size-4 text-amber-500" />}
            />

            {/* Summer Temp Anomaly */}
            <YieldInputBlock
              label={t("yield.summerTemp")}
              fieldKey="summer_temp_anomaly"
              value={summerTemp}
              onChange={setSummerTemp}
              baseVal={results.baseline_features.summer_temp_anomaly}
              unit="°C"
              icon={<Sun className="size-4 text-amber-500" />}
            />

            {/* Winter Temp Anomaly */}
            <YieldInputBlock
              label={t("yield.winterTemp")}
              fieldKey="winter_temp_anomaly"
              value={winterTemp}
              onChange={setWinterTemp}
              baseVal={results.baseline_features.winter_temp_anomaly}
              unit="°C"
              icon={<CloudSnow className="size-4 text-blue-400" />}
            />

            {/* Nitrogen */}
            <YieldInputBlock
              label={lang === "ar" ? "النيتروجين المستخدم" : "Nitrogen Used"}
              fieldKey="nitrogen_t"
              value={nitrogen}
              onChange={setNitrogen}
              baseVal={results.baseline_features.nitrogen_t}
              unit="kg/fed"
              icon={<span className="size-5 rounded bg-emerald-500 text-white font-extrabold text-[10px] flex items-center justify-center shrink-0 shadow-soft">N</span>}
            />

            {/* Phosphate */}
            <YieldInputBlock
              label={lang === "ar" ? "الفوسفات المستخدم" : "Phosphate Used"}
              fieldKey="phosphate_t"
              value={phosphate}
              onChange={setPhosphate}
              baseVal={results.baseline_features.phosphate_t}
              unit="kg/fed"
              icon={<span className="size-5 rounded bg-amber-500 text-white font-extrabold text-[10px] flex items-center justify-center shrink-0 shadow-soft">P</span>}
            />

            {/* Pesticides */}
            <YieldInputBlock
              label={lang === "ar" ? "المبيدات المستخدمة" : "Pesticides Used"}
              fieldKey="pesticides_t"
              value={pesticides}
              onChange={setPesticides}
              baseVal={results.baseline_features.pesticides_t}
              unit="kg/fed"
              icon={<Bug className="size-4 text-emerald-500" />}
            />

            {/* Arable Land */}
            <YieldInputBlock
              label={lang === "ar" ? "المساحة الزراعية" : "Arable Land"}
              fieldKey="arable_1000feddan"
              value={arable}
              onChange={setArable}
              baseVal={results.baseline_features.arable_1000ha}
              unit="k feddan"
              icon={<Layers className="size-4 text-emerald-500" />}
            />

            {/* Precip */}
            <YieldInputBlock
              label={lang === "ar" ? "هطول الأمطار" : "Precipitation"}
              fieldKey="precip_mm"
              value={precip}
              onChange={setPrecip}
              baseVal={results.baseline_features.precip_mm}
              unit="mm"
              icon={<CloudSnow className="size-4 text-blue-400" />}
            />

            {/* Summer Hot Days */}
            <YieldInputBlock
              label={lang === "ar" ? "الأيام شديدة الحرارة صيفاً" : "Summer Hot Days"}
              fieldKey="summer_hot_days"
              value={summerHotDays}
              onChange={setSummerHotDays}
              baseVal={results.baseline_features.summer_hot_days}
              unit="days"
              icon={<Sun className="size-4 text-rose-500" />}
            />

            {/* Action Button */}
            <div className="flex items-end">
              <button
                onClick={fetchPredictions}
                disabled={loading || hasErrors}
                className="w-full rounded-2xl bg-emerald-500 hover:bg-emerald-600 active:scale-95 text-white font-bold h-12 flex items-center justify-center gap-2 shadow-glow hover:shadow-elegant cursor-pointer transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="size-5 animate-spin" />
                    {t("yield.loading")}
                  </>
                ) : (
                  <>
                    <Wand2 className="size-5" />
                    {t("yield.simulate")}
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse mt-4">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="flex flex-col gap-3 p-4 rounded-2xl bg-white/40 dark:bg-zinc-900/40 border border-border/20 h-[104px]">
                <div className="flex justify-between w-full">
                  <div className="w-20 h-7 bg-white/60 dark:bg-zinc-800/60 rounded-xl" />
                  <div className="w-24 h-4 bg-white/60 dark:bg-zinc-800/60 rounded-md" />
                </div>
                <div className="w-full h-1.5 bg-emerald-500/20 rounded-full mt-3" />
                <div className="flex justify-between w-full mt-1">
                  <div className="w-10 h-2 bg-white/40 dark:bg-zinc-800/40 rounded-full" />
                  <div className="w-10 h-2 bg-white/40 dark:bg-zinc-800/40 rounded-full" />
                  <div className="w-10 h-2 bg-white/40 dark:bg-zinc-800/40 rounded-full" />
                </div>
              </div>
            ))}
            <div className="flex items-end">
              <div className="w-full h-12 rounded-2xl bg-emerald-500/30" />
            </div>
          </div>
        )}
      </div>

      {/* Results Section */}
      <AnimatePresence mode="wait">
        {results && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className={`grid grid-cols-1 lg:grid-cols-5 gap-8 transition-opacity duration-300 ${loading ? "opacity-50 pointer-events-none" : "opacity-100"}`}
          >
            {/* Direct Output Cards & Bar Chart (Left 3 columns) */}
            <div className="lg:col-span-3 space-y-6">
              <h2 className="text-xl font-bold font-display text-foreground flex items-center gap-2">
                <CheckCircle2 className="size-5 text-emerald-500" />
                {t("yield.results")}
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Baseline Card */}
                <div className="glass rounded-2xl p-5 border border-border/40 bg-white/20 dark:bg-zinc-950/20 shadow-sm flex flex-col justify-between">
                  <div>
                    <span className="text-muted-foreground text-[10px] font-bold uppercase tracking-wider block">
                      {t("yield.baseline")}
                    </span>
                    <span className="text-2xl font-extrabold text-foreground font-display mt-1 block">
                      {formatYield(results.baseline_yield)} <span className="text-xs font-normal text-muted-foreground">{lang === "ar" ? "كجم/فدان" : "kg/feddan"}</span>
                    </span>
                  </div>
                  <span className="text-[10px] text-muted-foreground mt-3 block">
                    {lang === "ar" ? "تنبؤ النموذج بظروف المناخ الافتراضية" : "Standard projection using default values"}
                  </span>
                </div>

                {/* Custom Card */}
                <div className="glass rounded-2xl p-5 border border-border/40 bg-emerald-500/5 dark:bg-emerald-950/10 shadow-sm flex flex-col justify-between">
                  <div>
                    <span className="text-muted-foreground text-[10px] font-bold uppercase tracking-wider block">
                      {t("yield.custom")}
                    </span>
                    <span className="text-2xl font-extrabold text-foreground font-display mt-1 block">
                      {formatYield(results.custom_yield)} <span className="text-xs font-normal text-muted-foreground">{lang === "ar" ? "كجم/فدان" : "kg/feddan"}</span>
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs">
                    <span className="text-[10px] text-muted-foreground">
                      {lang === "ar" ? "خطورة التغيير:" : "Risk status:"}
                    </span>
                    <span
                      className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                        results.color === "green"
                          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                          : results.color === "yellow"
                          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                      }`}
                    >
                      {lang === "ar" ? results.risk_ar : results.risk_en}
                    </span>
                  </div>
                </div>
              </div>

              {/* Graphical Yield Comparison Bar Chart */}
              <div className="glass rounded-3xl p-6 border border-border/40 bg-white/40 dark:bg-black/20 shadow-elegant">
                <h3 className="text-sm font-bold text-foreground mb-4">
                  {lang === "ar" ? "مقارنة بيانية للإنتاجية المتوقعة" : "Visual Yield Output Comparison"}
                </h3>
                <div className="h-[280px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                      <Tooltip
                        formatter={(value: number) => [formatYield(value), "Yield"]}
                        contentStyle={{
                          backgroundColor: "rgba(16, 185, 129, 0.95)",
                          borderColor: "rgba(255, 255, 255, 0.2)",
                          borderRadius: "12px",
                          color: "#ffffff",
                          boxShadow: "0 4px 12px rgba(16, 185, 129, 0.3)"
                        }}
                      />
                      <Bar dataKey="Yield" radius={[8, 8, 0, 0]} maxBarSize={60}>
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                {results.impact_pct !== 0 && (
                  <p className="text-xs text-center text-muted-foreground mt-4 flex items-center justify-center gap-1.5">
                    <AlertTriangle className="size-3.5 text-amber-500 shrink-0" />
                    {lang === "ar" ? (
                      <>
                        التعديل المخصص يؤدي إلى تغير قدره{" "}
                        <span className={`font-bold ${results.impact_pct >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                          {results.impact_pct >= 0 ? "+" : ""}
                          {results.impact_pct.toFixed(2)}%
                        </span>{" "}
                        في إنتاجية {getCropName(crop)} لعام {year}.
                      </>
                    ) : (
                      <>
                        Your inputs result in a{" "}
                        <span className={`font-bold ${results.impact_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {results.impact_pct >= 0 ? "+" : ""}
                          {results.impact_pct.toFixed(2)}%
                        </span>{" "}
                        change in expected {crop} yield for {year}.
                      </>
                    )}
                  </p>
                )}
              </div>
            </div>

            {/* Variable Comparison Table (Right 2 columns) */}
            <div className="lg:col-span-2 space-y-6">
              <h2 className="text-xl font-bold font-display text-foreground flex items-center gap-2">
                <FlaskConical className="size-5 text-emerald-500" />
                {lang === "ar" ? "تفاصيل قيم المدخلات" : "Input Variable Details"}
              </h2>

              <div className="glass rounded-3xl border border-border/40 overflow-hidden bg-white/40 dark:bg-black/35 backdrop-blur shadow-elegant">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-border/40 bg-white/20 dark:bg-zinc-900/40 text-muted-foreground font-semibold">
                      <th className="px-4 py-3.5">{lang === "ar" ? "المتغير" : "Variable"}</th>
                      <th className="px-4 py-3.5 text-center">{lang === "ar" ? "الافتراضي" : "Default"}</th>
                      <th className="px-4 py-3.5 text-center">{lang === "ar" ? "المدخل المخصص" : "Your Input"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getFeatureList().map((item, idx) => (
                      <tr
                        key={idx}
                        className={`border-b border-border/20 transition-colors ${
                          item.isChanged
                            ? "bg-amber-500/5 text-amber-600 dark:text-amber-400 font-medium"
                            : "text-foreground hover:bg-white/10 dark:hover:bg-zinc-900/10"
                        }`}
                      >
                        <td className="px-4 py-3">{item.label}</td>
                        <td className="px-4 py-3 text-center text-muted-foreground">{item.base}</td>
                        <td className="px-4 py-3 text-center font-bold">
                          {item.isChanged ? (
                            <span className="flex items-center justify-center gap-1">
                              {item.cust}
                            </span>
                          ) : (
                            <span className="text-muted-foreground font-normal">Auto</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Generated Report Section */}
            {results.report_html && (
              <div className="lg:col-span-5 mt-2 glass rounded-3xl overflow-hidden bg-white/40 dark:bg-black/20 shadow-elegant p-0">
                <iframe 
                  srcDoc={results.report_html} 
                  className="w-full min-h-[500px] border-none rounded-3xl"
                  title="Yield Prediction Report"
                />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
