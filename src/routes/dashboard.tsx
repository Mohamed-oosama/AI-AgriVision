import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Activity, Leaf, AlertTriangle, Target, ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useI18n } from "@/lib/i18n";
import { getHistory, type Diagnosis } from "@/lib/ai-mock";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, PieChart, Pie, Cell } from "recharts";

export const Route = createFileRoute("/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — AgriMind.AI" }, { name: "description", content: "Live agricultural AI dashboard." }] }),
  component: Dashboard,
});

const scanData = [
  { name: "Week 1", scans: 12 },
  { name: "Week 2", scans: 19 },
  { name: "Week 3", scans: 15 },
  { name: "Week 4", scans: 27 },
  { name: "Week 5", scans: 22 },
  { name: "Week 6", scans: 34 },
  { name: "Week 7", scans: 45 },
];

const healthData = [
  { name: "Healthy", value: 55, color: "#10b981" },
  { name: "Diseased", value: 30, color: "#f43f5e" },
  { name: "Nutrient Deficient", value: 15, color: "#f59e0b" },
];

function getDiseaseEmoji(disease: string): string {
  const d = disease.toLowerCase();
  if (d.includes("healthy")) return "🌿";
  if (d.includes("tomato")) return "🍅";
  if (d.includes("wheat")) return "🌾";
  if (d.includes("corn") || d.includes("maize")) return "🌽";
  if (d.includes("grape")) return "🍇";
  if (d.includes("orange") || d.includes("citrus")) return "🍊";
  if (d.includes("peach")) return "🍑";
  if (d.includes("pepper")) return "🫑";
  if (d.includes("rice")) return "🌾";
  if (d.includes("potato")) return "🥔";
  if (d.includes("cassava")) return "🍠";
  if (d.includes("soybean")) return "🫘";
  if (d.includes("squash")) return "🎃";
  if (d.includes("pest") || d.includes("aphid") || d.includes("worm") || d.includes("beetle") || d.includes("borer") || d.includes("cricket") || d.includes("locust") || d.includes("infestation")) return "🐛";
  return "🌱";
}

function Dashboard() {
  const { t, lang } = useI18n();
  const [hist, setHist] = useState<Diagnosis[]>([]);
  useEffect(() => setHist(getHistory()), []);

  const total = hist.length;
  const healthy = hist.filter(h => h.disease.toLowerCase().includes("healthy")).length;
  const diseased = total - healthy;
  const avg = total ? Math.round((hist.reduce((s, h) => s + h.confidence, 0) / total) * 100) : 0;

  const stats = [
    { k: "dash.scans" as const, v: total, icon: Activity, color: "from-chart-1 to-primary-glow" },
    { k: "dash.healthy" as const, v: healthy, icon: Leaf, color: "from-success to-primary-glow" },
    { k: "dash.diseased" as const, v: diseased, icon: AlertTriangle, color: "from-destructive to-warning" },
    { k: "dash.acc" as const, v: `${avg}%`, icon: Target, color: "from-chart-3 to-chart-5" },
  ];

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold">{t("dash.title")}</h1>
          <p className="text-muted-foreground mt-1">Overview of your agricultural diagnoses.</p>
        </div>
        <Link to="/analyze" className="inline-flex items-center gap-2 rounded-xl gradient-primary text-primary-foreground px-5 py-2.5 text-sm font-semibold shadow-glow">
          {t("hero.cta")} <ArrowRight className="size-4" />
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mt-8">
        {stats.map((s, i) => (
          <motion.div key={s.k} initial={{ y: 16, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: i * 0.06 }}
            className="glass rounded-2xl p-5 relative overflow-hidden">
            <div className={`absolute -top-10 -right-10 size-32 rounded-full bg-gradient-to-br ${s.color} opacity-20 blur-2xl`} />
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{t(s.k)}</span>
              <s.icon className="size-4 text-muted-foreground" />
            </div>
            <div className="mt-3 text-3xl font-bold font-display">{s.v}</div>
          </motion.div>
        ))}
      </div>

      {/* Visual Analytics Charts Section */}
      <div className="grid gap-5 lg:grid-cols-3 mt-8">
        <motion.div 
          initial={{ y: 16, opacity: 0 }} 
          animate={{ y: 0, opacity: 1 }} 
          transition={{ delay: 0.1 }}
          className="lg:col-span-2 glass rounded-2xl p-6 relative overflow-hidden"
        >
          <h2 className="font-display font-semibold text-lg mb-4">{lang === "ar" ? "نشاط فحص المحاصيل أسبوعياً" : "Weekly Crop Scan Activity"}</h2>
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={scanData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorScans" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: "rgba(255, 255, 255, 0.85)", border: "none", borderRadius: "12px", boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)" }} />
                <Area type="monotone" dataKey="scans" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#colorScans)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div 
          initial={{ y: 16, opacity: 0 }} 
          animate={{ y: 0, opacity: 1 }} 
          transition={{ delay: 0.2 }}
          className="glass rounded-2xl p-6 relative overflow-hidden flex flex-col justify-between"
        >
          <h2 className="font-display font-semibold text-lg mb-4">{lang === "ar" ? "توزيع صحة المحاصيل" : "Crop Health Distribution"}</h2>
          <div className="h-[180px] w-full relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={healthData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {healthData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold font-display">85%</span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{lang === "ar" ? "الدقة العامة" : "Avg. Accuracy"}</span>
            </div>
          </div>
          <div className="flex justify-around mt-4 text-xs font-semibold">
            {healthData.map((d) => (
              <div key={d.name} className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full" style={{ backgroundColor: d.color }} />
                <span className="text-muted-foreground">{lang === "ar" ? (d.name === "Healthy" ? "سليم" : d.name === "Diseased" ? "مريض" : "نقص مغذيات") : d.name}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      <div className="mt-8">
        <div className="glass rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-display font-semibold text-lg">Recent activity</h2>
          </div>
          <div className="mt-4 divide-y">
            {hist.slice(0, 5).map(h => (
              <div key={h.id} className="flex items-center gap-4 py-3">
                <div className="size-12 rounded-xl bg-emerald-500/10 dark:bg-emerald-500/20 border border-emerald-500/25 flex items-center justify-center text-2xl shadow-inner shrink-0">
                  {getDiseaseEmoji(h.disease)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{lang === "ar" ? h.diseaseAr : h.disease}</div>
                  <div className="text-xs text-muted-foreground">{new Date(h.createdAt || Date.now()).toLocaleString()}</div>
                </div>
                <span className="text-sm font-semibold text-primary">{Math.round(h.confidence * 100)}%</span>
              </div>
            ))}
            {!hist.length && <div className="text-sm text-muted-foreground py-8 text-center">{t("history.empty")}</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
