import { createFileRoute } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";
import { motion, AnimatePresence } from "framer-motion";
import { Leaf, Send, Sparkles, User, Bot, Loader2, ArrowRight } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useI18n } from "@/lib/i18n";
import { RealisticLeafSVG } from "../components/RealisticLeafSVG";

export const Route = createFileRoute("/chat")({
  head: () => ({
    meta: [
      { title: "AI Chat Advisor — AI AgriVision" },
      { name: "description", content: "Chat with our explainable agricultural AI advisor." }
    ]
  }),
  component: ChatPage,
});

const chatResponseFn = createServerFn({ method: "POST" })
  .inputValidator((data: { message: string; history?: any[] }) => data)
  .handler(async ({ data }) => {
    const { message } = data;
    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        return (await response.json()) as { reply: string };
      }
    } catch (err) {
      console.warn('Chatbot gateway connection failed, using fallback mock response:', err);
    }

    // Fallback Mock System if Flask server is down
    const text = message.toLowerCase();
    let reply = "";
    let replyAr = "";

    if (
      text.includes("tomato") ||
      text.includes("طماطم") ||
      text.includes("yellow") ||
      text.includes("أصفر")
    ) {
      reply = `### Yellowing Tomato Leaves Diagnosis:
1. **Nitrogen Deficiency**: The oldest leaves at the bottom turn yellow first.
   * **Remedy**: Apply nitrogen-rich fertilizer.
2. **Watering Issues**: Overwatering or underwatering.
   * **Remedy**: Adjust watering to ensure 1-1.5 inches per week.
3. **Early Blight (Fungal)**: Yellow leaves with dark spots.
   * **Remedy**: Remove infected leaves, apply copper fungicide.`;
      replyAr = `### تشخيص اصفرار أوراق الطماطم:
1. **نقص النيتروجين**: تبدأ الأوراق القديمة في الأسفل بالتحول إلى اللون الأصفر أولاً.
   * **العلاج**: ضع سماداً غنياً بالنيتروجين أو شاي الكمبوست.
2. **مشاكل الري**: يسبب كل من الإفراط في الري ونقصه الاصفرار.
   * **العلاج**: اضبط الري لضمان 2.5-3.8 سم من الماء أسبوعياً.
3. **اللفحة المبكرة (فطرية)**: أوراق صفراء بها بقع داكنة.
   * **العلاج**: أزل الأوراق المصابة، ورش مبيداً فطرياً نحاسياً.`;
    } else if (
      text.includes("npk") ||
      text.includes("wheat") ||
      text.includes("قمح") ||
      text.includes("tillering") ||
      text.includes("إشطاء")
    ) {
      reply = `### Wheat Tillering NPK Recommendation:
* **Recommended NPK Ratio**: A typical base fertilization is **120:60:40 kg/ha** of N:P2O5:K2O.
* **Tillering Application**: Apply **50% of the total Nitrogen** as a top dressing during active tillering (usually 21-30 days after sowing).`;
      replyAr = `### توصية NPK لمرحلة إشطاء القمح:
* **نسبة NPK الموصى بها**: التسميد الأساسي النموذجي هو **120:60:40 كجم/هكتار** من N:P2O5:K2O.
* **التطبيق أثناء الإشطاء**: أضف **50% من إجمالي النيتروجين** كدفعة تغطية (Top dressing) أثناء الإشطاء النشط.`;
    } else if (
      text.includes("powdery") ||
      text.includes("mildew") ||
      text.includes("بياض") ||
      text.includes("دقيقي")
    ) {
      reply = `### Organic Powdery Mildew Management:
1. **Neem Oil Spray**: 1-2 teaspoons neem oil + 1/2 teaspoon liquid soap in 1 quart of warm water. Spray every 7-14 days.
2. **Baking Soda & Potassium Bicarbonate**: Alters the pH on the leaf surface.
3. **Milk Spray**: 1 part milk to 9 parts water. Spray during bright sunlight.`;
      replyAr = `### مكافحة البياض الدقيقي عضويًا:
1. **رش زيت النيم**: 1-2 ملعقة صغيرة من زيت النيم + 1/2 ملعقة صغيرة من الصابون السائل في لتر من الماء الدافئ.
2. **بيكربونات البوتاسيوم وصودا الخبز**: يغير درجة الحموضة (pH) على سطح الأوراق.
3. **رش الحليب**: جزء واحد من الحليب إلى 9 أجزاء من الماء. يُرش خلال أشعة الشمس الساطعة.`;
    } else if (
      text.includes("olive") ||
      text.includes("زيتون") ||
      text.includes("irrigation") ||
      text.includes("ري")
    ) {
      reply = `### Summer Olive Tree Irrigation Schedule:
* **Mature Trees**: Deep watering every **2 to 3 weeks** is ideal.
* **Young Trees (1-3 years)**: Require watering every **3 to 5 days** during peak summer heat.
* **Critical Rule**: Avoid waterlogging to prevent root rot (*Phytophthora*).`;
      replyAr = `### جدول ري أشجار الزيتون في الصيف:
* **الأشجار البالغة**: الري العميق كل **2 إلى 3 أسابيع** هو الأنسب.
* **الأشجار الفتية (1-3 سنوات)**: تتطلب الري كل **3 إلى 5 أيام** خلال ذروة حرارة الصيف.
* **قاعدة ذهبية**: تجنب تغدق التربة بالماء لتجنب عفن الجذور.`;
    } else {
      reply = `Hello! I am your AI AgriVision Chat Advisor. I can help you with:
- Crop disease diagnosis and remedies
- NPK and fertilizer recommendations
- Soil moisture and irrigation schedules
- Knowledge Graph insights

Please ask me any agricultural question!`;
      replyAr = `مرحباً! أنا مستشارك الذكي AgriVision. يمكنني مساعدتك في:
- تشخيص أمراض المحاصيل وطرق علاجها
- توصيات التسميد وخلطات NPK المناسبة
- جداول الري ورطوبة التربة
- معلومات واستفسارات من الرسم المعرفي الزراعي

يسعدني الإجابة عن أي سؤال زراعي لديك!`;
    }

    const isArabic = /[\u0600-\u06FF]/.test(message);
    const finalReply = isArabic ? replyAr : reply;

    return { reply: finalReply };
  });

type Message = {
  id: string;
  sender: "user" | "bot";
  text: string;
  timestamp: number;
  reasoning?: { agent: string; action: string }[];
};

const SUGGESTIONS = {
  en: [
    { text: "Why are my tomato leaves turning yellow?", key: "q1" },
    { text: "Best NPK ratio for wheat at tillering stage?", key: "q2" },
    { text: "How to manage powdery mildew organically?", key: "q3" },
    { text: "Optimal irrigation schedule for olive trees in summer?", key: "q4" }
  ],
  ar: [
    { text: "لماذا تتحول أوراق الطماطم إلى اللون الأصفر؟", key: "q1" },
    { text: "ما هي أفضل نسبة NPK للقمح في مرحلة الإشطاء؟", key: "q2" },
    { text: "كيفية إدارة البياض الدقيقي عضويًا؟", key: "q3" },
    { text: "جدول الري الأمثل لأشجار الزيتون في الصيف؟", key: "q4" }
  ]
};

const RESPONSES = {
  en: {
    q1: {
      text: `### Yellowing Tomato Leaves Diagnosis:

1. **Nitrogen Deficiency**: The oldest leaves at the bottom turn yellow first while the rest of the plant is light green.
   * **Remedy**: Apply nitrogen-rich fertilizer or compost tea.
2. **Watering Issues**: Both overwatering and underwatering cause yellowing. Overwatered leaves feel limp; underwatered leaves are dry and crispy.
   * **Remedy**: Adjust watering to ensure 1-1.5 inches of water per week, allowing the top inch of soil to dry out between waterings.
3. **Early Blight (Fungal)**: Yellow leaves with dark spots that look like targets.
   * **Remedy**: Remove infected leaves, apply copper fungicide, and avoid overhead irrigation.`,
      reasoning: [
        { agent: "Vision & Retrieval Agent", action: "Matched symptoms to Nitrogen Deficiency & Early Blight patterns." },
        { agent: "Knowledge Graph RAG", action: "Queried: Tomato → Symptoms (Yellowing) → Causes (N-Deficiency, Blight)." },
        { agent: "Decision Fusion Agent", action: "Formulated response with biological controls and chemical remedies." }
      ]
    },
    q2: {
      text: `### Wheat Tillering NPK Recommendation:

During the tillering stage, **Nitrogen (N)** is crucial for boosting vegetative growth and tiller survival.

* **Recommended NPK Ratio**: A typical base fertilization is **120:60:40 kg/ha** of N:P2O5:K2O.
* **Tillering Application**: 
  * Apply **50% of the total Nitrogen** as a top dressing during active tillering (usually 21-30 days after sowing, combined with irrigation).
  * Ensure Phosphorus (P) and Potassium (K) were fully applied at sowing, as they support root development and lodging resistance.
  * **Tip**: If soil test shows low organic matter, supplement with zinc sulfate (25 kg/ha).`,
      reasoning: [
        { agent: "Agronomy Retrieval Agent", action: "Fetched growth stage requirements for cereal crops." },
        { agent: "Knowledge Graph RAG", action: "Queried: Wheat → Tillering → Nutrient uptake rates." },
        { agent: "Decision Fusion Agent", action: "Calculated optimal NPK ratios based on standard agronomic recommendations." }
      ]
    },
    q3: {
      text: `### Organic Powdery Mildew Management:

Powdery mildew is a fungal disease that appears as white, dusty patches on leaves.

1. **Neem Oil Spray**: Interferes with the fungus's metabolism and acts as an organic fungicide.
   * **Mix**: 1-2 teaspoons neem oil + 1/2 teaspoon liquid soap in 1 quart of warm water. Spray every 7-14 days.
2. **Baking Soda & Potassium Bicarbonate**: Alters the pH on the leaf surface, making it uninhabitable for spores.
   * **Mix**: 1 tablespoon potassium bicarbonate + 1 tablespoon horticultural oil in 1 gallon of water.
3. **Milk Spray**: The proteins in milk create a natural antiseptic when exposed to sunlight.
   * **Mix**: 1 part milk to 9 parts water. Spray during bright sunlight.
4. **Cultural Practices**: Prune dense foliage to improve airflow and expose inner leaves to sunlight.`,
      reasoning: [
        { agent: "Pathology Agent", action: "Identified Erysiphales fungal family characteristics." },
        { agent: "Knowledge Graph RAG", action: "Queried: Powdery Mildew → Treatments (Organic) → Neem Oil, Potassium Bicarbonate." },
        { agent: "Decision Fusion Agent", action: "Synthesized natural remedies and cultural prevention practices." }
      ]
    },
    q4: {
      text: `### Summer Olive Tree Irrigation Schedule:

Olive trees are drought-tolerant, but summer irrigation is essential for optimal fruit size and oil accumulation.

* **Mature Trees**: Deep watering every **2 to 3 weeks** is ideal. 
  * Apply water to a depth of 3 feet around the drip line.
  * If using drip irrigation, run it for 4-6 hours once or twice a week (around 40-60 liters per tree per week depending on soil type).
* **Young Trees (1-3 years)**: Require watering every **3 to 5 days** during peak summer heat to establish roots.
* **Critical Rule**: Avoid waterlogging. Olive roots are highly sensitive to root rot (*Phytophthora*). Ensure the soil drains well.`,
      reasoning: [
        { agent: "Irrigation Agent", action: "Accessed evapotranspiration rates for olive cultivars in dry climates." },
        { agent: "Knowledge Graph RAG", action: "Queried: Olive Tree → Irrigation (Summer) → Root Rot prevention." },
        { agent: "Decision Fusion Agent", action: "Formatted water volume and frequency schedule for clay vs sandy soils." }
      ]
    }
  },
  ar: {
    q1: {
      text: `### تشخيص اصفرار أوراق الطماطم:

1. **نقص النيتروجين**: تبدأ الأوراق القديمة في الأسفل بالتحول إلى اللون الأصفر أولاً بينما يكون باقي النبات أخضر فاتحاً.
   * **العلاج**: ضع سماداً غنياً بالنيتروجين أو شاي الكمبوست.
2. **مشاكل الري**: يسبب كل من الإفراط في الري ونقصه الاصفرار. الأوراق المفرطة في الري تبدو ذابلة ورطبة؛ بينما تكون الأوراق المتعطشة جافة وهشة.
   * **العلاج**: اضبط الري لضمان 2.5-3.8 سم من الماء أسبوعياً، مع ترك الطبقة السطحية من التربة تجف بين الريات.
3. **اللفحة المبكرة (فطرية)**: أوراق صفراء بها بقع داكنة تشبه حلقات الهدف.
   * **العلاج**: أزل الأوراق المصابة، ورش مبيداً فطرياً نحاسياً، وتجنب الري العلوي.`,
      reasoning: [
        { agent: "وكيل الرؤية والاسترجاع", action: "مطابقة الأعراض مع أنماط نقص النيتروجين واللفحة المبكرة." },
        { agent: "رسم المعرفة RAG", action: "استعلام: طماطم ← الأعراض (الاصفرار) ← الأسباب (نقص النيتروجين، اللفحة)." },
        { agent: "وكيل دمج القرارات", action: "صياغة استجابة تتضمن المكافحة الحيوية والعلاجات الكيميائية." }
      ]
    },
    q2: {
      text: `### توصية NPK لمرحلة إشطاء القمح:

خلال مرحلة الإشطاء (الـ Tillering)، يكون **النيتروجين (N)** حاسماً لتعزيز النمو الخضري وضمان بقاء الإشطاءات.

* **نسبة NPK الموصى بها**: التسميد الأساسي النموذجي هو **120:60:40 كجم/هكتار** من N:P2O5:K2O.
* **التطبيق أثناء الإشطاء**:
  * أضف **50% من إجمالي النيتروجين** كدفعة تغطية (Top dressing) أثناء الإشطاء النشط (عادةً بعد 21-30 يوماً من البذر، بالتزامن مع الري).
  * تأكد من إضافة الفسفور (P) والبوتاسيوم (K) بالكامل عند البذر، لدعم نمو الجذور ومقاومة الرقاد.
  * **نصيحة**: إذا أظهر تحليل التربة نقصاً في المادة العضوية، فادعم المحصول بكبريتات الزنك (25 كجم/هكتار).`,
      reasoning: [
        { agent: "وكيل الاسترجاع الزراعي", action: "جلب متطلبات مرحلة النمو لمحاصيل الحبوب." },
        { agent: "رسم المعرفة RAG", action: "استعلام: القمح ← الإشطاء ← معدلات امتصاص العناصر الغذائية." },
        { agent: "وكيل دمج القرارات", action: "حساب نسب NPK المثلى بناءً على التوصيات الزراعية القياسية." }
      ]
    },
    q3: {
      text: `### مكافحة البياض الدقيقي عضويًا:

البياض الدقيقي هو مرض فطري يظهر على شكل بقع بيضاء تشبه المسحوق على الأوراق.

1. **رش زيت النيم**: يتداخل مع عملية التمثيل الغذائي للفطريات ويعمل كمبيد فطري عضوي.
   * **الخلطة**: 1-2 ملعقة صغيرة من زيت النيم + 1/2 ملعقة صغيرة من الصابون السائل في لتر من الماء الدافئ. يرش كل 7-14 يوماً.
2. **بيكربونات البوتاسيوم وصودا الخبز**: يغير درجة الحموضة (pH) على سطح الأوراق، مما يجعلها غير صالحة للأبواغ.
   * **الخلطة**: 1 ملعقة كبيرة من بيكربونات البوتاسيوم + 1 ملعقة كبيرة من الزيت البستاني في 4 لترات من الماء.
3. **رش الحليب**: تخلق البروتينات الموجودة في الحليب مطهراً طبيعياً عند تعرضها لأشعة الشمس.
   * **الخلطة**: جزء واحد من الحليب إلى 9 أجزاء من الماء. يُرش خلال أشعة الشمس الساطعة.
4. **الممارسات الزراعية**: قلم الأوراق الكثيفة لتحسين تهوية الهواء وتعريض الأوراق الداخلية للشمس.`,
      reasoning: [
        { agent: "وكيل أمراض النبات", action: "تحديد خصائص الفصيلة الفطرية Erysiphales." },
        { agent: "رسم المعرفة RAG", action: "استعلام: البياض الدقيقي ← العلاجات (العضوية) ← زيت النيم، بيكربونات البوتاسيوم." },
        { agent: "وكيل دمج القرارات", action: "دمج العلاجات الطبيعية مع ممارسات الوقاية البستانية." }
      ]
    },
    q4: {
      text: `### جدول ري أشجار الزيتون في الصيف:

أشجار الزيتون مقاومة للجفاف، لكن الري الصيفي ضروري لحجم الثمار الأمثل وتراكم الزيت.

* **الأشجار البالغة**: الري العميق كل **2 إلى 3 أسابيع** هو الأنسب.
  * أضف الماء حتى عمق متر واحد حول خط تنقيط المظلة الشجرية.
  * في حال الري بالتنقيط، شغّله لمدة 4-6 ساعات مرة أو مرتين في الأسبوع (حوالي 40-60 لتراً لكل شجرة أسبوعياً حسب نوع التربة).
* **الأشجار الفتية (1-3 سنوات)**: تتطلب الري كل **3 إلى 5 أيام** خلال ذروة حرارة الصيف لتثبيت الجذور.
* **قاعدة ذهبية**: تجنب تغدق التربة بالماء. جذور الزيتون حساسة جداً لعفن الجذور (*Phytophthora*). تأكد من جودة تصريف التربة.`,
      reasoning: [
        { agent: "وكيل الري والتربة", action: "الوصول إلى معدلات النتح التبخري لأصناف الزيتون في المناخات الجافة." },
        { agent: "رسم المعرفة RAG", action: "استعلام: شجرة الزيتون ← الري (الصيف) ← الوقاية من عفن الجذور." },
        { agent: "وكيل دمج القرارات", action: "تحديد كميات المياه وجدول الري للتربة الطينية مقابل الرملية." }
      ]
    }
  }
};

let globalMessages: Message[] = [];
let globalInput = "";
let globalIsTyping = false;
const chatListeners = new Set<() => void>();

function notifyChat() {
  chatListeners.forEach(l => l());
}

function useGlobalChat() {
  const [, setTick] = useState(0);
  useEffect(() => {
    const l = () => setTick(t => t + 1);
    chatListeners.add(l);
    return () => { chatListeners.delete(l); };
  }, []);
  
  return {
    messages: globalMessages,
    input: globalInput,
    isTyping: globalIsTyping,
    setMessages: (m: Message[] | ((prev: Message[]) => Message[])) => {
      globalMessages = typeof m === 'function' ? m(globalMessages) : m;
      notifyChat();
    },
    setInput: (i: string) => {
      globalInput = i;
      notifyChat();
    },
    setIsTyping: (t: boolean) => {
      globalIsTyping = t;
      notifyChat();
    }
  };
}

function ChatPage() {
  const { t, lang } = useI18n();
  const { messages, setMessages, input, setInput, isTyping, setIsTyping } = useGlobalChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeSuggestions = lang === "ar" ? SUGGESTIONS.ar : SUGGESTIONS.en;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async (text: string) => {
    if (!text.trim()) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      sender: "user",
      text,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const historyPayload = messages.map((m) => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text,
      }));

      const data = await chatResponseFn({
        data: {
          message: text,
          history: historyPayload,
        }
      });
      
      const botMsg: Message = {
        id: crypto.randomUUID(),
        sender: "bot",
        text: data.reply || (lang === "ar" ? "عذراً، لم أتمكن من الحصول على إجابة." : "Sorry, I couldn't get a response."),
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error("Chat error:", err);
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        sender: "bot",
        text: lang === "ar"
          ? "حدث خطأ في الاتصال بخادم المحادثة الذكية. يرجى التأكد من تشغيل الخادم."
          : "An error occurred while connecting to the Chatbot server. Please make sure the server is running.",
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="relative flex-1 flex flex-col justify-between min-h-[calc(100vh-4rem)] pb-6 bg-transparent">
      {/* Background glow orb */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl aspect-square -z-10 gradient-mesh opacity-20 blur-[130px] rounded-full mix-blend-screen dark:mix-blend-lighten" />

      {/* Main content body */}
      <div className="flex-1 overflow-y-auto px-4 py-8 sm:px-6 pb-28">
        <div className="max-w-4xl mx-auto h-full flex flex-col justify-center">
          <AnimatePresence mode="wait">
            {messages.length === 0 ? (
              <motion.div
                key="welcome"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5 }}
                className="flex-1 flex flex-col items-center justify-center py-12 text-center"
              >
                <div className="size-20 flex items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 shadow-glow mb-6 dark:bg-emerald-500/20 p-2">
                  <RealisticLeafSVG className="size-12 animate-pulse" />
                </div>

                <h1 className="text-4xl sm:text-5xl font-extrabold font-display tracking-tight text-zinc-900 dark:text-white">
                  {lang === "ar" ? "كيف يمكنني مساعدة مزرعتك اليوم؟" : "How can I help your farm today?"}
                </h1>
                <p className="mt-4 text-base sm:text-lg text-zinc-700 dark:text-zinc-300 max-w-xl font-medium leading-relaxed">
                  {lang === "ar"
                    ? "اسأل عن الأمراض، التسميد، الري، والعلوم الزراعية القابلة للتفسير."
                    : "Ask about diseases, fertilization, irrigation, and explainable agronomy."}
                </p>

                {/* Suggestions Grid */}
                <div className="mt-8 grid gap-4 sm:grid-cols-2 w-full max-w-2xl px-2">
                  {activeSuggestions.map((s) => (
                    <button
                      key={s.key}
                      onClick={() => handleSend(s.text)}
                      className="bg-white/70 hover:bg-white/95 dark:bg-zinc-950/60 dark:hover:bg-zinc-950/80 text-start p-5 rounded-2xl border border-white/40 dark:border-zinc-800/40 transition-all text-sm hover:shadow-elegant font-semibold leading-relaxed text-zinc-850 dark:text-zinc-250 cursor-pointer shadow-sm hover:-translate-y-0.5 duration-200"
                    >
                      {s.text}
                    </button>
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="chat"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="py-4 flex flex-col"
              >
                <div className="flex justify-end mb-4 px-2">
                  <button 
                    onClick={() => setMessages([])}
                    className="text-xs text-slate-500 hover:text-rose-500 transition-colors flex items-center gap-1.5 bg-white/60 dark:bg-zinc-900/60 hover:bg-rose-50 dark:hover:bg-rose-950/30 px-3 py-1.5 rounded-full border border-slate-200 dark:border-zinc-800 shadow-sm font-medium"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
                    {lang === "ar" ? "مسح المحادثة" : "Clear Chat"}
                  </button>
                </div>
                <div className="space-y-6">
                  {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`flex gap-4 ${m.sender === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {m.sender === "bot" && (
                      <div className="size-9 rounded-xl gradient-primary text-primary-foreground grid place-items-center shrink-0 shadow-soft">
                        <Leaf className="size-4.5" />
                      </div>
                    )}
                    <div
                      className={`max-w-[85%] rounded-2xl p-4 sm:p-5 text-sm sm:text-base leading-relaxed ${
                        m.sender === "user"
                          ? "bg-emerald-600 text-white rounded-br-none shadow-soft"
                          : "bg-white/70 dark:bg-zinc-950/70 border border-white/30 dark:border-zinc-800/40 rounded-bl-none text-zinc-850 dark:text-zinc-200 backdrop-blur-md"
                      }`}
                    >
                      <div className="prose prose-sm dark:prose-invert max-w-none space-y-2 whitespace-pre-line font-medium leading-relaxed">
                        {m.text}
                      </div>
                    </div>
                    {m.sender === "user" && (
                      <div className="size-9 rounded-xl bg-secondary border text-muted-foreground grid place-items-center shrink-0">
                        <User className="size-4.5" />
                      </div>
                    )}
                  </div>
                ))}

                {isTyping && (
                  <div className="flex gap-4 justify-start">
                    <div className="size-9 rounded-xl gradient-primary text-primary-foreground grid place-items-center shrink-0">
                      <Leaf className="size-4.5" />
                    </div>
                    <div className="bg-white/75 dark:bg-zinc-950/75 border border-white/30 dark:border-zinc-800/40 rounded-2xl rounded-bl-none p-4 flex items-center gap-2">
                      <Loader2 className="size-4 animate-spin text-primary" />
                      <span className="text-xs text-muted-foreground">
                        {lang === "ar" ? "وكيل القرار يفكر..." : "Decision Agent thinking..."}
                      </span>
                    </div>
                  </div>
                )}
                </div>
                <div ref={messagesEndRef} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Floating Bottom Input Bar */}
      <div className="w-full px-4 mt-auto">
        <div className="max-w-3xl mx-auto">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(input);
            }}
            className="relative flex items-center bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md border border-white/30 dark:border-zinc-800/40 rounded-full shadow-elegant px-2 py-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={lang === "ar" ? "اسأل عن محصولك..." : "Ask about your crop..."}
              className={`w-full bg-transparent ${lang === "ar" ? "pr-5 pl-14" : "pl-5 pr-14"} py-2.5 text-sm sm:text-base outline-none border-0 text-zinc-850 dark:text-zinc-150 placeholder-zinc-400 dark:placeholder-zinc-500 focus:ring-0`}
              dir="auto"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className={`absolute ${lang === "ar" ? "left-2" : "right-2"} size-10 grid place-items-center rounded-full bg-emerald-500 hover:bg-emerald-600 text-white transition-all disabled:opacity-40 shadow-glow cursor-pointer border-0 shrink-0`}
            >
              <Send className="size-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
