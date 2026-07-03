import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, Info, AlertTriangle, CheckCircle, BarChart3, Wind, Sun, Droplets, Thermometer, ChevronDown, Loader2, RefreshCw, Layers } from "lucide-react";
import { useI18n } from "@/lib/i18n";

// Egyptian Protected Areas mapping matching Python
const EGYPTIAN_PROTECTED_AREAS = [
  { id: 0, name_ar: "محمية أشتوم الجميل", name_en: "Ashtum El-Gamil Protected Area" },
  { id: 1, name_ar: "محمية البرلس", name_en: "Lake Burullus Protected Area" },
  { id: 2, name_ar: "محمية الجزر الشمالية للبحر الأحمر", name_en: "Red Sea Northern Islands Protected Area" },
  { id: 3, name_ar: "محمية الجلف الكبير", name_en: "Gilf Kebir Protected Area" },
  { id: 4, name_ar: "محمية الدبابية", name_en: "El-Dababya Protected Area" },
  { id: 5, name_ar: "محمية الزرانيق", name_en: "Zaranik Protected Area" },
  { id: 6, name_ar: "محمية الصحراء البيضاء", name_en: "White Desert Protected Area" },
  { id: 7, name_ar: "محمية العميد", name_en: "El-Omayed Protected Area" },
  { id: 8, name_ar: "محمية الغابة المتحجرة", name_en: "Petrified Forest Protected Area" },
  { id: 9, name_ar: "محمية الواحات البحرية – الجزء الشرقي", name_en: "Bahariya Oasis - Eastern Part" },
  { id: 10, name_ar: "محمية الواحات البحرية – الجزء الغربي", name_en: "Bahariya Oasis - Western Part" },
  { id: 11, name_ar: "محمية الواحات البحرية – الجزء الوسطي", name_en: "Bahariya Oasis - Central Part" },
  { id: 12, name_ar: "محمية رأس محمد", name_en: "Ras Mohammad Protected Area" },
  { id: 13, name_ar: "محمية سالوجا وغزال", name_en: "Saluga and Ghazal Protected Area" },
  { id: 14, name_ar: "محمية سانت كاثرين", name_en: "Saint Catherine Protected Area" },
  { id: 15, name_ar: "محمية سيوة – القطاع الأوسط الجنوبي", name_en: "Siwa Oasis - South Central Sector" },
  { id: 16, name_ar: "محمية سيوة – القطاع الغربي", name_en: "Siwa Oasis - Western Sector" },
  { id: 17, name_ar: "محمية سيوة – القطاع الشرقي", name_en: "Siwa Oasis - Eastern Sector" },
  { id: 18, name_ar: "محمية طابا", name_en: "Taba Protected Area" },
  { id: 19, name_ar: "محمية علبة", name_en: "Gebel Elba Protected Area" },
  { id: 20, name_ar: "محمية قارون", name_en: "Lake Qarun Protected Area" },
  { id: 21, name_ar: "محمية قبة الحسنة", name_en: "Hassana Dome Protected Area" },
  { id: 22, name_ar: "محمية كهف سنور", name_en: "Sannur Cave Protected Area" },
  { id: 23, name_ar: "محمية نبق", name_en: "Nabq Protected Area" },
  { id: 24, name_ar: "محمية نيزك جبل كامل", name_en: "Gebel Kamil Crater Protected Area" },
  { id: 25, name_ar: "محمية وادي الأسيوطي", name_en: "Wadi El-Assiouti Protected Area" },
  { id: 26, name_ar: "محمية وادي الجمال", name_en: "Wadi El-Gemal Protected Area" },
  { id: 27, name_ar: "محمية وادي الريان", name_en: "Wadi El-Rayan Protected Area" },
  { id: 28, name_ar: "محمية وادي العلاقي", name_en: "Wadi El-Allaqi Protected Area" },
  { id: 29, name_ar: "محمية وادي دجلة", name_en: "Wadi Degla Protected Area" },
  { id: 30, name_ar: "محمية أبو جالوم", name_en: "Abu Galum Protected Area" },
];

export const Route = createFileRoute("/ews")({
  head: () => ({
    meta: [
      { title: "EWS Protected Areas — AgriMind.AI" },
      { name: "description", content: "Early Warning System for ecological stress in Egyptian Protected Areas." }
    ]
  }),
  component: EWSComponent,
});

interface EWSInputs {
  area_id: number;
  ndvi_mean: number;
  evi: number;
  savi: number;
  vegetation_percent: number;
  temperature_2m_c: number; // User input in Celsius
  total_precipitation_sum: number;
  volumetric_soil_water_layer_1: number;
  volumetric_soil_water_layer_2: number;
  volumetric_soil_water_layer_3: number;
  volumetric_soil_water_layer_4: number;
  surface_solar_radiation_downwards_sum: number;
  u_component_of_wind_10m: number;
  v_component_of_wind_10m: number;
  day_count: number;
}

interface EWSResult {
  status: string;
  error?: string;
  area_name: string;
  area_id: number;
  mode: string;
  stress_predicted: boolean;
  stress_probability: number;
  risk_level: "Low" | "Moderate" | "High" | "Critical";
  risk_score: number;
  action: string;
  action_ar: string;
  confidence: number;
  human_review: boolean;
  fusion_branch: string;
  individual_probs: { xgb: number; rf: number; lr: number };
  reasoning: string[];
  reasoning_ar: string[];
  shap_explanation?: {
    base_value: number;
    feature_impacts: Array<{ feature: string; shap_value: number; feature_value: number }>;
  };
  inference_ms: number;
  model_version: string;
  report_en?: string;
  report_ar?: string;
  report_html?: string;
}

function EWSComponent() {
  const { t, lang } = useI18n();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EWSResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [inputs, setInputs] = useState<EWSInputs>({
    area_id: 27, // Wadi El-Rayan as default
    ndvi_mean: 0.28,
    evi: 0.18,
    savi: 0.23,
    vegetation_percent: 32.5,
    temperature_2m_c: 32.0, // 32 degrees Celsius
    total_precipitation_sum: 0.2,
    volumetric_soil_water_layer_1: 0.08,
    volumetric_soil_water_layer_2: 0.09,
    volumetric_soil_water_layer_3: 0.11,
    volumetric_soil_water_layer_4: 0.14,
    surface_solar_radiation_downwards_sum: 22.0,
    u_component_of_wind_10m: 1.2,
    v_component_of_wind_10m: 0.8,
    day_count: 150,
  });

  const handleInputChange = (key: keyof EWSInputs, value: number) => {
    setInputs(prev => ({ ...prev, [key]: value }));
  };

  const runSimulation = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    // Removed setResult(null) to keep previous results visible during auto-refresh

    try {
      // Convert Celsius to Kelvin before sending to EWS API
      const requestData = {
        ...inputs,
        temperature_2m: inputs.temperature_2m_c + 273.15,
      };

      const response = await fetch("/api/ews/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`);
      }

      const data = await response.json();
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong running EWS simulation.");
    } finally {
      setLoading(false);
    }
  };

  // Auto-run simulation when inputs change (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      runSimulation();
    }, 400);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputs]);

  // Preset scenarios to help user test the dashboard
  const applyPreset = (presetType: "healthy" | "critical" | "moderate") => {
    if (presetType === "healthy") {
      setInputs({
        area_id: 27,
        ndvi_mean: 0.35,
        evi: 0.24,
        savi: 0.29,
        vegetation_percent: 45.0,
        temperature_2m_c: 25.0,
        total_precipitation_sum: 2.5,
        volumetric_soil_water_layer_1: 0.18,
        volumetric_soil_water_layer_2: 0.19,
        volumetric_soil_water_layer_3: 0.20,
        volumetric_soil_water_layer_4: 0.22,
        surface_solar_radiation_downwards_sum: 16.0,
        u_component_of_wind_10m: 1.0,
        v_component_of_wind_10m: 0.5,
        day_count: 100,
      });
    } else if (presetType === "critical") {
      setInputs({
        area_id: 14, // Saint Catherine
        ndvi_mean: 0.05, // Chronically stressed
        evi: 0.02,
        savi: 0.04,
        vegetation_percent: 8.0,
        temperature_2m_c: 44.0, // High temperature stress
        total_precipitation_sum: 0.0,
        volumetric_soil_water_layer_1: 0.01, // Low soil moisture
        volumetric_soil_water_layer_2: 0.02,
        volumetric_soil_water_layer_3: 0.04,
        volumetric_soil_water_layer_4: 0.06,
        surface_solar_radiation_downwards_sum: 28.5, // High solar radiation
        u_component_of_wind_10m: 4.2,
        v_component_of_wind_10m: 3.5,
        day_count: 200,
      });
    } else {
      // Moderate stress
      setInputs({
        area_id: 6, // White Desert
        ndvi_mean: 0.18,
        evi: 0.10,
        savi: 0.14,
        vegetation_percent: 18.0,
        temperature_2m_c: 38.0,
        total_precipitation_sum: 0.1,
        volumetric_soil_water_layer_1: 0.04,
        volumetric_soil_water_layer_2: 0.05,
        volumetric_soil_water_layer_3: 0.08,
        volumetric_soil_water_layer_4: 0.11,
        surface_solar_radiation_downwards_sum: 24.0,
        u_component_of_wind_10m: 2.5,
        v_component_of_wind_10m: 1.8,
        day_count: 160,
      });
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case "Critical":
        return "text-rose-500 bg-rose-500/10 border-rose-500/30";
      case "High":
        return "text-amber-500 bg-amber-500/10 border-amber-500/30";
      case "Moderate":
        return "text-yellow-500 bg-yellow-500/10 border-yellow-500/30";
      default:
        return "text-emerald-500 bg-emerald-500/10 border-emerald-500/30";
    }
  };

  const getRiskBorder = (level: string) => {
    switch (level) {
      case "Critical": return "border-rose-500/50 shadow-rose-950/20";
      case "High": return "border-amber-500/50 shadow-amber-950/20";
      case "Moderate": return "border-yellow-500/50 shadow-yellow-950/20";
      default: return "border-emerald-500/50 shadow-emerald-950/20";
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 relative min-h-[90vh]">
      {/* Background ambient glow */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/10 rounded-full blur-[120px] -z-10 pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-emerald-500/5 rounded-full blur-[120px] -z-10 pointer-events-none" />

      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-end justify-between flex-wrap gap-6 mb-10"
      >
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold mb-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            {lang === "ar" ? "نظام الذكاء الاصطناعي النشط" : "Active AI System"}
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold flex items-center gap-3 tracking-tight">
            <ShieldAlert className="size-10 sm:size-12 text-primary drop-shadow-sm" />
            <span className="bg-gradient-to-r from-emerald-950 via-emerald-800 to-emerald-600 bg-clip-text text-transparent">
              {lang === "ar" ? "الإنذار المبكر للمحميات" : "Early Warning System"}
            </span>
          </h1>
          <p className="text-slate-600 text-base sm:text-lg max-w-2xl leading-relaxed">
            {lang === "ar"
              ? "نظام متطور لمراقبة الإجهاد البيئي والجفاف في 31 محمية طبيعية بمصر باستخدام خوارزميات التعلم الآلي ونموذج الاندماج متعدد القنوات."
              : "Monitor ecological and vegetation stress in Egypt's 31 protected areas using advanced machine learning fusion algorithms."}
          </p>
        </div>
        <div className="flex gap-3 flex-wrap">
          <button onClick={() => applyPreset("healthy")} className="px-4 py-2 rounded-xl text-xs font-bold bg-white/60 border border-emerald-200 hover:border-emerald-500 hover:bg-emerald-50 text-emerald-700 transition-all duration-300 hover:shadow-md hover:-translate-y-0.5">
            {lang === "ar" ? "🌱 وضع طبيعي" : "🌱 Healthy"}
          </button>
          <button onClick={() => applyPreset("moderate")} className="px-4 py-2 rounded-xl text-xs font-bold bg-white/60 border border-yellow-200 hover:border-yellow-500 hover:bg-yellow-50 text-yellow-700 transition-all duration-300 hover:shadow-md hover:-translate-y-0.5">
            {lang === "ar" ? "⚠️ إجهاد متوسط" : "⚠️ Moderate"}
          </button>
          <button onClick={() => applyPreset("critical")} className="px-4 py-2 rounded-xl text-xs font-bold bg-white/60 border border-rose-200 hover:border-rose-500 hover:bg-rose-50 text-rose-700 transition-all duration-300 hover:shadow-md hover:-translate-y-0.5">
            {lang === "ar" ? "🚨 إجهاد حرج" : "🚨 Critical"}
          </button>
        </div>
      </motion.div>

      <div className="grid gap-8 lg:grid-cols-5">
        {/* Left column: Inputs Panel */}
        <div className="lg:col-span-2 space-y-6">
          <form onSubmit={runSimulation} className="glass rounded-[2rem] p-6 sm:p-8 bg-white/50 border border-white/60 shadow-[0_8px_32px_rgba(34,197,94,0.08)] relative overflow-hidden backdrop-blur-2xl">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary/40 to-transparent opacity-80" />
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-primary/5 blur-[60px] -z-10 rounded-full pointer-events-none" />
            
            <h2 className="text-xl font-bold mb-8 flex items-center gap-3 text-slate-900">
              <div className="p-2 bg-emerald-100 rounded-lg border border-emerald-200">
                <Layers className="size-5 text-emerald-700" />
              </div>
              {lang === "ar" ? "مدخلات المحاكاة المناخية" : "Simulation Climate Inputs"}
            </h2>

            <div className="space-y-6">
              {/* Protected Area Select */}
              <div className="group">
                <label className="text-sm font-bold text-slate-700 block mb-2 group-hover:text-emerald-700 transition-colors">
                  {lang === "ar" ? "المحمية الطبيعية المستهدفة" : "Target Protected Area"}
                </label>
                <div className="relative">
                  <select
                    value={inputs.area_id}
                    onChange={(e) => handleInputChange("area_id", parseInt(e.target.value))}
                    className="w-full bg-white/80 hover:bg-white border border-emerald-100 hover:border-emerald-300 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 rounded-xl px-4 py-3.5 text-sm font-medium text-slate-800 focus:outline-none appearance-none cursor-pointer transition-all duration-200 shadow-sm"
                  >
                    {EGYPTIAN_PROTECTED_AREAS.map(area => (
                      <option key={area.id} value={area.id} className="text-slate-800">
                        {lang === "ar" ? area.name_ar : area.name_en} (ID={area.id})
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="size-4 text-emerald-600 absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
              </div>

              {/* NDVI Mean */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-700">{lang === "ar" ? "مؤشر غطاء نباتي NDVI (متوسط)" : "NDVI Mean"}</span>
                  <span className="text-emerald-700 font-bold font-mono">{inputs.ndvi_mean.toFixed(2)}</span>
                </div>
                <input
                  type="range" min="-0.1" max="0.9" step="0.01"
                  value={inputs.ndvi_mean}
                  onChange={(e) => handleInputChange("ndvi_mean", parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Enhanced Vegetation Index (EVI) */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-700">{lang === "ar" ? "مؤشر غطاء نباتي محسّن EVI" : "EVI"}</span>
                  <span className="text-emerald-700 font-bold font-mono">{inputs.evi.toFixed(2)}</span>
                </div>
                <input
                  type="range" min="-0.1" max="0.9" step="0.01"
                  value={inputs.evi}
                  onChange={(e) => handleInputChange("evi", parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Vegetation Cover % */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-700">{lang === "ar" ? "نسبة الغطاء النباتي (%)" : "Vegetation Cover %"}</span>
                  <span className="text-emerald-700 font-bold font-mono">{inputs.vegetation_percent.toFixed(1)}%</span>
                </div>
                <input
                  type="range" min="0" max="100" step="0.5"
                  value={inputs.vegetation_percent}
                  onChange={(e) => handleInputChange("vegetation_percent", parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Temperature 2m Celsius */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-700 flex items-center gap-1">
                    <Thermometer className="size-3.5 text-slate-500" />
                    {lang === "ar" ? "درجة حرارة الهواء (°مئوية)" : "Air Temperature (2m)"}
                  </span>
                  <span className="text-emerald-700 font-bold font-mono">{inputs.temperature_2m_c.toFixed(1)}°C</span>
                </div>
                <input
                  type="range" min="-5" max="55" step="0.5"
                  value={inputs.temperature_2m_c}
                  onChange={(e) => handleInputChange("temperature_2m_c", parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Soil Moisture Layer 1 */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-700 flex items-center gap-1">
                    <Droplets className="size-3.5 text-slate-500" />
                    {lang === "ar" ? "رطوبة التربة - الطبقة السطحية (0-7 سم)" : "Soil Moisture (Layer 1)"}
                  </span>
                  <span className="text-emerald-700 font-bold font-mono">{inputs.volumetric_soil_water_layer_1.toFixed(3)} m³/m³</span>
                </div>
                <input
                  type="range" min="0.0" max="0.8" step="0.005"
                  value={inputs.volumetric_soil_water_layer_1}
                  onChange={(e) => handleInputChange("volumetric_soil_water_layer_1", parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Precipitation */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-700">{lang === "ar" ? "هطول الأمطار اليومي (ملم)" : "Daily Precipitation"}</span>
                  <span className="text-emerald-700 font-bold font-mono">{inputs.total_precipitation_sum.toFixed(2)} mm</span>
                </div>
                <input
                  type="range" min="0.0" max="25.0" step="0.1"
                  value={inputs.total_precipitation_sum}
                  onChange={(e) => handleInputChange("total_precipitation_sum", parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Advanced collapse toggle */}
              <details className="group">
                <summary className="text-xs text-emerald-700 font-bold cursor-pointer hover:text-emerald-800 list-none flex items-center gap-1 select-none mt-2">
                  <ChevronDown className="size-3 transition-transform group-open:rotate-180" />
                  {lang === "ar" ? "إعدادات مناخية متقدمة" : "Show Advanced Climate Settings"}
                </summary>
                <div className="pt-4 space-y-4 border-t border-emerald-100/50 mt-2">
                  {/* SAVI */}
                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-500 font-semibold">{lang === "ar" ? "مؤشر SAVI للتربة" : "SAVI"}</span>
                      <span className="text-emerald-700 font-mono font-bold">{inputs.savi.toFixed(2)}</span>
                    </div>
                    <input
                      type="range" min="-0.1" max="0.9" step="0.01"
                      value={inputs.savi}
                      onChange={(e) => handleInputChange("savi", parseFloat(e.target.value))}
                      className="w-full accent-emerald-500/80 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>

                  {/* Soil Moisture Layer 2 */}
                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-500 font-semibold">{lang === "ar" ? "رطوبة التربة - الطبقة 2 (7-28 سم)" : "Soil Moisture (Layer 2)"}</span>
                      <span className="text-emerald-700 font-mono font-bold">{inputs.volumetric_soil_water_layer_2.toFixed(3)} m³/m³</span>
                    </div>
                    <input
                      type="range" min="0.0" max="0.8" step="0.005"
                      value={inputs.volumetric_soil_water_layer_2}
                      onChange={(e) => handleInputChange("volumetric_soil_water_layer_2", parseFloat(e.target.value))}
                      className="w-full accent-emerald-500/80 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>

                  {/* Soil Moisture Layer 4 */}
                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-500 font-semibold">{lang === "ar" ? "رطوبة التربة - الطبقة 4 العمق" : "Soil Moisture (Layer 4)"}</span>
                      <span className="text-emerald-700 font-mono font-bold">{inputs.volumetric_soil_water_layer_4.toFixed(3)} m³/m³</span>
                    </div>
                    <input
                      type="range" min="0.0" max="0.8" step="0.005"
                      value={inputs.volumetric_soil_water_layer_4}
                      onChange={(e) => handleInputChange("volumetric_soil_water_layer_4", parseFloat(e.target.value))}
                      className="w-full accent-emerald-500/80 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>

                  {/* Radiation */}
                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-500 font-semibold flex items-center gap-1">
                        <Sun className="size-3.5 text-slate-400" />
                        {lang === "ar" ? "الإشعاع الشمسي الهابط (MJ/m²)" : "Solar Radiation Sum"}
                      </span>
                      <span className="text-emerald-700 font-mono font-bold">{inputs.surface_solar_radiation_downwards_sum.toFixed(1)}</span>
                    </div>
                    <input
                      type="range" min="1.0" max="35.0" step="0.5"
                      value={inputs.surface_solar_radiation_downwards_sum}
                      onChange={(e) => handleInputChange("surface_solar_radiation_downwards_sum", parseFloat(e.target.value))}
                      className="w-full accent-emerald-500/80 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>

                  {/* Wind speed indicator */}
                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-500 font-semibold flex items-center gap-1">
                        <Wind className="size-3.5 text-slate-400" />
                        {lang === "ar" ? "مركبة الرياح الأفقية u (م/ث)" : "U Wind Component"}
                      </span>
                      <span className="text-emerald-700 font-mono font-bold">{inputs.u_component_of_wind_10m.toFixed(1)} m/s</span>
                    </div>
                    <input
                      type="range" min="-15" max="15" step="0.1"
                      value={inputs.u_component_of_wind_10m}
                      onChange={(e) => handleInputChange("u_component_of_wind_10m", parseFloat(e.target.value))}
                      className="w-full accent-emerald-500/80 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>
                </div>
              </details>

              <button
                type="submit"
                disabled={loading}
                className="group relative w-full overflow-hidden bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl py-4 px-4 shadow-[0_4px_20px_rgba(16,185,129,0.3)] hover:shadow-[0_8px_30px_rgba(16,185,129,0.5)] flex items-center justify-center gap-2 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed mt-8 hover:-translate-y-1"
              >
                <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
                {loading ? (
                  <>
                    <Loader2 className="size-5 animate-spin" />
                    <span className="tracking-wide">{lang === "ar" ? "جاري الاستدلال..." : "Running EWS Fusion..."}</span>
                  </>
                ) : (
                  <>
                    <RefreshCw className="size-5 group-hover:rotate-180 transition-transform duration-500" />
                    <span className="tracking-wide">{lang === "ar" ? "تشغيل محاكاة الإنذار المبكر" : "Run EWS Simulation"}</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Right column: Results Panel */}
        <div className="lg:col-span-3">
          <AnimatePresence mode="wait">
            {loading && !result ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                className="glass rounded-3xl bg-white/40 border border-white/60 shadow-sm p-10 h-full flex flex-col items-center justify-center text-center min-h-[450px]"
              >
                <Loader2 className="size-16 text-emerald-600 animate-spin mb-4" />
                <h3 className="text-xl font-bold mb-2 text-slate-800">
                  {lang === "ar" ? "تحليل البيانات المناخية والغطاء النباتي" : "Analyzing Ecosystem Telemetry"}
                </h3>
                <p className="text-slate-500 text-sm max-w-sm">
                  {lang === "ar"
                    ? "تقوم البوابة باستدعاء نماذج الغابات العشوائية و XGBoost والانحدار اللوجستي ومعايرتها لحساب احتمالات الإجهاد البيئي بدقة."
                    : "FastAPI is running calibrated XGBoost, Random Forest, and Linear models, routing through 3-branch decision fusion."}
                </p>
              </motion.div>
            ) : error ? (
              <motion.div
                key="error"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="glass border border-rose-200 bg-white/60 shadow-[0_8px_30px_rgba(244,63,94,0.1)] rounded-[2rem] p-8 text-center text-rose-500 min-h-[300px] flex flex-col items-center justify-center backdrop-blur-2xl"
              >
                <div className="p-4 bg-rose-50 rounded-full mb-4 border border-rose-100">
                  <AlertTriangle className="size-12 text-rose-500" />
                </div>
                <h3 className="font-bold text-xl mb-2 text-slate-900">{lang === "ar" ? "فشل الاتصال بخادم النماذج" : "Simulation Request Failed"}</h3>
                <p className="text-sm text-slate-600 max-w-sm mb-4">{error}</p>
              </motion.div>
            ) : result ? (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 30, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ type: "spring", damping: 25, stiffness: 200 }}
                className={`glass border bg-white/60 rounded-[2rem] p-8 relative overflow-hidden backdrop-blur-2xl transition-all duration-300 ${getRiskBorder(result.risk_level)} ${loading ? "opacity-60 grayscale-[30%] scale-[0.99] pointer-events-none" : "opacity-100"}`}
              >
                {/* Visual glow matching risk level */}
                <div className={`absolute top-0 right-0 w-48 h-48 rounded-full blur-[80px] -z-10 opacity-20 ${
                  result.risk_level === "Critical" ? "bg-rose-500" :
                  result.risk_level === "High" ? "bg-amber-500" :
                  result.risk_level === "Moderate" ? "bg-yellow-500" : "bg-emerald-500"
                }`} />

                {/* Header info */}
                <div className="flex items-start justify-between flex-wrap gap-4 border-b border-emerald-100/50 pb-4 mb-6">
                  <div>
                    <span className="text-xs text-slate-500 font-mono uppercase tracking-wider">{result.model_version}</span>
                    <h3 className="text-2xl font-bold mt-0.5 text-slate-900">
                      {lang === "ar" ? result.area_name : EGYPTIAN_PROTECTED_AREAS.find(a => a.id === result.area_id)?.name_en || result.area_name}
                    </h3>
                  </div>
                  <div className={`px-4 py-2 rounded-xl text-sm font-bold border bg-white shadow-sm ${getRiskColor(result.risk_level)}`}>
                    {lang === "ar"
                      ? (result.risk_level === "Critical" ? "إجهاد حرج 🔴" :
                         result.risk_level === "High" ? "إجهاد مرتفع 🟠" :
                         result.risk_level === "Moderate" ? "إجهاد متوسط 🟡" : "مستقر / طبيعي 🟢")
                      : `${result.risk_level} Stress`}
                  </div>
                </div>

                {/* Score & Gauge Section */}
                <div className="grid gap-6 md:grid-cols-5 mb-6">
                  {/* Gauge */}
                  <div className="md:col-span-2 flex flex-col items-center justify-center py-4 bg-white/50 rounded-2xl border border-white/60 shadow-sm">
                    <div className="relative size-36">
                      {/* SVG Circle Gauge */}
                      <svg className="size-full -rotate-90 drop-shadow-lg">
                        <defs>
                          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                            <feGaussianBlur stdDeviation="4" result="blur" />
                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                          </filter>
                        </defs>
                        <circle cx="72" cy="72" r="60" className="stroke-slate-200" strokeWidth="10" fill="transparent" />
                        <motion.circle
                          cx="72" cy="72" r="60"
                          className={`${
                            result.risk_level === "Critical" ? "stroke-rose-500" :
                            result.risk_level === "High" ? "stroke-amber-500" :
                            result.risk_level === "Moderate" ? "stroke-yellow-500" : "stroke-emerald-500"
                          }`}
                          strokeWidth="10"
                          fill="transparent"
                          strokeDasharray={377}
                          initial={{ strokeDashoffset: 377 }}
                          animate={{ strokeDashoffset: 377 - (377 * result.stress_probability) }}
                          transition={{ duration: 2, ease: "easeOut" }}
                          strokeLinecap="round"
                          filter="url(#glow)"
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-4xl font-extrabold font-mono tracking-tighter text-slate-900 drop-shadow-sm">{(result.stress_probability * 100).toFixed(1)}<span className="text-xl text-slate-400">%</span></span>
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">{lang === "ar" ? "احتمالية الإجهاد" : "Stress Prob"}</span>
                      </div>
                    </div>
                    <div className="text-center mt-3 px-2">
                      <span className="text-xs text-slate-500 block">
                        {lang === "ar" ? `دقة المحاذاة للثقة: ${(result.confidence * 100).toFixed(0)}%` : `Model Agreement Confidence: ${(result.confidence * 100).toFixed(0)}%`}
                      </span>
                    </div>
                  </div>

                  {/* Actions / Recs */}
                  <div className="md:col-span-3 space-y-4">
                    <div>
                      <h4 className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1">
                        {lang === "ar" ? "الإجراءات الوقائية المطلوبة" : "Recommended Preventive Actions"}
                      </h4>
                      <p className="text-slate-800 text-sm leading-relaxed font-medium bg-emerald-50/50 border border-emerald-100 rounded-xl p-3 shadow-sm">
                        {lang === "ar" ? result.action_ar : result.action}
                      </p>
                    </div>

                  </div>
                </div>

                {/* Trigger Reasons / Indicators */}
                <div className="mb-6">
                  <h4 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                    <Info className="size-4 text-emerald-600" />
                    {lang === "ar" ? "مؤشرات الإجهاد المرصودة" : "Detected Stress Indicators"}
                  </h4>
                  {result.reasoning.length === 0 ? (
                    <div className="text-sm text-slate-500 italic bg-white/50 border border-emerald-100 rounded-xl p-3">
                      {lang === "ar" ? "لا توجد مؤشرات إجهاد مفعّلة في هذا النطاق." : "No stress indicator triggers detected."}
                    </div>
                  ) : (
                    <ul className="space-y-2">
                      {(lang === "ar" ? result.reasoning_ar : result.reasoning).map((reason, idx) => (
                        <li key={idx} className="text-sm text-slate-700 bg-white/60 border border-emerald-100/50 rounded-xl p-3 flex items-start gap-2.5 shadow-sm">
                          <CheckCircle className="size-4 text-emerald-600 shrink-0 mt-0.5" />
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* Ensemble Breakdowns */}
                <div className="mb-6">
                  <h4 className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-3">
                    {lang === "ar" ? "نتائج الاحتمالات التفصيلية للموديلات" : "Individual Machine Learning Model Probs"}
                  </h4>
                  <div className="grid gap-3 grid-cols-3">
                    {Object.entries(result.individual_probs).map(([modelName, prob]) => (
                      <div key={modelName} className="bg-white/60 border border-slate-200 rounded-xl p-3 text-center shadow-sm">
                        <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">{modelName}</span>
                        <span className="text-lg font-bold font-mono text-slate-800">{(prob * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* SHAP Explanation */}
                {result.shap_explanation && result.shap_explanation.feature_impacts && result.shap_explanation.feature_impacts.length > 0 && (
                  <div>
                    <h4 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                      <BarChart3 className="size-4 text-emerald-600" />
                      {lang === "ar" ? "تحليل مساهمة السمات البيئية (SHAP)" : "Environmental Feature Impact Analysis (SHAP)"}
                    </h4>
                    <div className="space-y-2 bg-white/60 border border-emerald-100/50 rounded-xl p-4 shadow-sm">
                      {result.shap_explanation.feature_impacts.slice(0, 6).map((impact, idx) => {
                        const isPositive = impact.shap_value >= 0;
                        // Max shap value to scale the bars
                        const maxVal = Math.max(...result.shap_explanation!.feature_impacts.map(i => Math.abs(i.shap_value))) || 0.1;
                        const percentage = Math.min(100, (Math.abs(impact.shap_value) / maxVal) * 100);

                        return (
                          <div key={idx} className="space-y-1">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="font-mono text-slate-700 font-medium">{impact.feature}</span>
                              <span className="text-slate-500">
                                val: <span className="text-slate-800 font-semibold font-mono">{impact.feature_value.toFixed(3)}</span>
                                <span className="mx-2 opacity-30">|</span>
                                SHAP: <span className={`${isPositive ? "text-rose-600" : "text-emerald-600"} font-bold font-mono bg-white/80 px-1.5 py-0.5 rounded shadow-sm border border-slate-100`}>
                                  {isPositive ? "+" : ""}{impact.shap_value.toFixed(4)}
                                </span>
                              </span>
                            </div>
                            <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden flex shadow-inner">
                              {/* If positive impact (increases risk), bar pushes right (red) */}
                              {isPositive ? (
                                <motion.div 
                                  initial={{ width: 0 }}
                                  animate={{ width: `${percentage}%` }}
                                  transition={{ duration: 1.5, ease: "easeOut", delay: idx * 0.1 }}
                                  className="h-full bg-gradient-to-r from-rose-500 to-rose-400 rounded-full shadow-[0_0_10px_rgba(244,63,94,0.3)]" 
                                />
                              ) : (
                                /* If negative impact (reduces risk), bar pushes right (green) */
                                <motion.div 
                                  initial={{ width: 0 }}
                                  animate={{ width: `${percentage}%` }}
                                  transition={{ duration: 1.5, ease: "easeOut", delay: idx * 0.1 }}
                                  className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.3)]" 
                                />
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="glass rounded-[2rem] bg-white/40 border border-white/60 p-10 h-full flex flex-col items-center justify-center text-center min-h-[450px] relative overflow-hidden backdrop-blur-2xl shadow-[0_8px_32px_rgba(34,197,94,0.05)]"
              >
                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-[0.05] z-0"></div>
                <ShieldAlert className="size-16 text-emerald-300 mb-4 animate-pulse" />
                <h3 className="text-xl font-bold mb-2 text-slate-800">
                  {lang === "ar" ? "بانتظار تشغيل المحاكاة" : "Awaiting EWS Simulation"}
                </h3>
                <p className="text-slate-500 text-sm max-w-sm">
                  {lang === "ar"
                    ? "اختر محمية طبيعية من القائمة واضبط بارامترات المناخ الحالية، ثم اضغط على زر التشغيل لبدء فحص وتقييم مخاطر الجفاف والتصحر النباتي."
                    : "Select a protected area, adjust telemetry sliders, and click run to analyze risk levels, trigger rules and trace AI shap values."}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* EWS Report Integration - Standalone & Full Width */}
      {!loading && !error && result && (result.report_html || result.report_en || result.report_ar) && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.2 }}
          className="mt-12 relative w-full max-w-5xl mx-auto"
        >
          <h3 className="font-display font-bold text-slate-900 mb-4 flex items-center justify-center gap-3 px-2 text-2xl">
            <div className="p-2 bg-emerald-100 rounded-xl border border-emerald-200 shadow-sm">
              <Layers className="size-6 text-emerald-700" />
            </div>
            {lang === "ar" ? "التقرير الشامل لنظام الإنذار المبكر" : "Comprehensive Early Warning System Report"}
          </h3>
          <div className="glass rounded-[2rem] overflow-hidden bg-white/80 border border-slate-200 shadow-lg p-0 w-full relative backdrop-blur-xl">
            {result.report_html ? (
              <iframe 
                srcDoc={result.report_html} 
                className="w-full min-h-[600px] border-none rounded-3xl"
                title="EWS Expert Report"
              />
            ) : (
              <div className="p-8">
                <div 
                  className="prose prose-stone prose-emerald max-w-none w-full text-slate-800 font-medium text-lg"
                  dangerouslySetInnerHTML={{ 
                    __html: (lang === "ar" ? result.report_ar! : result.report_en!).replace(/\n/g, '<br/>')
                  }} 
                />
              </div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
