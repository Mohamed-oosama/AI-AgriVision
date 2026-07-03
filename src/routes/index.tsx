import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, Leaf, Sprout, Network, Brain, ShieldAlert, Activity, Send, MessageSquare, FlaskConical, LineChart } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { RealisticLeafSVG } from "../components/RealisticLeafSVG";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AI AgriVision — Explainable Crop Diagnosis" },
      { name: "description", content: "Upload a leaf, ask in Arabic or English, and trace AI reasoning across an agronomy knowledge graph." },
    ],
  }),
  component: Landing,
});

const LeafNeuralSVG = () => (
  <div className="relative w-full aspect-square max-w-[360px] lg:max-w-[420px] mx-auto">
    <div className="absolute inset-0 bg-emerald-500/15 rounded-full blur-[80px] -z-10 animate-pulse" style={{ animationDuration: '4s' }} />
    <motion.div
      animate={{ y: [0, -12, 0] }}
      transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      className="glass rounded-3xl p-6 border border-border/50 shadow-elegant relative overflow-hidden h-full flex items-center justify-center bg-white/20 dark:bg-zinc-950/20 backdrop-blur-md"
    >
      <svg className="w-full h-full max-h-[320px]" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          {/* Glowing Filters for Cybernetic Feel */}
          <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          
          <linearGradient id="leaf-grad" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#059669" />
            <stop offset="50%" stopColor="#10b981" />
            <stop offset="100%" stopColor="#84cc16" />
          </linearGradient>
          
          <linearGradient id="glow-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#06b6d4" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>
        </defs>
        
        {/* Background Tech Radar Rings & Grids */}
        <circle cx="100" cy="100" r="85" stroke="rgba(16, 185, 129, 0.08)" strokeWidth="1" strokeDasharray="5 10" />
        <circle cx="100" cy="100" r="70" stroke="rgba(16, 185, 129, 0.05)" strokeWidth="1.5" />
        <circle cx="100" cy="100" r="50" stroke="rgba(16, 185, 129, 0.04)" strokeWidth="1" strokeDasharray="2 5" />
        
        {/* Axis Crosshair lines for sci-fi look */}
        <line x1="100" y1="10" x2="100" y2="190" stroke="rgba(16, 185, 129, 0.03)" strokeWidth="1" />
        <line x1="10" y1="100" x2="190" y2="100" stroke="rgba(16, 185, 129, 0.03)" strokeWidth="1" />
        
        {/* Leaf Outline Shape (Thick Glowing Outer Stroke) */}
        <path d="M 100,180 C 35,145 25,75 100,15 C 175,75 165,145 100,180 Z" stroke="url(#leaf-grad)" strokeWidth="3.5" strokeLinecap="round" filter="url(#glow)" opacity="0.85" />
        
        {/* Leaf Outline Thin Inner Accents */}
        <path d="M 100,177 C 42,143 32,78 100,20 C 168,78 158,143 100,177 Z" stroke="#ffffff" strokeWidth="0.8" strokeLinecap="round" opacity="0.25" />
        
        {/* Main Leaf Stem with moving dashed light pulses */}
        <path d="M 100,180 L 100,15" stroke="url(#leaf-grad)" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
        <path d="M 100,180 L 100,15" stroke="#ffffff" strokeWidth="2" strokeDasharray="10 30" strokeDashoffset="0" strokeLinecap="round" opacity="0.85" filter="url(#glow)">
          <animate attributeName="strokeDashoffset" values="0; -80" dur="2.5s" repeatCount="indefinite" />
        </path>
        
        {/* Neural Network Circuit Connections */}
        <g stroke="url(#glow-grad)" strokeWidth="1.5" opacity="0.6">
          {/* Constellation Circuit Paths */}
          <path d="M 100,140 L 55,115 M 55,115 L 65,75 M 65,75 L 100,55" />
          <path d="M 100,140 L 145,115 M 145,115 L 135,75 M 135,75 L 100,55" />
          <path d="M 55,115 L 100,95 M 145,115 L 100,95 M 100,95 L 65,75 M 100,95 L 135,75" />
          <path d="M 100,55 L 100,15" />
        </g>
        
        {/* Digital Grid Accents (dotted) */}
        <g stroke="#10b981" strokeWidth="1" opacity="0.3" strokeDasharray="3 3">
          <line x1="55" y1="115" x2="145" y2="115" />
          <line x1="65" y1="75" x2="135" y2="75" />
        </g>
        
        {/* Animated Light Pulses flowing through circuits */}
        <path d="M 100,140 L 55,115 L 65,75 L 100,55" stroke="#ffffff" strokeWidth="1.8" strokeDasharray="6 24" opacity="0.9" strokeLinecap="round" filter="url(#glow)">
          <animate attributeName="strokeDashoffset" values="0; -60" dur="1.8s" repeatCount="indefinite" />
        </path>
        <path d="M 100,140 L 145,115 L 135,75 L 100,55" stroke="#ffffff" strokeWidth="1.8" strokeDasharray="6 24" opacity="0.9" strokeLinecap="round" filter="url(#glow)">
          <animate attributeName="strokeDashoffset" values="0; 60" dur="1.8s" repeatCount="indefinite" />
        </path>
        
        {/* Cyber Nodes (Concentric layered circles for deep glows) */}
        {/* Bottom Node */}
        <g filter="url(#glow)">
          <circle cx="100" cy="140" r="9" fill="#10b981" opacity="0.2">
            <animate attributeName="r" values="7;11;7" dur="2.4s" repeatCount="indefinite" />
          </circle>
          <circle cx="100" cy="140" r="4.5" fill="#10b981" />
          <circle cx="100" cy="140" r="1.5" fill="#ffffff" />
        </g>
        
        {/* Lower Left Node */}
        <g filter="url(#glow)">
          <circle cx="55" cy="115" r="8" fill="#f59e0b" opacity="0.2">
            <animate attributeName="r" values="6;10;6" dur="2.1s" repeatCount="indefinite" />
          </circle>
          <circle cx="55" cy="115" r="4" fill="#d97706" />
          <circle cx="55" cy="115" r="1.5" fill="#ffffff" />
        </g>
        
        {/* Lower Right Node */}
        <g filter="url(#glow)">
          <circle cx="145" cy="115" r="8" fill="#f59e0b" opacity="0.2">
            <animate attributeName="r" values="6;10;6" dur="2.6s" repeatCount="indefinite" />
          </circle>
          <circle cx="145" cy="115" r="4" fill="#d97706" />
          <circle cx="145" cy="115" r="1.5" fill="#ffffff" />
        </g>
        
        {/* Center core node ("Brain") */}
        <g filter="url(#glow)">
          <circle cx="100" cy="95" r="12" fill="#10b981" opacity="0.25">
            <animate attributeName="r" values="9;14;9" dur="2.8s" repeatCount="indefinite" />
          </circle>
          <circle cx="100" cy="95" r="6" fill="#059669" />
          <circle cx="100" cy="95" r="2.5" fill="#ffffff" />
        </g>
        
        {/* Upper Left Node */}
        <g filter="url(#glow)">
          <circle cx="65" cy="75" r="8" fill="#06b6d4" opacity="0.2">
            <animate attributeName="r" values="6;10;6" dur="2.3s" repeatCount="indefinite" />
          </circle>
          <circle cx="65" cy="75" r="4" fill="#0891b2" />
          <circle cx="65" cy="75" r="1.5" fill="#ffffff" />
        </g>
        
        {/* Upper Right Node */}
        <g filter="url(#glow)">
          <circle cx="135" cy="75" r="8" fill="#06b6d4" opacity="0.2">
            <animate attributeName="r" values="6;10;6" dur="2.7s" repeatCount="indefinite" />
          </circle>
          <circle cx="135" cy="75" r="4" fill="#0891b2" />
          <circle cx="135" cy="75" r="1.5" fill="#ffffff" />
        </g>
        
        {/* Upper Stem Node */}
        <g filter="url(#glow)">
          <circle cx="100" cy="55" r="9" fill="#10b981" opacity="0.2">
            <animate attributeName="r" values="7;11;7" dur="2.5s" repeatCount="indefinite" />
          </circle>
          <circle cx="100" cy="55" r="4.5" fill="#10b981" />
          <circle cx="100" cy="55" r="1.5" fill="#ffffff" />
        </g>
        
        {/* Apex Tip Node */}
        <g filter="url(#glow)">
          <circle cx="100" cy="15" r="7" fill="#84cc16" opacity="0.25">
            <animate attributeName="r" values="5;9;5" dur="3s" repeatCount="indefinite" />
          </circle>
          <circle cx="100" cy="15" r="3.5" fill="#65a30d" />
          <circle cx="100" cy="15" r="1" fill="#ffffff" />
        </g>
      </svg>
    </motion.div>
  </div>
);

function Landing() {
  const { t, lang } = useI18n();

  return (
    <div className="relative flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] w-full overflow-hidden bg-transparent">

      {/* Floating Sparkles Background Particles */}
      <div className="absolute top-[20%] left-[10%] w-2 h-2 rounded-full bg-emerald-400/40 animate-ping duration-[3s] -z-10" />
      <div className="absolute top-[50%] right-[15%] w-3 h-3 rounded-full bg-emerald-400/30 animate-pulse duration-[4s] -z-10" />

      {/* Hero Section Content */}
      <section className="relative mx-auto max-w-5xl px-6 pt-16 pb-28 md:pb-36 w-full z-10 text-center flex flex-col items-center">
        <motion.div
          initial="hidden"
          animate="visible"
          variants={{
            hidden: { opacity: 0 },
            visible: { opacity: 1, transition: { staggerChildren: 0.12 } }
          }}
          className="flex flex-col items-center"
        >

          {/* Title */}
          <motion.h1
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } }
            }}
            className="mt-6 text-4xl sm:text-6xl lg:text-7xl font-bold leading-[1.1] tracking-tight text-white font-display max-w-4xl"
          >
            {lang === "ar" ? (
              <>
                مستشارك الزراعي الذكي: احصل على{" "}
                <span className="text-gradient font-extrabold bg-gradient-to-r from-emerald-400 to-green-500">إجابات فورية لمشاكلك</span>
              </>
            ) : (
              <>
                Your Smart Agricultural Advisor: Get{" "}
                <span className="text-gradient font-extrabold bg-gradient-to-r from-emerald-400 to-green-500">Instant AI Answers</span>
              </>
            )}
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } }
            }}
            className="mt-6 text-base sm:text-lg lg:text-xl text-zinc-200 max-w-2xl leading-relaxed font-medium"
          >
            {lang === "ar"
              ? "دردش مع شات بوت الزراعي المدعم بالذكاء الاصطناعي للحصول على نصائح فورية حول الزراعة، الأمراض، المحاصيل والطقس."
              : "Chat with our AI agricultural assistant to get instant advice on farming, crop leaf diseases, fertilization, and weather."}
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            variants={{
              hidden: { opacity: 0, y: 15 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }
            }}
            className="mt-8 flex flex-wrap justify-center gap-4"
          >
            <Link
              to="/chat"
              className="group inline-flex items-center gap-2 rounded-2xl bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold px-8 py-4 text-sm sm:text-base shadow-glow hover:shadow-elegant transition-all hover:-translate-y-0.5 duration-200 cursor-pointer"
            >
              {lang === "ar" ? "ابدأ الدردشة الآن" : "Start Chatting Now"}
              <ArrowRight className="size-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              to="/analyze"
              className="inline-flex items-center gap-2 rounded-2xl border border-white/20 bg-white/10 backdrop-blur-md hover:bg-white/20 text-white font-semibold px-8 py-4 text-sm sm:text-base transition-all hover:-translate-y-0.5 duration-200 cursor-pointer"
            >
              {lang === "ar" ? "شخص أوراق المحصول" : "Diagnose Crop Leaves"}
            </Link>
          </motion.div>
        </motion.div>
      </section>

      <section className="-mt-16 sm:-mt-20 md:-mt-24 z-20 relative mx-auto max-w-5xl px-6 w-full mb-18">
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2">
          {[
            {
              title: lang === "ar" ? "تشخيص الأمراض" : "Disease Diagnosis",
              desc: lang === "ar" ? "شخّص أوراق المحاصيل بالرؤية الحاسوبية." : "Diagnose crop leaf diseases with computer vision AI.",
              icon: RealisticLeafSVG,
              to: "/analyze",
              color: "text-emerald-500"
            },
            {
              title: lang === "ar" ? "تحليل التربة الذكي" : "Soil Nutrient AI",
              desc: lang === "ar" ? "توصيات تسميد متوازنة وخلاطات NPK." : "Balanced NPK fertilizer recommendation plan.",
              icon: Sprout,
              to: "/soil",
              color: "text-amber-500"
            },
            {
              title: lang === "ar" ? "مستشار المحادثة" : "Chat AI Advisor",
              desc: lang === "ar" ? "اطرح الأسئلة واحصل على نصائح فورية." : "Ask questions and get instant agricultural advice.",
              icon: MessageSquare,
              to: "/chat",
              color: "text-blue-500"
            },
            {
              title: lang === "ar" ? "توقع المحصول" : "Crop Yield Explorer",
              desc: lang === "ar" ? "توقع كمية المحصول باستخدام الذكاء الاصطناعي بناءً على التربة والمناخ." : "Predict crop yield using AI based on soil, inputs, and climate.",
              icon: LineChart,
              to: "/yield",
              color: "text-purple-500"
            }
          ].map((feat, i) => {
            const Icon = feat.icon;
            return (
              <motion.div
                key={feat.title}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * i, duration: 0.5 }}
                className="group"
              >
                <Link to={feat.to} className="block glass rounded-3xl p-5 border border-border/60 hover:border-emerald-500/30 hover:shadow-elegant transition-all duration-300 bg-white/70 dark:bg-zinc-950/70 backdrop-blur-md cursor-pointer hover:-translate-y-1.5 h-full flex flex-col justify-between">
                  <div>
                    <div className={`size-11 rounded-2xl bg-secondary flex items-center justify-center ${feat.color} group-hover:scale-110 transition-transform shadow-soft`}>
                      <Icon className="size-5.5" />
                    </div>
                    <h3 className="font-display font-bold text-sm sm:text-base text-foreground mt-4">{feat.title}</h3>
                    <p className="text-muted-foreground text-xs mt-2 leading-relaxed">{feat.desc}</p>
                  </div>
                  <div className="mt-4 flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400 group-hover:underline">
                    {lang === "ar" ? "تصفح الأداة" : "Launch Tool"}
                    <ArrowRight className="size-3 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
