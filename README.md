# AlgoX-Ray

Counterexample-driven visual debugging and evidence-grounded hints for algorithmic problem solving.

نموذج بحثي **محلي** لمسائل Dijkstra وBinary Search وMaximum Subarray في فرع Option B (إصدار بحثي متحقق محلياً). يشغّل الحل، ويبحث عن حالة فشل قانونية، ويتحقق منها ويصغّرها، ثم يعرض التنفيذ الحقيقي وتلميحات مرتبطة بأدلتها. عدم اكتشاف خطأ لا يثبت صحة الحل.

## Option B — حالة التطوير

الفرع الحالي يدعم العقود الثلاثة والإلغاء من الخادم، وخيار عامل جديد لكل حالة، ومقارنة تغطية الأسطر بين حالات نجاح وفشل محدودة، واعتماديات حسابية مرصودة وملاحظات رياضية محققة. ترتيب الاشتباه ليس دليلاً على السبب الجذري. الإصدار 089009d اجتاز 126 اختباراً و20 رحلة متصفح؛ اكتملت 450 تجربة v2 وتدقيقها: 225/225 شاهد للحلول الخاطئة و0/225 اتهاماً للصحيحة ضمن العينة، و40/75 ملاحظة محددة في المسار الكامل. هذه ليست دقة عامة ولا دراسة تعليمية.

- [سجل مراحل Option B](docs/OPTION_B_STATUS.md)
- [البروتوكول الجديد](docs/OPTION_B_EVALUATION.md): 30 ملفاً، 450 تشغيلاً لكل إصدار؛ [نتائج v1 المقاسة](docs/option_b/MEASURED_V1.md). [نتائج v2 المقاسة](docs/option_b/MEASURED_V2.md). لا ننسب نتائج إصدار إلى آخر.
- [مصفوفة الأعمال السابقة](docs/OPTION_B_PRIOR_WORK.md)
- [مسودة V1](docs/option_b/manuscript.md) و[بوستر V1](docs/option_b/poster.html) و[نص العرض الأولي](docs/option_b/demo_ar.md). حزمة V2 المقاسة محفوظة محلياً تحت `results/option-b-v2/conference` للمراجعة قبل الإرسال.
- [إعادة الإنتاج](docs/option_b/REPRODUCE_V2.md) و[المراجعة البشرية المستقلة](docs/option_b/HUMAN_REVIEW_PROTOCOL.md).

## التشغيل على Windows

المطلوب Python 3.12. النسخة الأساسية لا تحتاج Node أو npm أو حساب API.

1. افتح `setup.bat` لتثبيت الاعتماديات داخل `.venv`.
2. افتح `start.bat` لتشغيل الخادم.
3. افتح [المختبر المحلي](http://127.0.0.1:8000).

أو من PowerShell داخل مجلد المشروع:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
.\.venv\Scripts\python.exe -m algoxray.cli serve
```

## تجربة أولى

اختر Dijkstra وحل «إغلاق العقدة مبكراً»، واترك البذرة 2026، ثم ابدأ التحليل. افتح التلميحات تدريجياً واضغط رابط الحدث في التلميح الثالث إن ظهر. يمكنك مقارنة الشاهد الأصلي بالمصغر، والتنقل بين أحداث التنفيذ، وتنزيل ملف JSON كامل.

## تحليل كودك من الموقع

1. اختر المسألة ثم «كودي الخاص».
2. الصق دالة Python باسم `solve(payload)`، أو استخدم «فتح ملف .py».
3. راجع عقد المدخل والخرج المعروض أسفل عنوان المحرر. الحد الأقصى للمصدر 32 KiB.
4. فعّل تأكيد أن الكود لك أو راجعته، ثم اضغط «ابدأ التحليل».
5. استخدم «وين ظهرت المشكلة؟» للانتقال إلى الحدث المدعوم، أو افحص التتبع عند غياب تشخيص محدد.
6. لتجربة سريعة في Binary Search: «مثال فيه خطأ»، ومدخل `{"array":[7],"target":7}`. المثال مزروع فيه خطأ معلن؛ كودك المستقل لا يحتاج تسجيله في catalog.

الأخطاء النحوية تعرض رقم السطر قبل التشغيل. الاستثناءات تعرض موضع ظهورها في التنفيذ المطابق لإعادة التشغيل. توجد ملاحظة AST/تنفيذ محدودة لتفويت عنصر أخير في بحث ذي حدود شاملة، وتعمل مع أسماء متغيرات مختلفة ضمن البنية المدعومة. لا تُستنتج أسباب منطقية عامة لكل كود. تعديل المصدر يلغي نتيجة العرض القديمة، والتنزيل يتضمن المصدر وبصمته والأدلة الفعلية.

## من الطرفية

```powershell
.\.venv\Scripts\python.exe -m algoxray.cli analyze --problem dijkstra_v1 --fixture dijkstra_premature_visited --seed 2026 --summary
.\.venv\Scripts\python.exe -m algoxray.cli analyze --problem binary_search_v1 --fixture binary_missing_last --case contracts/binary.example.json --summary
.\.venv\Scripts\python.exe -m algoxray.cli list
```

إضافة كود محلي: اكتب `solve(payload)` في ملف Python، واقرأ العقد في `contracts` ودليل API. بعد مراجعة الملف:

```powershell
.\.venv\Scripts\python.exe -m algoxray.cli analyze --problem dijkstra_v1 --submission reviewed_solution.py --trusted-local-file --summary
```

تشغيل ملف محلي جديد يعمل دون تسجيله في catalog. التتبع يسجل متغيرات محلية بسيطة ضمن حدود معلنة. adapters الأصلية مرتبطة ببصمة المصدر، وتوجد أيضاً فحوص ضيقة لبنية AST مع الدليل التنفيذي، ومواضع الاستثناءات. الامتناع هو النتيجة عند غياب دليل كافٍ؛ هذه ليست آلية عامة لاستنتاج السبب الجذري.

## التحقق والتجارب

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe benchmarks/run.py --config benchmarks/config.json
```

التقييم الافتراضي: 8 fixtures، و20 بذرة لكل من Random وHypothesis، أي 320 تشغيلاً. يتوقف كل بحث عند 100 مرشح أو 5 ثوانٍ قبل أول شاهد مؤكد. التصغير والتتبع معطلان في مقارنة الاكتشاف. هذه إعدادات بروتوكول وليست وعداً بمعدل نجاح.

نتائج التشغيل تحفظ في `results/benchmarks/<timestamp>`، وتشمل JSON لكل تشغيل وCSV وconfig وsummary. أحدث ملخص يظهر في صفحة «نتائج التجارب»، ويكتب أيضاً إلى `docs/MEASURED_RESULTS.md`. `results/runs` يحفظ تحليلات المستخدم منفصلة. لا تنسب تشغيلات البذور إلى عدد مستقل من البرامج أو الطلاب.

عداد `post_discovery_candidates` يشمل استدعاءات Hypothesis بعد أول شاهد مؤكد، بما فيها تأكيداته الداخلية والتصغير عند تمكينه. لا ندّعي أنه عدد عمليات التصغير الخالصة. `verification_solver_calls` و`replay_solver_calls` و`trace_solver_calls` منفصلة؛ السجل يسجل المصدر والإعدادات والبصمات والإصدارات.

## اختبار الواجهة الاختياري

```powershell
.\.venv\Scripts\python.exe -m pip install -e "./backend[browser]"
.\.venv\Scripts\python.exe tools/verify_browser.py
```

يستخدم Chrome أو Edge الموجودين على الجهاز في ملف تعريف مؤقت، ويشغّل خادماً اختبارياً على 8787 ثم يوقفه. يدعم `--browser` لمسار المتصفح. يمنع طلبات الشبكة الخارجية أثناء الفحص ويحفظ لقطات ونتيجة التحقق في `docs`.

فحص رحلة المحرر والملفات:

```powershell
.\.venv\Scripts\python.exe tools/verify_custom_browser.py
```

تقرير الإضافة: `docs/custom-code-ui-verification.json`، واختبارات المحرك/API: `docs/custom-code-tests.xml`. المقارنة التاريخية ذات 320 تشغيلاً تخص بصمة نسختها المحفوظة؛ لا تثبت أداء المحرر أو التشخيصات الجديدة.

## العقود والأدلة

- Dijkstra: غراف موجه بسيط، 2–8 عقد، أوزان صحيحة 1–20، حتى 20 حافة؛ قائمة المسافات من المصدر. `null` لغير القابل للوصول.
- المرجع NetworkX Bellman–Ford، مع فحص مستقل باستخدام Floyd–Warshall على المدخل نفسه.
- Binary Search: مصفوفة مرتبة بطول 0–32 وقيم -20 إلى 20؛ تكرارات مسموحة؛ أي فهرس مطابق صحيح، و-1 لغير الموجود.
- Maximum Subarray: مصفوفة غير فارغة بطول 1–24 من الأعداد الصحيحة في [-20,20]؛ أكبر مجموع لمقطع متصل غير فارغ. مرجع تعداد المقاطع يقارن مع Kadane.
- نوع الفشل منفصل: `wrong_answer`, `exception`, `timeout`, `contract_violation`.
- الحالة `inconclusive` ليست برهان صحة. `oracle_disagreement` لا يتهم الحل.
- H1 ملاحظة مؤكدة، وH2 سؤال تعليمي، وH3/H4 لا يظهران إلا عند وجود دليل خاص بالمصدر. لا يوصف السؤال التعليمي كتشخيص مثبت.
- `contracts/evidence.schema.json` يحدد البنية؛ `validate_bundle` يفحص إحالات الأحداث والادعاءات وإعادة التشغيل.

## حدود الثقة

هذا البرنامج ليس sandbox للكود المجهول. الخادم مرتبط بـ127.0.0.1. يقبل API حل catalog أو مصدراً محلياً موثوقاً، مع منع الجمع بينهما ومنع مسارات الملفات. المصدر الجديد يتطلب اتصال loopback وتأكيد الثقة ورمز الجلسة المحلي في ترويسة مخصصة؛ تُرفض الطلبات العابرة للمواقع. هذه الضوابط تمنع التشغيل غير المقصود من صفحة أخرى، ولا تعزل كوداً عدائياً عن ملفات الجهاز أو شبكته. توجد حدود للمهلة والخرج والتتبع وتنظيف العمليات، وملف مصدر مؤقت مستقل يُحذف بعد التحليل.

المسار الحتمي للمنتج لا يحتاج LLM أو مفتاح API، ولم يُفعّل أي مزود خارجي. لا يوجد تسجيل دخول أو نشر عام أو دراسة فائدة تعليمية. جميع fixtures مؤلفة أو benchmark منسوب لمصدره، وليست مجموعة أكواد طلاب حقيقية. تفاصيل القيود والإحالات موجودة في `docs/ARCHITECTURE.md` و`THIRD_PARTY_NOTICES.md`.

## خريطة المشروع

- `backend/src/algoxray`: المحرك والعامل والمراجع وAPI وCLI.
- `backend/tests`: اختبارات العقود والعمليات والأدلة والواجهات.
- `fixtures/catalog.json`: مصدر كل حل ورخصته وبصمته وadapter الخاص به.
- `web`: واجهة عربية تعمل بأصول محلية.
- `contracts`: أمثلة المدخلات وJSON Schema.
- `benchmarks`: البروتوكول وتشغيل التجارب.
- `docs`: التوثيق والنتائج والعرض ومسودة البحث وسجل الإنجاز.

راجع `docs/progress.md` لمعرفة الحالة التي تم التحقق منها فعلياً، و`docs/HANDOFF.md` لاستكمال العمل العلمي والتسليم.

## Docker deployment (Linux containers)

Run from the repository root:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f algoxray
```

Open http://localhost:8000. Health endpoint: /api/health.

For a reverse proxy on the same host, set ALGOXRAY_ALLOWED_HOSTS in a local
.env file to the actual DNS name plus localhost,127.0.0.1, and forward HTTPS
traffic to 127.0.0.1:8000 with the original Host header. Keep the application
port private. Add authentication and rate limiting at the reverse proxy for
shared deployments.

The container runs as a non-root user with restricted resources and a
read-only root filesystem in Compose. The deployment intentionally disables
arbitrary user-submitted Python (including the session-token endpoint);
catalog fixtures remain available. The local Windows workflow still supports
reviewed, trusted code. Do not enable custom code on a public server without
a separate hardened execution sandbox. Run artifacts in Compose are ephemeral.

Stop with:

```bash
docker compose down
```
