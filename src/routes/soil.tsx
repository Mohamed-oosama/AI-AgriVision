import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sprout, Wand2, CheckCircle2, Leaf, Sun, Droplets, FlaskConical, ChevronDown, Layers, Loader2, Thermometer, CloudRain } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";

const CROP_IDEAL_NUTRIENTS: Record<string, { n: number, p: number, k: number }> = {
  Tomato: { n: 120, p: 60, k: 120 },
  Wheat: { n: 100, p: 50, k: 80 },
  Corn: { n: 140, p: 60, k: 100 },
  Cotton: { n: 90, p: 40, k: 90 },
  Potato: { n: 150, p: 80, k: 150 },
  Rice: { n: 80, p: 40, k: 40 },
  Banana: { n: 150, p: 50, k: 250 },
};

export const CropVisual = ({ crop, className = "size-14" }: { crop: string; className?: string }) => {
  switch (crop) {
    case "Tomato":
      return (
        <svg className={`${className} mx-auto text-rose-500 fill-rose-500/10 animate-bounce`} style={{ animationDuration: '3s' }} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="13" r="7" />
          <path d="M 12,6 C 12,4 10,4 10,4 M 12,6 C 12,4 14,4 14,4 M 12,6 L 12,3" stroke="currentColor" strokeWidth="2" fill="none" />
          <path d="M 9,7 C 9,7 10,8 12,6 C 14,8 15,7 15,7" stroke="currentColor" strokeWidth="1.5" fill="none" />
        </svg>
      );
    case "Wheat":
      return (
        <svg className={`${className} mx-auto text-amber-500 fill-amber-500/10 animate-bounce`} style={{ animationDuration: '3s' }} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="22" x2="12" y2="4" strokeWidth="2" />
          <path d="M 12,6 Q 8,5 10,9 Q 12,8 12,6" />
          <path d="M 12,6 Q 16,5 14,9 Q 12,8 12,6" />
          <path d="M 12,10 Q 8,9 10,13 Q 12,12 12,10" />
          <path d="M 12,10 Q 16,9 14,13 Q 12,12 12,10" />
          <path d="M 12,14 Q 8,13 10,17 Q 12,16 12,14" />
          <path d="M 12,14 Q 16,13 14,17 Q 12,16 12,14" />
        </svg>
      );
    case "Corn":
      return (
        <svg className={`${className} mx-auto text-yellow-500 fill-yellow-500/10 animate-bounce`} style={{ animationDuration: '3s' }} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path d="M 9,16 C 9,20 15,20 15,16 L 14,6 C 14,4 10,4 10,6 Z" />
          <line x1="12" y1="6" x2="12" y2="18" strokeWidth="1" strokeDasharray="2 2" />
          <line x1="10" y1="8" x2="14" y2="8" strokeWidth="1" />
          <line x1="10" y1="11" x2="14" y2="11" strokeWidth="1" />
          <line x1="9" y1="14" x2="15" y2="14" strokeWidth="1" />
          <path d="M 6,18 C 8,14 8,8 10,6" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M 18,18 C 16,14 16,8 14,6" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      );
    case "Cotton":
      return (
        <svg className={`${className} mx-auto text-sky-400 fill-sky-100/20 animate-bounce`} style={{ animationDuration: '3s' }} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="9" r="4" />
          <circle cx="8" cy="12" r="4" />
          <circle cx="16" cy="12" r="4" />
          <circle cx="12" cy="14" r="4" />
          <path d="M 6,15 C 8,17 10,18 12,16 C 14,18 16,17 18,15 L 12,21 Z" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      );
    case "Potato":
      return (
        <svg className={`${className} mx-auto text-amber-700 fill-amber-700/10 animate-bounce`} style={{ animationDuration: '3s' }} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path d="M 6,12 C 6,8 18,7 18,12 C 18,17 6,16 6,12 Z" />
          <circle cx="9" cy="10" r="1" fill="currentColor" />
          <circle cx="14" cy="13" r="1" fill="currentColor" />
          <circle cx="11" cy="14" r="1" fill="currentColor" />
          <circle cx="15" cy="10" r="1" fill="currentColor" />
        </svg>
      );
    case "Rice":
      return (
        <svg className={`${className} mx-auto text-emerald-600 fill-emerald-500/5 animate-bounce`} style={{ animationDuration: '3s' }} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path d="M 6,22 C 8,16 12,10 18,6" fill="none" strokeWidth="2" />
          <circle cx="18" cy="6" r="2.5" />
          <circle cx="15" cy="8" r="2" />
          <circle cx="13" cy="11" r="2" />
          <circle cx="10" cy="14" r="2" />
          <circle cx="16" cy="10" r="2" />
          <circle cx="13" cy="14" r="2" />
        </svg>
      );
    case "Banana":
      return (
        <svg className={`${className} mx-auto text-yellow-500 fill-yellow-400/10 animate-bounce`} style={{ animationDuration: '3s' }} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path d="M5 19c6 0 11-4 13-10 1-3-.5-5-1.5-6-.5-.5-1.5 0-1.5.5.5 1 .5 2 0 3-2 4-6.5 7.5-11 7.5-.5 0-1 .5-1 1s.5 1 1 1c1.5 0 2.5.5 3 1.5.5.5 1.5.5 1.5 0 .5-1.5.5-2.5-3.5-2.5z" />
        </svg>
      );
    default:
      return (
        <svg className={`${className} mx-auto text-emerald-500 fill-emerald-500/10 animate-bounce`} style={{ animationDuration: '3s' }} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a15 15 0 0 0-15 15c0 .73.18 1.42.49 2.05l2.42-2.42a3.5 3.5 0 0 1 4.95 0 3.5 3.5 0 0 1 0 4.95l-2.42 2.42c.63.31 1.32.49 2.05.49a15 15 0 0 0 15-15Z" />
          <path d="m12 12 9 9" />
        </svg>
      );
  }
};

export function getCropFromDisease(disease: string): string | null {
  const d = disease.toLowerCase();
  if (d.includes("tomato")) return "Tomato";
  if (d.includes("wheat")) return "Wheat";
  if (d.includes("corn") || d.includes("maize")) return "Corn";
  if (d.includes("cotton")) return "Cotton";
  if (d.includes("potato")) return "Potato";
  if (d.includes("rice")) return "Rice";
  return null;
}


export const Route = createFileRoute("/soil")({
  head: () => ({ meta: [{ title: "Smart Soil Analysis — AI AgriVision" }, { name: "description", content: "AI-powered fertilizer recommendations." }] }),
  component: SoilPage,
});

function SoilPage() {
  const { t, lang } = useI18n();
  const [crops, setCrops] = useState<string[]>(["Tomato", "Wheat", "Corn", "Cotton", "Potato", "Rice", "Banana"]);
  const [crop, setCrop] = useState("Tomato");
  const [season, setSeason] = useState("Summer");
  const [n, setN] = useState("80");
  const [p, setP] = useState("40");
  const [k, setK] = useState("90");
  const [ph, setPh] = useState("6.5");
  const [soilType, setSoilType] = useState("Loamy");
  const [temp, setTemp] = useState("Auto");
  const [humidity, setHumidity] = useState("Auto");
  const [rainfall, setRainfall] = useState("Auto");
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<{
    subject: string;
    intro?: string;
    recommendation: string;
    n?: string;
    p?: string;
    k?: string;
    fullText?: string;
    n_target?: number;
    p_target?: number;
    k_target?: number;
  } | null>(null);

  useEffect(() => {
    fetch("/api/soil/crops")
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setCrops(data);
          if (data.includes("Tomato")) {
            setCrop("Tomato");
          } else {
            setCrop(data[0]);
          }
        }
      })
      .catch(err => console.error("Error fetching dynamic crop list:", err));
  }, []);

  const seasons = ["Summer", "Spring", "Autumn", "Winter"];
  const soilTypes = ["Loamy", "Clay", "Sandy", "Silty", "Peaty"];

  const chartData = report ? [
    {
      name: lang === "ar" ? "النيتروجين" : "Nitrogen",
      Current: Number(n) || 0,
      Recommended: report.n_target || CROP_IDEAL_NUTRIENTS[crop]?.n || 100,
    },
    {
      name: lang === "ar" ? "الفسفور" : "Phosphorus",
      Current: Number(p) || 0,
      Recommended: report.p_target || CROP_IDEAL_NUTRIENTS[crop]?.p || 50,
    },
    {
      name: lang === "ar" ? "البوتاسيوم" : "Potassium",
      Current: Number(k) || 0,
      Recommended: report.k_target || CROP_IDEAL_NUTRIENTS[crop]?.k || 80,
    },
  ] : [];

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const payload = {
        crop: crop,
        season: season,
        n_val: parseFloat(n) || 0.0,
        p_val: parseFloat(p) || 0.0,
        k_val: parseFloat(k) || 0.0,
        ph_val: parseFloat(ph) || 0.0,
        soil_type: soilType,
        temperature: temp.toLowerCase().trim() === "auto" ? null : parseFloat(temp),
        humidity: humidity.toLowerCase().trim() === "auto" ? null : parseFloat(humidity),
        rainfall: rainfall.toLowerCase().trim() === "auto" ? null : parseFloat(rainfall)
      };

      const response = await fetch("/api/soil/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (data.error) {
        console.error("API error:", data.error);
        setReport({
          subject: `${season} ${crop} Cultivation Recommendation (Simulation Mode)`,
          intro: `Dear Farmer,\n\nWe encountered an issue connecting to the AI Soil server: ${data.error}. Showing simulated calculation results instead.`,
          recommendation: `Based on standard crop averages:`,
          n: `Nitrogen: Recommended to add Urea based on target crop values.`,
          p: `Phosphorus: Keep monitoring levels.`,
          k: `Potassium: Keep monitoring levels.`
        });
      } else {
        setReport({
          subject: `${season} ${crop} Cultivation Recommendation Report`,
          recommendation: "",
          fullText: data.recommendation,
          n_target: data.n_target,
          p_target: data.p_target,
          k_target: data.k_target
        });
      }
    } catch (err: any) {
      console.error("Failed to generate recommendation:", err);
      setReport({
        subject: `${season} ${crop} Cultivation Recommendation (Simulation Mode)`,
        intro: `Dear Farmer,\n\nFailed to connect to the AI Soil server: ${err.message}. Showing simulated calculation results instead.`,
        recommendation: `Based on standard crop averages:`,
        n: `Nitrogen: Recommended to add Urea.`,
        p: `Phosphorus: Adequate.`,
        k: `Potassium: Adequate.`
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 relative">
      {/* Background glow orb */}
      <div className="absolute top-0 right-1/4 w-96 h-96 -z-10 gradient-mesh opacity-20 blur-[100px] rounded-full" />

      {/* Header section with badge */}
      <div className="flex items-center gap-4 mb-8">
        <div className="size-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 shadow-glow flex items-center justify-center shrink-0 dark:bg-emerald-500/20">
          <Sprout className="size-7" />
        </div>
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight text-foreground">{t("soil.title")}</h1>
          <p className="text-muted-foreground text-sm mt-1">{t("soil.sub")}</p>
        </div>
      </div>

      {/* Main card */}
      <div className="glass rounded-3xl p-6 sm:p-8 shadow-elegant border border-border/40 bg-white/40 dark:bg-black/20 backdrop-blur-md">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Target Crop */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <Leaf className="size-4 text-emerald-500" />
              {t("soil.crop")}
            </label>
            <div className="flex gap-3 items-center">
              <div className="relative flex-1">
                <select
                  value={crop}
                  onChange={e => setCrop(e.target.value)}
                  className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all cursor-pointer appearance-none text-foreground pr-10"
                >
                  {crops.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <div className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                  <ChevronDown className="size-4" />
                </div>
              </div>
              <div className="size-[46px] flex items-center justify-center rounded-2xl bg-white/40 dark:bg-zinc-900/40 border border-border/40 shrink-0 shadow-soft">
                <CropVisual crop={crop} className="size-8" />
              </div>
            </div>
          </div>

          {/* Season */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <Sun className="size-4 text-amber-500" />
              {t("soil.season")}
            </label>
            <div className="relative">
              <select
                value={season}
                onChange={e => setSeason(e.target.value)}
                className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all cursor-pointer appearance-none pr-10 text-foreground"
              >
                {seasons.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <div className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                <ChevronDown className="size-4" />
              </div>
            </div>
          </div>

          {/* pH Level */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <Droplets className="size-4 text-emerald-500" />
              {t("soil.ph")}
            </label>
            <input
              type="number"
              step="0.1"
              value={ph}
              onChange={e => setPh(e.target.value)}
              className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-foreground"
            />
          </div>

          {/* Nitrogen (N) */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <span className="size-5 rounded bg-emerald-500 text-white font-extrabold text-[10px] flex items-center justify-center shrink-0 shadow-soft">N</span>
              {t("soil.n")}
            </label>
            <input
              type="number"
              value={n}
              onChange={e => setN(e.target.value)}
              className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-foreground"
            />
          </div>

          {/* Phosphorus (P) */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <span className="size-5 rounded bg-amber-500 text-white font-extrabold text-[10px] flex items-center justify-center shrink-0 shadow-soft">P</span>
              {t("soil.p")}
            </label>
            <input
              type="number"
              value={p}
              onChange={e => setP(e.target.value)}
              className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-foreground"
            />
          </div>

          {/* Potassium (K) */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <span className="size-5 rounded bg-blue-500 text-white font-extrabold text-[10px] flex items-center justify-center shrink-0 shadow-soft">K</span>
              {t("soil.k")}
            </label>
            <input
              type="number"
              value={k}
              onChange={e => setK(e.target.value)}
              className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-foreground"
            />
          </div>

          {/* Temperature */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <Thermometer className="size-4 text-amber-500" />
              {t("soil.temp")}
            </label>
            <input
              type="text"
              value={temp}
              onChange={e => setTemp(e.target.value)}
              className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-foreground"
            />
          </div>

          {/* Humidity */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <Droplets className="size-4 text-blue-500" />
              {t("soil.humidity")}
            </label>
            <input
              type="text"
              value={humidity}
              onChange={e => setHumidity(e.target.value)}
              className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-foreground"
            />
          </div>

          {/* Rainfall */}
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <CloudRain className="size-4 text-sky-500" />
              {t("soil.rainfall")}
            </label>
            <input
              type="text"
              value={rainfall}
              onChange={e => setRainfall(e.target.value)}
              className="w-full rounded-2xl border border-border/60 bg-white/60 dark:bg-zinc-900/60 px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-foreground"
            />
          </div>

          {/* Soil Type */}
          <div className="md:col-span-3 flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <Layers className="size-4 text-emerald-500" />
              {t("soil.type")}
            </label>
            <div className="relative">
              <select
                value={soilType}
                onChange={e => setSoilType(e.target.value)}
                className="w-full rounded-2xl border border-emerald-500/50 bg-white/60 dark:bg-zinc-900/60 px-4 py-3.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all cursor-pointer appearance-none pr-12 text-foreground"
              >
                {soilTypes.map(st => <option key={st} value={st}>{st}</option>)}
              </select>
              <div className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-emerald-500">
                <FlaskConical className="size-5" />
              </div>
            </div>
          </div>

          {/* Generate Recommendation Button */}
          <div className="md:col-span-3 mt-2">
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full rounded-2xl bg-emerald-500 hover:bg-emerald-600 text-white font-semibold py-4 shadow-glow hover:shadow-elegant disabled:opacity-50 transition-all flex items-center justify-center gap-2 cursor-pointer text-sm sm:text-base"
            >
              {loading ? (
                <>
                  <Loader2 className="size-5 animate-spin" />
                  <span>{lang === "ar" ? "جاري إنشاء التوصيات..." : "Generating Recommendation..."}</span>
                </>
              ) : (
                <>
                  <Wand2 className="size-5" />
                  <span>{t("soil.btn")}</span>
                </>
              )}
            </button>
          </div>

        </div>
      </div>

      {/* Recommendations Report */}
      <AnimatePresence>
        {report && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-10">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="size-6 text-emerald-500" />
              <h2 className="text-2xl font-bold text-foreground">{t("soil.report")}</h2>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* Text Report */}
              <div className="lg:col-span-3 glass rounded-3xl p-6 md:p-8 relative border border-border/40 bg-white/40 dark:bg-zinc-900/40 backdrop-blur-md">
                <div className="flex items-start justify-between gap-4 border-b border-border/30 pb-4 mb-6">
                  <div className="text-sm sm:text-base leading-relaxed space-y-2">
                    <p className="font-bold text-foreground flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 shadow-soft">
                        <Leaf className="size-3" />
                        {crop}
                      </span>
                      <span>{report.subject}</span>
                    </p>
                  </div>
                  <div className="size-16 shrink-0 rounded-2xl bg-emerald-500/10 dark:bg-emerald-500/20 border border-emerald-500/20 flex items-center justify-center shadow-glow">
                    <CropVisual crop={crop} className="size-10" />
                  </div>
                </div>
                
                <div className="text-sm sm:text-base leading-relaxed space-y-4 pl-2">
                  {report.fullText ? (
                    <div className="whitespace-pre-wrap text-muted-foreground">{report.fullText}</div>
                  ) : (
                    <>
                      <p className="whitespace-pre-line text-muted-foreground">{report.intro}</p>
                      <p className="whitespace-pre-line text-muted-foreground">{report.recommendation}</p>
                      <ol className="list-decimal list-inside space-y-3 mt-4 text-muted-foreground font-medium">
                        <li>{report.n}</li>
                        <li>{report.p}</li>
                        <li>{report.k}</li>
                      </ol>
                    </>
                  )}
                </div>
              </div>

              {/* Chart Visual Representation */}
              <div className="lg:col-span-2 glass rounded-3xl p-6 relative border border-border/40 bg-white/40 dark:bg-zinc-900/40 backdrop-blur-md flex flex-col justify-between">
                <div>
                  <h3 className="font-display font-semibold text-base text-foreground mb-1">
                    {lang === "ar" ? "مقارنة نسب المغذيات" : "Nutrient Level Comparison"}
                  </h3>
                  <p className="text-muted-foreground text-xs mb-4">
                    {lang === "ar" ? "نسب المغذيات في تربتك مقارنة بالنسب المثالية الموصى بها." : "Your nutrient values compared to ideal requirements."}
                  </p>
                </div>
                <div className="h-[500px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                      <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ background: "rgba(255, 255, 255, 0.85)", border: "none", borderRadius: "12px" }} />
                      <Legend verticalAlign="top" height={36} iconSize={10} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="Current" fill="#f59e0b" name={lang === "ar" ? "الحالي" : "Current"} radius={[4, 4, 0, 0]} />
                      <Bar dataKey="Recommended" fill="#10b981" name={lang === "ar" ? "الموصى به" : "Recommended"} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

