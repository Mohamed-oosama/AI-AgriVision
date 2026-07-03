import io
content = io.open('src/components/AppShell.tsx', 'r', encoding='utf-8').read()
header = content.split('<footer className="border-t mt-auto bg-background/50">')[0]

footer = """<footer className="border-t mt-auto bg-background/50">
        <div className="mx-auto max-w-7xl px-6 py-4 text-xs text-muted-foreground flex flex-col sm:flex-row items-center justify-between gap-4 relative">
          <span>© {new Date().getFullYear()} AI AgriVision</span>

          <details className="group [&_summary::-webkit-details-marker]:hidden">
            <summary className="cursor-pointer font-display flex items-center gap-1.5 outline-none hover:text-foreground transition-colors font-medium text-sm">
              <span className="text-base">🌱</span> تعليمات الاستخدام (Usage)
            </summary>
            
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-[95vw] max-w-6xl bg-background/95 backdrop-blur-2xl border shadow-2xl rounded-3xl p-6 z-50 cursor-auto text-left text-sm text-foreground space-y-6">
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
                  <h3 className="font-bold text-primary mb-3 pb-3 border-b flex items-center gap-3 text-base">
                    <div className="p-2 bg-primary/10 rounded-lg text-primary"><FlaskConical className="size-5" /></div>
                    <div>Nutrient Deficiencies<br/><span className="text-xs font-normal text-muted-foreground">نقص العناصر الغذائية</span></div>
                  </h3>
                  <ul className="flex flex-col text-xs space-y-0 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Citrus Nutrient Deficiency</span><span className="text-muted-foreground mt-0.5">اصفرار أوراق الحمضيات</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Maize Nitrogen Deficiency</span><span className="text-muted-foreground mt-0.5">نقص النيتروجين في الذرة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Maize Phosphorus Deficiency</span><span className="text-muted-foreground mt-0.5">نقص الفوسفور في الذرة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Maize Potassium Deficiency</span><span className="text-muted-foreground mt-0.5">نقص البوتاسيوم في الذرة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Maize Zinc Deficiency</span><span className="text-muted-foreground mt-0.5">نقص الزنك في الذرة</span></li>
                  </ul>
                </div>

                {/* Plant Diseases */}
                <div className="bg-background/50 rounded-2xl p-5 border shadow-sm flex flex-col h-[350px]">
                  <h3 className="font-bold text-destructive mb-3 pb-3 border-b flex items-center gap-3 text-base">
                    <div className="p-2 bg-destructive/10 rounded-lg text-destructive"><Leaf className="size-5" /></div>
                    <div>Plant Diseases<br/><span className="text-xs font-normal text-muted-foreground">أمراض النباتات</span></div>
                  </h3>
                  <ul className="flex flex-col text-xs space-y-0 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Bacterial Blight</span><span className="text-muted-foreground mt-0.5">اللفحة البكتيرية للكسافا</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Brown Streak</span><span className="text-muted-foreground mt-0.5">مرض الخط البني في الكسافا</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Green Mottle</span><span className="text-muted-foreground mt-0.5">التبقع الأخضر في الكسافا</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Healthy</span><span className="text-muted-foreground mt-0.5">كسافا سليمة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Cassava Mosaic Disease</span><span className="text-muted-foreground mt-0.5">مرض موزايك الكسافا</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Citrus Canker Disease</span><span className="text-muted-foreground mt-0.5">تقرحات الحمضيات</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Healthy Orange Leaf</span><span className="text-muted-foreground mt-0.5">ورقة برتقال سليمة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Apple Healthy</span><span className="text-muted-foreground mt-0.5">تفاح سليم</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Corn Common Rust</span><span className="text-muted-foreground mt-0.5">الصدأ الشائع في الذرة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Corn Healthy</span><span className="text-muted-foreground mt-0.5">ذرة سليمة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Corn Northern Leaf Blight</span><span className="text-muted-foreground mt-0.5">اللفحة الشمالية للذرة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Grape Black Rot</span><span className="text-muted-foreground mt-0.5">العفن الأسود في العنب</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Grape Esca</span><span className="text-muted-foreground mt-0.5">مرض الإيسكا في العنب</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Grape Leaf Blight</span><span className="text-muted-foreground mt-0.5">لفحة أوراق العنب</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Orange Huanglongbing</span><span className="text-muted-foreground mt-0.5">مرض اخضرار الحمضيات</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Peach Bacterial Spot</span><span className="text-muted-foreground mt-0.5">التبقع البكتيري في الخوخ</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Bell Pepper Healthy</span><span className="text-muted-foreground mt-0.5">فلفل رومي سليم</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Rice Healthy</span><span className="text-muted-foreground mt-0.5">أرز سليم</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Rice Leaf Blast</span><span className="text-muted-foreground mt-0.5">لفحة أوراق الأرز</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Rice Sheath Blight</span><span className="text-muted-foreground mt-0.5">لفحة غمد الأرز</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Rice Tungro</span><span className="text-muted-foreground mt-0.5">مرض التنجرو في الأرز</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Soybean Healthy</span><span className="text-muted-foreground mt-0.5">فول صويا سليم</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Squash Powdery Mildew</span><span className="text-muted-foreground mt-0.5">البياض الدقيقي في القرع</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Tomato Blight</span><span className="text-muted-foreground mt-0.5">لفحة الطماطم</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Tomato Healthy</span><span className="text-muted-foreground mt-0.5">طماطم سليمة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Tomato Yellow Leaf Curl</span><span className="text-muted-foreground mt-0.5">تجعد واصفرار أوراق الطماطم</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Wheat Smut</span><span className="text-muted-foreground mt-0.5">التفحم في القمح</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Wheat Yellow Rust</span><span className="text-muted-foreground mt-0.5">الصدأ الأصفر في القمح</span></li>
                  </ul>
                </div>

                {/* Plant Pests */}
                <div className="bg-background/50 rounded-2xl p-5 border shadow-sm flex flex-col h-[350px]">
                  <h3 className="font-bold text-amber-600 mb-3 pb-3 border-b flex items-center gap-3 text-base">
                    <div className="p-2 bg-amber-600/10 rounded-lg text-amber-600"><Bug className="size-5" /></div>
                    <div>Plant Pests<br/><span className="text-xs font-normal text-muted-foreground">الآفات الحشرية</span></div>
                  </h3>
                  <ul className="flex flex-col text-xs space-y-0 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Aphids</span><span className="text-muted-foreground mt-0.5">حشرة المنّ</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Army Worm</span><span className="text-muted-foreground mt-0.5">دودة الحشد</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Asiatic Rice Borer</span><span className="text-muted-foreground mt-0.5">حفار الأرز الآسيوي</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Blister Beetle</span><span className="text-muted-foreground mt-0.5">الخنفساء الفقاعية</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Corn Borer</span><span className="text-muted-foreground mt-0.5">حفار الذرة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Leafhopper</span><span className="text-muted-foreground mt-0.5">نطاط الأوراق</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Limacodidae</span><span className="text-muted-foreground mt-0.5">يرقات القواقع الشوكية</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Locustoidea</span><span className="text-muted-foreground mt-0.5">الجراد</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Lycorma Delicatula</span><span className="text-muted-foreground mt-0.5">الذبابة الفانوسية المرقطة</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Miridae</span><span className="text-muted-foreground mt-0.5">بقّ النبات</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Mole Cricket</span><span className="text-muted-foreground mt-0.5">صرصار الخلد</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Prodenia Litura</span><span className="text-muted-foreground mt-0.5">دودة ورق القطن</span></li>
                    <li className="flex flex-col py-2 border-b border-border/50 last:border-0"><span className="font-semibold text-foreground">Xylotrechus</span><span className="text-muted-foreground mt-0.5">حفار الساق الخشبي</span></li>
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
"""
io.open('src/components/AppShell.tsx', 'w', encoding='utf-8').write(header + footer)