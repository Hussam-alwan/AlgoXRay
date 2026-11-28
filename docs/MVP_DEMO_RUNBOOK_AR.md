# إعادة تشغيل عرض AlgoXRay المحلي

## تجهيز نسخة التحقق

ابدأ من checkout مستقل لرأس `mvp-implementation` الذي تسجله [الخطة المعتمدة](AlgoXRay_MVP_Master_Plan_AR.md). استخدم Python 3.12 وDocker، وثبّت Edge أو Chrome لفحوص المتصفح. الأوامر التالية لـPowerShell من جذر المستودع.

```powershell
git rev-parse HEAD
docker version --format '{{.Server.Version}}'
python -m venv .venv
$py = '.\.venv\Scripts\python.exe'
& $py -m pip install -r requirements.lock.txt
& $py -m pip install --no-deps -e ./backend
& $py -m pip check
& $py tools/prepare_v4_worker.py
```

يسجل أمر تجهيز العامل معرف الصورة المحلي في `results/v4-runtime.json`. يمكن إعادة استخدام صورة تحقق موجودة بتعيين معرفها الكامل في `ALGOXRAY_V4_IMAGE`. تسجل نتائج تشغيل العامل معرف الصورة المستخدم.

لتشغيل الواجهة محلياً، افتح `http://127.0.0.1:8787/v4` بعد بدء الخادم. راجع مصادر البرامج والمراجع قبل اعتمادها في الواجهة.

```powershell
& $py -m uvicorn algoxray.api:app --host 127.0.0.1 --port 8787
```

## الرحلات الثلاث

تبدأ أدوات التحقق خوادم مؤقتة على منافذها الخاصة. كرر الأوامر بمجلد نتائج جديد لحفظ كل إعادة. القياسات والبرامج هنا أمثلة تطوير معلنة.

```powershell
$out = 'results/mvp-demo-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
& $py -m pytest backend/tests -q
& $py tools/verify_mvp_intake_browser.py --port 18930 --out "$out/witness.json"
& $py tools/verify_mvp_performance.py --out "$out/performance.json"
& $py tools/verify_v4_failure_browser.py --port 18931 --out "$out/limits"
```

| الرحلة | ما يُعرض | الدليل |
|---|---|---|
| اكتشاف عيب وإصلاحه | إدخال وصف مسألة جديدة، شاهد أصلي ومصغر، تتبع ثم إصلاح كامل | `witness.json` يسجل الشاهدين، خطوات التصغير، وهوية مجموعة تحقق الإصلاح |
| فهم الأداء | حلان صحيحان للمهمة نفسها. منحنى على خمسة أحجام، ثم تتبع منفصل عند حجم واحد | `performance.json` يحفظ بيانات كل تكرار ودليل تطابق المخارج وسبب الامتناع عن الملاءمة عند الضجيج |
| حدود الحكم | تعارض مرجع، متابعة يدوية، فشل الصياغة وتعطل مزود محاكى | `limits/report.json` وملفات التشغيل داخل المجلد |

يُشغل فحص الإلغاء وحدود العامل بعد انتهاء بقية فحوص Docker على نفس الجهاز، لأن أداة التحقق تتعرف إلى الحاوية الجديدة أثناء طلب القياس. تسجل الأداة حدود الذاكرة والمعالج والعمليات التي أعادها Docker، ونتيجة تنظيف العامل بعد الإلغاء.

```powershell
& $py tools/verify_mvp_observation_browser.py --port 18932 --out "$out/observation.json"
```

يمكن فحص تطبيق الويب المغلف في Docker بشكل منفصل عبر `docker compose config --quiet` وأمر البناء. رحلة تحليل الكود تستخدم خادم التطوير المحلي وعامل Docker المخصص.
