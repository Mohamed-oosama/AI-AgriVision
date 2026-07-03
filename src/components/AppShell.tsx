import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Home, LayoutDashboard, Upload, Network, History, Settings, Moon, Sun, Languages, Leaf, Sprout, FlaskConical, Bug, ChevronDown, MessageSquare, LineChart, ShieldAlert } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { useTheme } from "@/lib/theme";

const nav = [
  { to: "/", icon: Home, k: "nav.home" as const },
  { to: "/analyze", icon: Upload, k: "nav.analyze" as const },
  { to: "/chat", icon: MessageSquare, k: "nav.chat" as const },
  { to: "/soil", icon: FlaskConical, k: "nav.soil" as const },
  { to: "/yield", icon: LineChart, k: "nav.yield" as const },
  { to: "/ews", icon: ShieldAlert, k: "nav.ews" as const },
  { to: "/dashboard", icon: LayoutDashboard, k: "nav.dashboard" as const },
];

export function AppShell() {
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const path = useRouterState({ select: s => s.location.pathname });

  const isAnalyze = path === "/analyze";
  const isHome = path === "/";
  const isChat = path === "/chat";
  const isSoil = path === "/soil";
  const isYield = path === "/yield";
  const isEws = path === "/ews";

  let bgImage = "";
  if (isAnalyze) bgImage = "url('/analyze_custom_bg.jpg')";
  else if (isSoil || isYield || isEws) bgImage = "url('/soil_custom_bg.jpg')";
  else if (isChat) bgImage = "url('/chat_custom_bg.jpg')";
  else if (isHome) bgImage = "url('/farm_hero_bg.png')";

  return (
    <div className="min-h-screen flex flex-col relative z-0 overflow-hidden">
      {bgImage && (
        <div 
          className={`fixed inset-0 bg-cover bg-center -z-20 pointer-events-none transition-all duration-500 ${
            (isChat || isSoil || isAnalyze || isYield || isEws)
              ? "opacity-100 dark:opacity-100"
              : "opacity-100 dark:opacity-65"
          }`}
          style={{ backgroundImage: bgImage }}
        />
      )}

      {/* Landing page gradient overlay */}
      {isHome && (
        <div className="fixed inset-0 bg-gradient-to-b from-black/80 via-emerald-950/45 to-background dark:from-black/90 dark:via-black/75 dark:to-zinc-950 -z-15 pointer-events-none" />
      )}

      {/* Premium Dotted Grid Overlay */}
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(oklch(0.55_0.16_152_/_0.06)_1px,transparent_1px)] [background-size:32px_32px] opacity-50 dark:opacity-30" />

      {/* Multi-layered Background Glows for Color Depth */}
      <div className="fixed top-[10%] left-0 w-80 h-80 -z-10 bg-amber-500/6 dark:bg-amber-500/3 blur-[100px] rounded-full" />
      <div className="fixed bottom-0 right-0 w-[500px] h-[500px] -z-10 bg-emerald-500/10 dark:bg-emerald-900/3 blur-[130px] rounded-full" />
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl aspect-square -z-10 gradient-mesh opacity-50 blur-[130px] rounded-full mix-blend-screen dark:mix-blend-lighten animate-rotate-mesh" />

      {/* Abstract constellation network SVG background */}
      <svg className="fixed inset-0 size-full -z-10 opacity-20 dark:opacity-10 pointer-events-none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="network-grad" x1="0" y1="0" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.15" />
            <stop offset="100%" stopColor="var(--color-success)" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        
        {/* Draw constellation connections */}
        <path d="M 100,250 L 250,150 L 400,200 L 300,350 L 150,300 Z" fill="none" stroke="url(#network-grad)" strokeWidth="1.5" />
        <path d="M 250,150 L 300,350 M 400,200 L 150,300" fill="none" stroke="url(#network-grad)" strokeWidth="1" strokeDasharray="3 3" />
        
        <path d="M 850,650 L 1000,550 L 1150,600 L 1050,750 L 900,700 Z" fill="none" stroke="url(#network-grad)" strokeWidth="1.5" />
        <path d="M 1000,550 L 1050,750 M 1150,600 L 900,700" fill="none" stroke="url(#network-grad)" strokeWidth="1" strokeDasharray="3 3" />
        
        {/* Network Connection Nodes */}
        <g fill="var(--color-primary)" fillOpacity="0.4">
          <circle cx="100" cy="250" r="4" />
          <circle cx="250" cy="150" r="5" className="animate-pulse" />
          <circle cx="400" cy="200" r="4" />
          <circle cx="300" cy="350" r="6" />
          <circle cx="150" cy="300" r="5" />
          
          <circle cx="850" cy="650" r="4" className="animate-pulse" />
          <circle cx="1000" cy="550" r="5" />
          <circle cx="1150" cy="600" r="4" />
          <circle cx="1050" cy="750" r="6" />
          <circle cx="900" cy="700" r="5" />
        </g>
        
        {/* Abstract network arcs/curves */}
        <path d="M 100,250 Q 500,50 1000,550" fill="none" stroke="url(#network-grad)" strokeWidth="1.5" />
        <path d="M 150,300 Q 600,600 1050,750" fill="none" stroke="url(#network-grad)" strokeWidth="1" strokeDasharray="5 5" />
      </svg>

      {/* Floating Agricultural Details in the Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10 select-none">
        {/* Leaf 1 - top left */}
        <motion.div
          animate={{ y: [0, -12, 0], rotate: [15, 20, 15] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-[10%] left-[8%] text-emerald-500/15 dark:text-emerald-400/5 hidden md:block"
        >
          <Leaf className="size-24 -rotate-12" strokeWidth={0.8} />
        </motion.div>

        {/* Sprout 1 - top right */}
        <motion.div
          animate={{ y: [0, 10, 0], rotate: [-10, -5, -10] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-[15%] right-[10%] text-emerald-500/15 dark:text-emerald-400/5 hidden md:block"
        >
          <Sprout className="size-20" strokeWidth={0.8} />
        </motion.div>

        {/* Leaf 2 - bottom left */}
        <motion.div
          animate={{ y: [0, 15, 0], rotate: [45, 50, 45] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          className="absolute bottom-[15%] left-[12%] text-emerald-500/15 dark:text-emerald-400/5 hidden md:block"
        >
          <Leaf className="size-28" strokeWidth={0.6} />
        </motion.div>

        {/* Sprout 2 - bottom right */}
        <motion.div
          animate={{ y: [0, -15, 0], rotate: [-30, -35, -30] }}
          transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
          className="absolute bottom-[10%] right-[15%] text-emerald-500/15 dark:text-emerald-400/5 hidden md:block"
        >
          <Sprout className="size-24" strokeWidth={0.8} />
        </motion.div>

        {/* Tiny floating leaves */}
        <div className="absolute top-[40%] left-[20%] text-emerald-500/8 dark:text-emerald-400/3 hidden md:block">
          <Leaf className="size-10 rotate-45" strokeWidth={1} />
        </div>
        <div className="absolute bottom-[40%] right-[22%] text-emerald-500/8 dark:text-emerald-400/3 hidden md:block">
          <Leaf className="size-12 -rotate-12" strokeWidth={1} />
        </div>

        {/* Floating Sparks/Particles */}
        <div className="absolute top-[25%] left-[15%] w-2 h-2 rounded-full bg-emerald-400/40 animate-ping duration-[3s]" />
        <div className="absolute bottom-[35%] right-[18%] w-3 h-3 rounded-full bg-emerald-400/30 animate-pulse duration-[4s]" />
        <div className="absolute top-[50%] right-[30%] w-2 h-2 rounded-full bg-emerald-400/20 animate-ping duration-[5s]" />
      </div>
      <header className="sticky top-3 z-50 mx-auto w-[95vw] max-w-7xl glass rounded-2xl border shadow-lg transition-all duration-300">
        <div className="flex items-center justify-between px-6 h-14">
          <Link to="/" className="flex items-center gap-2 font-display font-bold text-lg">
            <span className="size-9 grid place-items-center rounded-xl gradient-primary shadow-glow">
              <Leaf className="size-5 text-primary-foreground" />
            </span>
            <span className="hidden sm:inline">AI <span className="text-gradient">AgriVision</span></span>
          </Link>

          <nav className="hidden lg:flex items-center gap-0.5 xl:gap-1">
            {nav.map(n => {
              const active = path === n.to;
              return (
                <Link key={n.to} to={n.to}
                  className={`relative px-3 py-2 rounded-lg text-sm transition-colors ${active ? "text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                  {active && (
                    <motion.span layoutId="navpill" className="absolute inset-0 bg-secondary rounded-lg -z-10"
                      transition={{ type: "spring", stiffness: 400, damping: 30 }} />
                  )}
                  {t(n.k)}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-1">
            <button onClick={() => setLang(lang === "en" ? "ar" : "en")}
              className="size-9 grid place-items-center rounded-lg hover:bg-secondary transition-colors" aria-label="language">
              <Languages className="size-4" />
              <span className="sr-only">lang</span>
            </button>
            <span className="text-xs font-medium text-muted-foreground px-1">{lang.toUpperCase()}</span>
            <button onClick={toggle} className="size-9 grid place-items-center rounded-lg hover:bg-secondary transition-colors" aria-label="theme">
              {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </button>
          </div>
        </div>
        {/* mobile nav */}
        <nav className="lg:hidden flex items-center gap-1 overflow-x-auto px-3 pb-2 -mt-1 custom-scrollbar">
          {nav.map(n => {
            const active = path === n.to;
            return (
              <Link key={n.to} to={n.to}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs whitespace-nowrap border ${active ? "bg-primary text-primary-foreground border-transparent" : "border-border text-muted-foreground"}`}>
                <n.icon className="size-3.5" /> {t(n.k)}
              </Link>
            );
          })}
        </nav>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t mt-auto bg-background/50">
        <div className="mx-auto max-w-7xl px-6 py-4 text-sm text-muted-foreground flex flex-col sm:flex-row items-center justify-between gap-4 w-full relative">
          <span className="font-medium">© {new Date().getFullYear()} AI AgriVision</span>

          <details className="group [&_summary::-webkit-details-marker]:hidden">
            <summary className="cursor-pointer font-display flex items-center gap-1.5 outline-none hover:text-foreground transition-colors font-medium text-sm">
              <span className="text-base">🌱</span> تعليمات الاستخدام (Usage)
            </summary>
            
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-[95vw] max-w-6xl bg-background/95 backdrop-blur-2xl border shadow-2xl rounded-3xl p-6 z-50 cursor-auto text-start text-sm text-foreground space-y-6">
              <div className="p-4 rounded-xl bg-warning/10 border border-warning/20">
                <h3 className="font-semibold flex items-center gap-2 text-warning-foreground text-sm">
                  <span className="text-lg">⚠️</span> شروط الصورة المرفوعة
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-foreground">
                  يجب أن تكون الصورة واضحة وذات جودة عالية للجزء المريض من النبات فقط.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Nutrient Deficiencies */}
                <div className="bg-background/50 rounded-2xl p-5 border shadow-sm flex flex-col h-[350px]">
                  <h3 className="font-bold text-primary mb-3 pb-3 border-b flex items-center gap-3 text-start text-base">
                    <div className="p-2 bg-primary/10 rounded-lg text-primary"><FlaskConical className="size-5" /></div>
                    <div>Nutrient Deficiencies<br/><span className="text-xs font-normal text-muted-foreground">نقص العناصر الغذائية</span></div>
                  </h3>
                  <ul className="flex flex-col text-xs space-y-0 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Citrus Nutrient Deficiency</span><span className="text-muted-foreground mt-0.5">اصفرار أوراق الحمضيات</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Maize Nitrogen Deficiency</span><span className="text-muted-foreground mt-0.5">نقص النيتروجين في الذرة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Maize Phosphorus Deficiency</span><span className="text-muted-foreground mt-0.5">نقص الفوسفور في الذرة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Maize Potassium Deficiency</span><span className="text-muted-foreground mt-0.5">نقص البوتاسيوم في الذرة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Maize Zinc Deficiency</span><span className="text-muted-foreground mt-0.5">نقص الزنك في الذرة</span></li>
                  </ul>
                </div>

                {/* Plant Diseases */}
                <div className="bg-background/50 rounded-2xl p-5 border shadow-sm flex flex-col h-[350px]">
                  <h3 className="font-bold text-destructive mb-3 pb-3 border-b flex items-center gap-3 text-start text-base">
                    <div className="p-2 bg-destructive/10 rounded-lg text-destructive"><Leaf className="size-5" /></div>
                    <div>Plant Diseases<br/><span className="text-xs font-normal text-muted-foreground">أمراض النباتات</span></div>
                  </h3>
                  <ul className="flex flex-col text-xs space-y-0 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Bacterial Blight</span><span className="text-muted-foreground mt-0.5">اللفحة البكتيرية للكسافا</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Brown Streak</span><span className="text-muted-foreground mt-0.5">مرض الخط البني في الكسافا</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Green Mottle</span><span className="text-muted-foreground mt-0.5">التبقع الأخضر في الكسافا</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Healthy</span><span className="text-muted-foreground mt-0.5">كسافا سليمة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Mosaic Disease</span><span className="text-muted-foreground mt-0.5">مرض موزايك الكسافا</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Citrus Canker Disease</span><span className="text-muted-foreground mt-0.5">تقرحات الحمضيات</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Healthy Orange Leaf</span><span className="text-muted-foreground mt-0.5">ورقة برتقال سليمة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Apple Healthy</span><span className="text-muted-foreground mt-0.5">تفاح سليم</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Corn Common Rust</span><span className="text-muted-foreground mt-0.5">الصدأ الشائع في الذرة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Corn Healthy</span><span className="text-muted-foreground mt-0.5">ذرة سليمة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Corn Northern Leaf Blight</span><span className="text-muted-foreground mt-0.5">اللفحة الشمالية للذرة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Grape Black Rot</span><span className="text-muted-foreground mt-0.5">العفن الأسود في العنب</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Grape Esca</span><span className="text-muted-foreground mt-0.5">مرض الإيسكا في العنب</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Grape Leaf Blight</span><span className="text-muted-foreground mt-0.5">لفحة أوراق العنب</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Orange Huanglongbing</span><span className="text-muted-foreground mt-0.5">مرض اخضرار الحمضيات</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Peach Bacterial Spot</span><span className="text-muted-foreground mt-0.5">التبقع البكتيري في الخوخ</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Bell Pepper Healthy</span><span className="text-muted-foreground mt-0.5">فلفل رومي سليم</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Rice Healthy</span><span className="text-muted-foreground mt-0.5">أرز سليم</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Rice Leaf Blast</span><span className="text-muted-foreground mt-0.5">لفحة أوراق الأرز</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Rice Sheath Blight</span><span className="text-muted-foreground mt-0.5">لفحة غمد الأرز</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Rice Tungro</span><span className="text-muted-foreground mt-0.5">مرض التنجرو في الأرز</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Soybean Healthy</span><span className="text-muted-foreground mt-0.5">فول صويا سليم</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Squash Powdery Mildew</span><span className="text-muted-foreground mt-0.5">البياض الدقيقي في القرع</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Tomato Blight</span><span className="text-muted-foreground mt-0.5">لفحة الطماطم</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Tomato Healthy</span><span className="text-muted-foreground mt-0.5">طماطم سليمة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Tomato Yellow Leaf Curl</span><span className="text-muted-foreground mt-0.5">تجعد واصفرار أوراق الطماطم</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Wheat Smut</span><span className="text-muted-foreground mt-0.5">التفحم في القمح</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Wheat Yellow Rust</span><span className="text-muted-foreground mt-0.5">الصدأ الأصفر في القمح</span></li>
                  </ul>
                </div>

                {/* Plant Pests */}
                <div className="bg-background/50 rounded-2xl p-5 border shadow-sm flex flex-col h-[350px]">
                  <h3 className="font-bold text-amber-600 mb-3 pb-3 border-b flex items-center gap-3 text-start text-base">
                    <div className="p-2 bg-amber-600/10 rounded-lg text-amber-600"><Bug className="size-5" /></div>
                    <div>Plant Pests<br/><span className="text-xs font-normal text-muted-foreground">الآفات الحشرية</span></div>
                  </h3>
                  <ul className="flex flex-col text-xs space-y-0 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Aphids</span><span className="text-muted-foreground mt-0.5">حشرة المنّ</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Army Worm</span><span className="text-muted-foreground mt-0.5">دودة الحشد</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Asiatic Rice Borer</span><span className="text-muted-foreground mt-0.5">حفار الأرز الآسيوي</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Blister Beetle</span><span className="text-muted-foreground mt-0.5">الخنفساء الفقاعية</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Corn Borer</span><span className="text-muted-foreground mt-0.5">حفار الذرة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Leafhopper</span><span className="text-muted-foreground mt-0.5">نطاط الأوراق</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Limacodidae</span><span className="text-muted-foreground mt-0.5">يرقات القواقع الشوكية</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Locustoidea</span><span className="text-muted-foreground mt-0.5">الجراد</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Lycorma Delicatula</span><span className="text-muted-foreground mt-0.5">الذبابة الفانوسية المرقطة</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Miridae</span><span className="text-muted-foreground mt-0.5">بقّ النبات</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Mole Cricket</span><span className="text-muted-foreground mt-0.5">صرصار الخلد</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Prodenia Litura</span><span className="text-muted-foreground mt-0.5">دودة ورق القطن</span></li>
                    <li className="flex flex-col items-start text-start py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Xylotrechus</span><span className="text-muted-foreground mt-0.5">حفار الساق الخشبي</span></li>
                  </ul>
                </div>
              </div>
            </div>
          </details>

        </div>
      </footer>
    </div>
  );
}
