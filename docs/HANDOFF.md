> Current continuation: [V4 active plan and verification status](V4_DYNAMIC_AI_IMPLEMENTATION_PLAN.md). This document preserves its original checkpoint; later measurements do not replace its historical results.

# تسليم المشروع

المجلد على جهاز Windows: D:\icips. شغّل start.bat ثم http://127.0.0.1:8000. لإعادة التثبيت استخدم setup.bat. اقرأ README.md قبل إضافة حل جديد.

## إضافة الكود من المتصفح

اختر المسألة ثم «كودي الخاص»، والصق solve(payload) أو افتح .py، وراجع العقد ثم فعّل تأكيد الكود المحلي وشغّل التحليل. لا يلزم تسجيل ملف في catalog. المحرر يحتفظ بالمسودات في ذاكرة الصفحة لكل مسألة؛ تحديث الصفحة يمحوها، والتصدير يحتفظ بالمصدر مع الأدلة.

المصدر يُنفذ عبر عامل محلي منفصل؛ ليس عزلاً أمنياً للأكواد العدائية. الأخطاء النحوية وسطر الاستثناء مدعومة، ويظهر فحص منطقي محدود لحالة آخر عنصر في البحث الثنائي عند وجود دليل AST وتنفيذ مطابق. لا يوجد ضمان لتحديد السبب المنطقي لكل كود.

إعادة فحص الإضافة: `tools/verify_custom_browser.py`، والنتائج في `docs/custom-code-ui-verification.json` و`docs/custom-code-tests.xml`. راجع `docs/CUSTOM_CODE.md` قبل توسيع التشخيص أو تغيير حدود الثقة. أوراق PDF ونتائج benchmark السابقة تعكس النسخة المقاسة ببصمتها، وليست قياساً لهذه الإضافة.

## الملفات المهمة

| المطلوب | الملف |
|---|---|
| تفاصيل الحالة المنجزة والمتبقية | docs/progress.md |
| نتائج فعلية وبروتوكول القياس | docs/MEASURED_RESULTS.md وbenchmarks/config.json |
| كل تجارب المقارنة وCSV | results/benchmarks، والمجلد الأحدث في results/summary.json |
| مثال شاهد حقيقي | results/clean-check-evidence.json |
| تحقق التثبيت والاختبارات | docs/clean-verification.json وdocs/clean-tests.xml |
| تحقق الواجهة والصور | docs/ui-verification.json وdocs/screenshots |
| البوستر القابل للطباعة | docs/poster.html وdocs/poster.pdf بعد التصدير |
| مسودة البحث | docs/manuscript_draft.md وHTML وPDF بعد التصدير |
| الرد التحضيري للمحكمين | docs/reviewer_response/response_draft.md |
| سيناريو العرض | docs/demo/demo_script_ar.md |

## إعادة التحقق

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe tools/verify_browser.py
.\.venv\Scripts\python.exe benchmarks/run.py --config benchmarks/config.json
.\.venv\Scripts\python.exe benchmarks/evidence_audit.py
.\.venv\Scripts\python.exe tools/build_report.py
.\.venv\Scripts\python.exe tools/export_pdfs.py
```

التقييم الجديد ينشئ مجلداً مؤرخاً؛ لا تعدل نتائج قديمة يدوياً. build_report يعيد بناء المسودات من آخر ملخص محفوظ ويتطلب ملفات التحقق. export_pdfs يستخدم Edge أو Chrome المثبت مع Playwright الاختياري. ملفات المصدر الجديدة تستلزم إعادة التقييم إذا تغيرت المكونات المشمولة في بصمته.

نسخة التنزيل تحتوي المصدر والأصول المحلية وملخصات القياس والتحقق والأمثلة والصور وسجلات أحدث مقارنة محفوظة. السجلات الكاملة لكل تجربة موجودة على جهازك؛ بياناتها قابلة لإعادة التوليد بالأوامر أعلاه. لا تتضمن النسخة .venv أو إعدادات Rider أو بيانات اعتماد. لا يوجد نشر عام أو رفع للمؤتمر تلقائياً.
