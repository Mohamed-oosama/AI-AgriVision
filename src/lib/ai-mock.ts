// Mock AI layer — swap with calls to your FastAPI backend (POST /analyze, etc.)
export type Diagnosis = {
  id: string;
  imageUrl: string;
  disease: string;
  diseaseAr: string;
  confidence: number;
  severity: "low" | "medium" | "high";
  treatment: string;
  treatmentAr: string;
  reasoning: { step: string; node: string }[];
  reasoningAr: { step: string; node: string }[];
  createdAt: number;
  predictions?: { disease: string; diseaseAr: string; confidence: number }[];
};

const SAMPLES = [
  {
    disease: "Tomato Late Blight", diseaseAr: "اللفحة المتأخرة في الطماطم",
    confidence: 0.93, severity: "high" as const,
    treatment: "Apply copper-based fungicide. Remove infected leaves. Improve air circulation and avoid overhead watering.",
    treatmentAr: "استخدم مبيداً فطرياً نحاسياً. أزل الأوراق المصابة. حسّن تهوية النبات وتجنّب الري العلوي.",
    reasoning: [
      { step: "Vision Agent", node: "Detected dark water-soaked lesions" },
      { step: "Graph-RAG", node: "Lesions → Phytophthora infestans" },
      { step: "Fusion Agent", node: "Cross-checked with humid conditions" },
      { step: "Decision Agent", node: "Late Blight (high severity)" },
    ],
    reasoningAr: [
      { step: "وكيل الرؤية", node: "اكتُشفت بقع داكنة مشبعة بالماء" },
      { step: "Graph-RAG", node: "بقع ← Phytophthora infestans" },
      { step: "وكيل الدمج", node: "تطابق مع ظروف الرطوبة" },
      { step: "وكيل القرار", node: "اللفحة المتأخرة (شدة عالية)" },
    ],
    predictions: [
      { disease: "Tomato Late Blight", diseaseAr: "اللفحة المتأخرة في الطماطم", confidence: 0.93 },
      { disease: "Tomato Early Blight", diseaseAr: "اللفحة المبكرة في الطماطم", confidence: 0.05 },
      { disease: "Tomato Septoria Leaf Spot", diseaseAr: "تبقع أوراق السبتوريا في الطماطم", confidence: 0.02 },
    ]
  },
  {
    disease: "Healthy Plant", diseaseAr: "نبات سليم",
    confidence: 0.97, severity: "low" as const,
    treatment: "No action required. Maintain regular watering schedule and monitor for changes.",
    treatmentAr: "لا حاجة لأي إجراء. حافظ على جدول الري المنتظم وراقب التغيرات.",
    reasoning: [
      { step: "Vision Agent", node: "Uniform green pigmentation" },
      { step: "Graph-RAG", node: "No disease pattern matched" },
      { step: "Decision Agent", node: "Healthy" },
    ],
    reasoningAr: [
      { step: "وكيل الرؤية", node: "تصبّغ أخضر منتظم" },
      { step: "Graph-RAG", node: "لا يوجد نمط مرض مطابق" },
      { step: "وكيل القرار", node: "سليم" },
    ],
    predictions: [
      { disease: "Healthy Plant", diseaseAr: "نبات سليم", confidence: 0.97 },
      { disease: "Tomato Early Blight", diseaseAr: "اللفحة المبكرة في الطماطم", confidence: 0.02 },
      { disease: "Tomato Bacterial Spot", diseaseAr: "التبقع البكتيري في الطماطم", confidence: 0.01 },
    ]
  },
  {
    disease: "Powdery Mildew", diseaseAr: "البياض الدقيقي",
    confidence: 0.86, severity: "medium" as const,
    treatment: "Spray with potassium bicarbonate or neem oil weekly. Prune dense foliage to improve airflow.",
    treatmentAr: "رشّ ببيكربونات البوتاسيوم أو زيت النيم أسبوعياً. قلّم الأوراق الكثيفة لتحسين التهوية.",
    reasoning: [
      { step: "Vision Agent", node: "White powdery patches detected" },
      { step: "Graph-RAG", node: "Patches → Erysiphales fungi" },
      { step: "Fusion Agent", node: "Confirmed by leaf curling" },
      { step: "Decision Agent", node: "Powdery Mildew (medium severity)" },
    ],
    reasoningAr: [
      { step: "وكيل الرؤية", node: "بقع دقيقة بيضاء" },
      { step: "Graph-RAG", node: "بقع ← فطريات Erysiphales" },
      { step: "وكيل الدمج", node: "تأكيد بتجعّد الأوراق" },
      { step: "وكيل القرار", node: "بياض دقيقي (شدة متوسطة)" },
    ],
    predictions: [
      { disease: "Powdery Mildew", diseaseAr: "البياض الدقيقي", confidence: 0.86 },
      { disease: "Healthy Plant", diseaseAr: "نبات سليم", confidence: 0.09 },
      { disease: "Leaf Mold", diseaseAr: "عفن الأوراق", confidence: 0.05 },
    ]
  },
];

export async function analyzeImage(imageUrl: string, _question?: string): Promise<Diagnosis> {
  await new Promise(r => setTimeout(r, 1400));
  const s = SAMPLES[Math.floor(Math.random() * SAMPLES.length)];
  return {
    id: crypto.randomUUID(), imageUrl, createdAt: Date.now(), ...s,
  };
}

const KEY = "agri-history";
export function saveHistory(d: Diagnosis) {
  if (typeof window === "undefined") return;
  const list = getHistory();
  const item = { ...d, createdAt: d.createdAt || Date.now() };
  list.unshift(item);
  localStorage.setItem(KEY, JSON.stringify(list.slice(0, 50)));
}
export function getHistory(): Diagnosis[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(KEY) ?? "[]"); } catch { return []; }
}
export function clearHistory() { if (typeof window !== "undefined") localStorage.removeItem(KEY); }
