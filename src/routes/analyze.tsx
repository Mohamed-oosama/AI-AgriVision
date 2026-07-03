import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Mic, Loader2, Sparkles, Network as NetIcon, CheckCircle2, Info, ChevronDown, Bug, Leaf, FlaskConical } from "lucide-react";
import { useRef, useState, useEffect } from "react";
import { useI18n } from "@/lib/i18n";
import { saveHistory, type Diagnosis } from "@/lib/ai-mock";
import { GraphView, type GraphNode, type GraphEdge } from "@/components/GraphView";
import { CropVisual, getCropFromDisease } from "./soil";
import { RealisticLeafSVG } from "../components/RealisticLeafSVG";

export const Route = createFileRoute("/analyze")({
  head: () => ({ meta: [{ title: "Analyze — AI AgriVision" }, { name: "description", content: "Upload a plant image and get an explainable diagnosis." }] }),
  component: Analyze,
});

let globalFile: File | null = null;
let globalPreview: string | null = null;
let globalQuestion = "";
let globalLoading = false;
let globalResult: Diagnosis & { viz_url?: string, report_html?: string, report_en?: string, report_ar?: string } | null = null;
let globalListening = false;

const analyzeListeners = new Set<() => void>();
function notifyAnalyze() { analyzeListeners.forEach(l => l()); }

function useGlobalAnalyze() {
  const [, setTick] = useState(0);
  useEffect(() => {
    const l = () => setTick(t => t + 1);
    analyzeListeners.add(l);
    return () => { analyzeListeners.delete(l); };
  }, []);

  return {
    file: globalFile,
    setFile: (f: any) => { globalFile = typeof f === 'function' ? f(globalFile) : f; notifyAnalyze(); },
    preview: globalPreview,
    setPreview: (p: any) => { globalPreview = typeof p === 'function' ? p(globalPreview) : p; notifyAnalyze(); },
    question: globalQuestion,
    setQuestion: (q: any) => { globalQuestion = typeof q === 'function' ? q(globalQuestion) : q; notifyAnalyze(); },
    loading: globalLoading,
    setLoading: (l: any) => { globalLoading = typeof l === 'function' ? l(globalLoading) : l; notifyAnalyze(); },
    result: globalResult,
    setResult: (r: any) => { globalResult = typeof r === 'function' ? r(globalResult) : r; notifyAnalyze(); },
    listening: globalListening,
    setListening: (l: any) => { globalListening = typeof l === 'function' ? l(globalListening) : l; notifyAnalyze(); }
  };
}

function Analyze() {
  const { t, lang } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const { file, setFile, preview, setPreview, question, setQuestion, loading, setLoading, result, setResult, listening, setListening } = useGlobalAnalyze();

  function onPick(f?: File) {
    if (!f) return;
    setFile(f);
    const url = URL.createObjectURL(f);
    setPreview(url); setResult(null);
  }

  async function run() {
    if (!file) return;
    setLoading(true);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const res = await fetch("/api/analyze", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      
      setResult(data);
      saveHistory(data);
    } catch (err) {
      console.error(err);
      alert("Error analyzing image");
    } finally {
      setLoading(false);
    }
  }

  function voice() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert("Voice not supported in this browser"); return; }
    const rec = new SR();
    rec.lang = lang === "ar" ? "ar-SA" : "en-US";
    rec.onresult = (e: any) => setQuestion(e.results[0][0].transcript);
    rec.onstart = () => setListening(true);
    rec.onend = () => setListening(false);
    rec.start();
  }

  const reasoning = result ? (lang === "ar" ? result.reasoningAr : result.reasoning) : [];
  const graphNodes: GraphNode[] = result ? [
    { id: "img", label: "Leaf image", group: "crop" },
    ...reasoning.map((r, i) => ({ id: `s${i}`, label: r.step, group: "agent" as const })),
    { id: "dx", label: lang === "ar" ? result.diseaseAr : result.disease, group: "disease" as const },
    { id: "tx", label: lang === "ar" ? "علاج" : "Treatment", group: "treatment" as const },
  ] : [];
  const graphEdges: GraphEdge[] = result ? [
    { source: "img", target: "s0" },
    ...reasoning.slice(0, -1).map((_, i) => ({ source: `s${i}`, target: `s${i + 1}` })),
    { source: `s${reasoning.length - 1}`, target: "dx" },
    { source: "dx", target: "tx" },
  ] : [];

  return (
    <div className="w-full min-h-[calc(100vh-4rem)] py-12 relative z-0 flex flex-col justify-start select-none bg-transparent">
      
      <div className="mx-auto max-w-7xl px-6 w-full relative z-10">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-6xl sm:text-7xl lg:text-8xl font-extrabold font-sans text-white tracking-tight leading-tight">
            {lang === "ar" ? (
              <>
                حلّل{" "}
                <span className="text-gradient font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-green-500">
                  نبتة
                </span>
              </>
            ) : (
              <>
                Analyze{" "}
                <span className="text-gradient font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-green-500">
                  a plant
                </span>
              </>
            )}
          </h1>
          <p className="text-zinc-200 mt-5 max-w-3xl mx-auto text-lg sm:text-xl md:text-2xl leading-relaxed font-medium">
            {lang === "ar"
              ? "ارفع صورة ورقة، واسأل بأي لغة، وتتبع الاستدلال داخل رسم معرفي زراعي حيّ."
              : "Upload a leaf, ask in any language, and trace the reasoning across a living agricultural knowledge graph."}
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-2 mt-12 items-stretch">
          {/* Left Card: Glassmorphism Upload Container */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="glass rounded-3xl p-6 flex flex-col justify-between w-full shadow-elegant bg-white/45 dark:bg-zinc-950/45 backdrop-blur-xl"
          >
            <div className="flex-1 flex flex-col justify-center w-full">
              <div
                onClick={() => inputRef.current?.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => { e.preventDefault(); onPick(e.dataTransfer.files?.[0]); }}
                className="relative border border-dashed border-stone-300 dark:border-stone-700 hover:border-emerald-600 transition-colors rounded-2xl aspect-video grid place-items-center cursor-pointer overflow-hidden bg-white/20 dark:bg-black/10 w-full"
              >
                {preview ? (
                  <img src={preview} alt="preview" className="absolute inset-0 size-full object-cover" />
                ) : (
                  <div className="text-center p-6 flex flex-col items-center">
                    <div className="mb-4">
                      <div className="size-16 rounded-full bg-emerald-500/10 dark:bg-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shadow-inner">
                        <Leaf className="size-8 fill-emerald-600/10 dark:fill-emerald-400/10" />
                      </div>
                    </div>
                    <div className="font-bold text-stone-700 dark:text-stone-200 text-sm sm:text-base">
                      {t("upload.drop")}
                    </div>
                    <div className="text-xs text-stone-500 mt-1.5 font-semibold">{t("upload.hint")}</div>
                  </div>
                )}
                <input ref={inputRef} type="file" accept="image/*" hidden onChange={e => onPick(e.target.files?.[0] ?? undefined)} />
              </div>
            </div>

            <button
              onClick={run}
              disabled={!preview || loading}
              className="mt-6 w-full rounded-2xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white font-bold py-3.5 text-sm sm:text-base shadow-glow hover:shadow-elegant transition-all duration-200 cursor-pointer inline-flex items-center justify-center gap-2 border-0 disabled:opacity-50"
            >
              {loading ? (
                <><Loader2 className="size-4 animate-spin" /> {lang === "ar" ? "جاري التحليل..." : "Analyzing..."}</>
              ) : (
                <><Sparkles className="size-4" /> {t("upload.btn")}</>
              )}
            </button>
          </motion.div>

          {/* Right Card: Glassmorphism Results Container */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="glass rounded-3xl p-6 min-h-[380px] flex flex-col justify-between relative overflow-hidden w-full shadow-elegant bg-white/45 dark:bg-zinc-950/45 backdrop-blur-xl"
          >
            <AnimatePresence mode="wait">
              {!result && !loading && (
                <motion.div key="empty" exit={{ opacity: 0 }} className="h-full min-h-[320px] grid place-items-center text-center text-stone-500 dark:text-stone-400 w-full">
                  <div className="flex flex-col items-center">
                    <div className="mb-4">
                      <div className="size-16 rounded-full bg-emerald-500/10 dark:bg-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shadow-inner">
                        <Leaf className="size-8 fill-emerald-600/10 dark:fill-emerald-400/10" />
                      </div>
                    </div>
                    <p className="text-sm font-semibold tracking-wide">{lang === "ar" ? "ستظهر نتائج الفحص والتقرير هنا." : "Results and reasoning will appear here."}</p>
                  </div>
                </motion.div>
              )}

              {loading && (
                <motion.div key="load" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3 w-full">
                  {(lang === "ar" ? [
                    "جاري رفع صورة الورقة...",
                    "جاري فحص بنية الأوراق والسمات البصرية...",
                    "جاري حساب نسب احتمالات الفئات...",
                    "جاري استرداد العلاج الموصى به..."
                  ] : [
                    "Uploading image asset...",
                    "Analyzing leaf structure & visual features...",
                    "Calculating category confidence scores...",
                    "Retrieving recommended treatments..."
                  ]).map((a, i) => (
                    <motion.div
                      key={a}
                      initial={{ x: -20, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      transition={{ delay: i * 0.25 }}
                      className="flex items-center gap-3 p-3.5 rounded-xl bg-white/40 dark:bg-black/20 border border-stone-200/50 dark:border-stone-850/50 shadow-sm"
                    >
                      <Loader2 className="size-4 animate-spin text-emerald-600" />
                      <span className="text-sm font-semibold text-stone-700 dark:text-stone-200">{a}</span>
                    </motion.div>
                  ))}
                </motion.div>
              )}

              {result && (
                <motion.div key="result" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5 w-full text-start">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-xs font-bold text-stone-500 uppercase tracking-widest">{t("result.disease")}</div>
                      <div className="flex items-center gap-2 mt-1.5">
                        <CheckCircle2 className="size-5 text-emerald-600" />
                        <h2 className="text-xl sm:text-2xl font-bold font-display text-stone-900 dark:text-stone-100 leading-tight">
                          {lang === "ar" ? result.diseaseAr : result.disease}
                        </h2>
                      </div>
                    </div>
                    {(() => {
                      const parsedCrop = getCropFromDisease(result.disease);
                      if (!parsedCrop) return null;
                      return (
                        <div className="size-14 shrink-0 rounded-2xl bg-emerald-600/10 border border-emerald-600/20 flex items-center justify-center shadow-md">
                          <CropVisual crop={parsedCrop} className="size-9" />
                        </div>
                      );
                    })()}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-2xl border border-stone-200/50 bg-white/40 dark:bg-black/20 p-4 shadow-sm">
                      <div className="text-xs font-bold text-stone-500 uppercase tracking-widest">{t("result.confidence")}</div>
                      <div className="mt-1 flex items-end gap-2">
                        <span className="text-2xl font-bold text-stone-900 dark:text-stone-100">{Math.round(result.confidence * 100)}%</span>
                      </div>
                      <div className="mt-2 h-1.5 rounded-full bg-stone-200 dark:bg-stone-800 overflow-hidden">
                        <motion.div className="h-full bg-emerald-600" initial={{ width: 0 }} animate={{ width: `${result.confidence * 100}%` }} transition={{ duration: 0.8 }} />
                      </div>
                    </div>
                    <div className="rounded-2xl border border-stone-200/50 bg-white/40 dark:bg-black/20 p-4 shadow-sm">
                      <div className="text-xs font-bold text-stone-500 uppercase tracking-widest">{t("result.severity")}</div>
                      <div className={`mt-2.5 inline-flex px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                        result.severity === "high" ? "bg-red-500/10 text-red-700 border border-red-200 dark:text-red-400" :
                        result.severity === "medium" ? "bg-amber-500/10 text-amber-700 border border-amber-200 dark:text-amber-400" : "bg-emerald-500/10 text-emerald-700 border border-emerald-200 dark:text-emerald-400"
                      }`}>{result.severity}</div>
                    </div>
                  </div>

                  <div>
                    <div className="text-xs font-bold text-stone-500 uppercase tracking-widest mb-1.5">{t("result.treatment")}</div>
                    <p className="text-sm leading-relaxed text-stone-700 dark:text-stone-300 font-medium">{lang === "ar" ? result.treatmentAr : result.treatment}</p>
                  </div>

                  <div>
                    {result.predictions && result.predictions.length > 0 ? (
                      <div>
                        <div className="text-xs font-bold text-stone-500 uppercase tracking-widest mb-3">
                          {t("result.reasoning")}
                        </div>
                        <div className="space-y-3">
                          {result.predictions.map((pred, i) => {
                            const isTop = i === 0;
                            const pct = Math.round(pred.confidence * 100);
                            return (
                              <motion.div
                                key={i}
                                initial={{ x: -10, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                transition={{ delay: i * 0.08 }}
                                className={`p-3.5 rounded-2xl border bg-white/40 dark:bg-black/25 flex flex-col gap-2 ${
                                  isTop 
                                    ? "border-emerald-500/30 dark:border-emerald-500/20 shadow-sm shadow-emerald-500/5" 
                                    : "border-stone-200/50 dark:border-stone-850/50"
                                }`}
                              >
                                <div className="flex justify-between items-center">
                                  <span className={`text-sm font-bold ${
                                    isTop ? "text-stone-900 dark:text-stone-100" : "text-stone-600 dark:text-stone-400"
                                  }`}>
                                    {lang === "ar" ? pred.diseaseAr : pred.disease}
                                  </span>
                                  <span className={`text-sm font-extrabold ${
                                    isTop ? "text-emerald-600 dark:text-emerald-400" : "text-stone-500 dark:text-stone-400"
                                  }`}>
                                    {pct}%
                                  </span>
                                </div>
                                <div className="h-2 w-full rounded-full bg-stone-200/60 dark:bg-stone-800/80 overflow-hidden">
                                  <motion.div 
                                    className={`h-full rounded-full ${
                                      isTop ? "bg-emerald-500" : "bg-stone-400 dark:bg-stone-600"
                                    }`}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${pct}%` }}
                                    transition={{ duration: 0.8, delay: i * 0.1 }}
                                  />
                                </div>
                              </motion.div>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div className="text-xs font-bold text-stone-500 uppercase tracking-widest mb-2">{t("result.reasoning")}</div>
                        <ol className="space-y-2">
                          {reasoning.map((r, i) => (
                            <motion.li
                              key={i}
                              initial={{ x: -10, opacity: 0 }}
                              animate={{ x: 0, opacity: 1 }}
                              transition={{ delay: i * 0.1 }}
                              className="flex gap-3 p-3 rounded-xl bg-white/40 dark:bg-black/20 border border-stone-200/50 dark:border-stone-850/50"
                            >
                              <span className="size-6 grid place-items-center rounded-full bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-xs font-bold shrink-0">{i + 1}</span>
                              <div className="text-sm">
                                <div className="font-bold text-stone-900 dark:text-stone-100">{r.step}</div>
                                <div className="text-stone-500 dark:text-stone-400 text-xs font-semibold">{r.node}</div>
                              </div>
                            </motion.li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>

        {result && result.viz_url && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mt-12 relative">
            <h3 className="font-display font-bold text-stone-900 dark:text-stone-100 text-lg mb-3 drop-shadow-sm">
              {lang === "ar" ? "خرائط التفعيل المرئية (Feature Maps)" : "Model Interpretability (Feature Maps)"}
            </h3>
            <div className="p-2 glass rounded-3xl overflow-hidden flex justify-center bg-white/60 dark:bg-zinc-950/60 shadow-elegant">
              <img src={result.viz_url} alt="Model Interpretability" className="w-full h-auto object-contain max-h-[800px] rounded-2xl bg-white/50 dark:bg-zinc-900 shadow-inner" />
            </div>
          </motion.div>
        )}

        {result && (result.report_html || result.report_en || result.report_ar) && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mt-12 relative w-full">
            <h3 className="font-display font-bold text-stone-900 dark:text-stone-100 text-lg mb-3 drop-shadow-sm">
              {lang === "ar" ? "تقرير النظام الخبير" : "Expert System Report"}
            </h3>
            <div className="glass rounded-3xl overflow-hidden bg-white/60 dark:bg-zinc-950/60 shadow-elegant p-0">
              {result.report_html ? (
                <iframe 
                  srcDoc={result.report_html} 
                  className="w-full min-h-[600px] border-none rounded-3xl"
                  title="Expert System Report"
                />
              ) : (
                <div className="p-6">
                  <div 
                    className="prose prose-stone dark:prose-invert prose-emerald max-w-none prose-headings:font-display prose-a:text-emerald-600 w-full"
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
    </div>
  );
}
