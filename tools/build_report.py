"""Build reviewable presentation drafts from saved measurements, never invented values."""
import base64
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def write(path, text):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def main():
    summary = read("results/summary.json")
    audit = read("results/evidence-audit.json")
    clean = read("docs/clean-verification.json")
    ui = read("docs/ui-verification.json")
    demo = read("results/clean-check-evidence.json")
    assert summary["status"] == "completed" and clean["status"] == ui["status"] == "passed"
    assert audit["claims_checked"] == audit["claims_supported"]
    suites = ET.parse(ROOT / "docs/clean-tests.xml").getroot()
    suites = [suites] if suites.tag == "testsuite" else list(suites)
    tests = sum(int(s.get("tests", 0)) for s in suites)
    assert sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites) == 0
    bugs = sum(r["buggy_found"] for r in summary["rows"])
    bug_trials = sum(r["buggy_runs"] for r in summary["rows"])
    controls = sum(r["control_runs"] for r in summary["rows"])
    false = sum(r["control_accusations"] for r in summary["rows"])
    table = "| Problem | Generator | Buggy trials with witness | Control accusations | Median ms | Median candidates |\n|---|---|---|---|---|---|\n"
    htmlrows = []
    for r in summary["rows"]:
        name = "Binary search" if r["problem_id"].startswith("binary") else "Dijkstra"
        values = [name, r["strategy"], f'{r["buggy_found"]}/{r["buggy_runs"]}',
                  f'{r["control_accusations"]}/{r["control_runs"]}',
                  f'{r["median_discovery_ms"]:.2f}', f'{r["median_discovery_candidates"]:g}']
        table += "| " + " | ".join(values) + " |\n"
        htmlrows.append("<tr>" + "".join(f"<td>{escape(v)}</td>" for v in values) + "</tr>")
    results_html = '<table><thead><tr><th>Problem</th><th>Generator</th><th>Witnesses</th><th>Controls</th><th>Median ms</th><th>Cases</th></tr></thead><tbody>' + "".join(htmlrows) + "</tbody></table>"
    example = f'Input: {json.dumps(demo["case"])}\nObserved: {json.dumps(demo["observed_output"])}\nReference: {json.dumps(demo["expected_output"])}'
    refs = [
        ("Python Tutor: execution visualization", "https://pythontutor.com/visualize.html"),
        ("Tillmann et al. Code Hunt (SBST 2014)", "https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/CodeHunt20SBST202014b.pdf"),
        ("Rivers and Koedinger. Data-Driven Hint Generation in Vast Solution Spaces", "https://krivers.net/files/ijaied2015-paper.pdf"),
        ("Liffiton et al. CodeHelp (2023), DOI 10.1145/3631802.3631830", "https://arxiv.org/abs/2308.06921"),
        ("Kazemitabaar et al. CodeAid (CHI 2024), DOI 10.1145/3613904.3642773", "https://arxiv.org/abs/2401.11314"),
        ("Hypothesis API: generation, shrinking and explain phases", "https://hypothesis.readthedocs.io/en/latest/reference/api.html"),
        ("QuixBugs; pinned source and license in fixtures/catalog.json", "https://github.com/jkoppel/QuixBugs"),
    ]
    refmd = "\n".join(f"{i}. {title}. {url}" for i, (title, url) in enumerate(refs, 1))
    refhtml = "<ol>" + "".join(f'<li>{escape(t)}. <a href="{u}">{u}</a></li>' for t, u in refs) + "</ol>"
    sections = [
        ("Abstract", f"AlgoX-Ray is a local prototype connecting legal counterexample search, validation, reduction, recorded Python execution, and staged feedback. It supports bounded Dijkstra and binary-search contracts. Hypothesis generation and shrinking are reused, with a seeded random baseline. Specific diagnostic observations require a reviewed source fingerprint and a matching runtime predicate; otherwise the system abstains. A technical evaluation executed {summary['total_runs']} trials over eight source files: seven authored fixtures and one adapted, attributed QuixBugs program. Both generators found reproducible failures in all {bug_trials} buggy trials combined, with {false} accusations across {controls} control trials. A separate automated audit checked {audit['claims_checked']} emitted claim instances in {audit['runs']} runs. These results demonstrate feasibility on the declared sample, not educational effectiveness or general root-cause accuracy."),
        ("1. Problem and contribution scope", "A failing output alone does not show which recorded program state supports a debugging observation. This prototype packages a legal witness, expected and observed results, replay outcomes, source/version provenance, line events, and claim-to-event references in one inspectable evidence bundle. The engineering contribution proposed for review is this explicit connection and its abstention rules. Test generation, shrinking, visualization and programming hints each have substantial prior work. No claim of algorithmic novelty or a first-of-its-kind system is established here."),
        ("2. Relation to prior work", "Python Tutor provides execution visualization [1]. Code Hunt uses automated input/output clues and dynamic symbolic execution [2]. ITAP studies data-driven personalized programming hints [3]. CodeHelp uses LLM assistance with guardrails [4], while CodeAid evaluates an assistant in a course deployment [5]. Hypothesis supplies mature property-based testing and shrinking [6]. AlgoX-Ray does not reproduce the full capabilities of those systems. It currently uses deterministic feedback templates rather than an LLM, restricts semantic adapters to two reviewed fixtures, and contributes a locally inspectable evidence workflow. This comparison is scoped and does not establish absence of similar features in prior systems."),
        ("3. Implemented method", "Each problem has an input validator, output checker, reference, generator and size measure. Dijkstra accepts simple directed graphs with 2–8 vertices, at most 20 unique edges, positive integer weights 1–20, and a valid source. NetworkX Bellman–Ford is cross-checked against an independently implemented small Floyd–Warshall computation on each candidate. Unreachable distances are null. Binary search accepts sorted arrays of length 0–32, values and target in [-20,20], including duplicates; any matching index is valid. A linear membership/index check supplies its reference contract. These bounds are experimental scope, not universal algorithm support."),
        ("3.1. Search, verification and reduction", "Seeded random and general Hypothesis strategies generate inputs within the same legal domain, with different sampling distributions. Candidate failures are replayed before acceptance; wrong answer, exception, timeout and output-contract violation remain separate. Oracle disagreement yields no accusation. Hypothesis find performs its library-supported search/shrinking when enabled. The random/manual path uses greedy legal reductions. Every accepted reduction preserves a confirmed failure category and exception type where applicable. Reduction is best effort and does not prove a globally minimal witness. Search budgets and post-discovery work are recorded separately; post_discovery_candidates includes internal confirmation calls and must not be described as pure shrinking attempts."),
        ("3.2. Execution and evidence", "A persistent child interpreter executes each candidate in a fresh namespace. Source hash, bounded output, per-case deadlines, process-tree cleanup and bounded sys.settrace snapshots are recorded. Line snapshots describe state before the highlighted line. Final evidence includes three replay attempts and a traced replay checked against the untraced outcome. Truncation or a trace-induced mismatch suppresses source-specific diagnosis. Claim references must resolve to recorded events. E0 denotes inconclusive evidence; E2 a confirmed legal witness; E3 adds a supported source-specific runtime observation. These labels express the prototype's validation policy, not a mathematical correctness proof."),
        ("3.3. Feedback and trust boundary", "H1 states a verified failure observation; H2 asks an educational question and is not a proven cause. H3/H4 appear only if the source fingerprint and complete-trace predicates match a registered adapter. For the premature-visited Dijkstra fixture, the predicate records a continue at a seen vertex even though d+w improves its distance. For the binary fixture, it records a missed final matching element. Editing the source disables that adapter. Generic code can still produce a witness and trace without a specific diagnosis. The HTTP interface accepts catalog fixtures only and binds to loopback. Reviewed local solve(payload) files are supported through an explicit CLI trust flag. The subprocess runner is not a hostile-code sandbox; public arbitrary-code submission is outside scope."),
        ("4. Technical evaluation protocol", f"The saved protocol uses eight source files, 20 seeds (2026–2045), and two generators, giving {summary['total_runs']} trials. Six files are intentionally buggy and two are correct controls. Seven are authored fixtures; one is adapted from the MIT-licensed QuixBugs find_in_sorted program [7], pinned by commit and source hash. All sources were reviewed; split labels are bookkeeping and are not a blinded holdout. Each discovery trial uses up to 100 candidate inputs or five seconds before the first confirmed witness, with shrinking and tracing disabled equally. Generator order alternates by seed. Timing includes worker startup and pre-acceptance verification. Discovery medians include successful trials only; censored and excluded runs are counted in the machine-readable summary. Repeated seeds are not independent programs or learners."),
        ("4.1. Measured results", "The table reports actual saved runs. The random baseline was faster in median discovery time on both sampled problems. The result provides no evidence that Hypothesis is superior on this sample; distributions differ, timings are machine-specific, and the corpus is small and known. No censored or excluded trials occurred in this run. The QuixBugs fixture is detected through a recursion exception on suitable absent targets, which is reported as an exception rather than silently recoded as wrong answer."),
        ("4.2. Verification and evidence audit", f"A fresh virtual environment on the same Windows machine installed the locked dependencies and passed {tests} automated tests, followed by a manual-case CLI run. This is installation validation, not independent-machine replication. Browser automation passed {len(ui['journeys'])} journeys, including local-only requests, graph/array views, hints, event navigation, JSON export, invalid input and a 390-pixel mobile layout; no page errors or external requests were recorded. Separately, {audit['runs']} generated/shrunk runs on the two supported authored fixtures produced {audit['witnesses']} witnesses, {audit['complete_traces']} complete traces, {audit['replay_matches']}/{audit['replay_attempts']} matching replay attempts, and {audit['claims_supported']}/{audit['claims_checked']} claim instances passing structural/arithmetic/source predicates. This audit shares the implementation's diagnostic rules and is not an independent human factuality study or event-level fidelity estimate."),
        ("5. Demonstration", "The supplied three-vertex Dijkstra example has edges 0→1=1, 0→2=3 and 1→2=1. The buggy fixture returns distance 3 for vertex 2; the validated reference returns 2. The interface displays the witness and source, highlights the actual recorded line, allows event navigation and gradual feedback, and exports the evidence. The companion JSON records the exact source fingerprint, event IDs and replay outcomes. This manually supplied example explains the mechanism; it is separate from the generated discovery benchmark and does not recover historical manuscript counts or event identifiers."),
        ("6. Limitations and threats to validity", "The sample contains only eight known source files and two bounded problems. The one external benchmark program does not make the corpus representative of student work. Replays increase confidence in observed stability without proving determinism. Source-specific predicates cover two authored mistakes and do not infer arbitrary root causes. Recorded variables are bounded snapshots, not a verified semantic model. There is no learner study, blinded test set, independent human annotation, educational-effect estimate, global-minimality proof, adversarial sandbox or general-language support. Timing depends on the Windows machine, libraries, worker startup and input distributions. These limitations should remain visible in the paper and demonstration."),
        ("7. Reproducibility and conclusion", f"Source, contracts, attribution, locked dependencies, tests, benchmark configuration and raw run files are available in the local project. Reproduce with the commands in README.md and inspect results/benchmarks/{summary['raw_directory']}. The evaluated source/protocol SHA256 is {summary['codebase_sha256']}. There is currently no verified public artifact URL or Git commit; a downloadable source snapshot is prepared separately. The implementation demonstrates a feasible bounded workflow from a verified failure to inspectable feedback. Broader diagnosis accuracy and educational value remain research questions. This draft must be reconciled with the original submission, reviewer text, author details and the venue's template before camera-ready submission."),
    ]
    draft = "# AlgoX-Ray: Counterexample-Driven Visual Debugging and Evidence-Grounded Hints for Algorithmic Problem Solving\n\n**Implementation-grounded draft — 26 November 2026. Author review required; not a camera-ready file.**\n\n"
    for heading, body in sections:
        draft += f"## {heading}\n\n{body}\n\n"
        if heading == "4.1. Measured results":
            draft += table + "\n"
        if heading == "5. Demonstration":
            draft += "```json\n" + example + "\n```\n\n"
    write("docs/manuscript_draft.md", draft + "## References\n\n" + refmd + "\n")
    article = "".join(f"<section><h2>{escape(h)}</h2><p>{escape(b)}</p>" + (results_html if h == "4.1. Measured results" else "") + (f'<pre>{escape(example)}</pre><figure><img src="screenshots/dijkstra-desktop.jpg" style="width:100%;max-height:100mm;object-fit:contain"><figcaption>Actual prototype screenshot from browser verification; a generated witness may differ from the manual example.</figcaption></figure>' if h == "5. Demonstration" else "") + "</section>" for h, b in sections)
    write("docs/manuscript_draft.html", '<!doctype html><html lang="en"><meta charset="utf-8"><title>AlgoX-Ray — implementation draft</title><style>@page{size:A4;margin:19mm}body{font:10.5pt/1.47 Arial,sans-serif;color:#142b36;max-width:180mm;margin:auto}h1{font-size:23pt;line-height:1.12}h2{font-size:13pt;break-after:avoid;margin-top:18pt}p{orphans:3;widows:3}table{width:100%;border-collapse:collapse;font-size:8.5pt}td,th{text-align:left;border-bottom:1px solid #ccd7d8;padding:6px}pre{white-space:pre-wrap;font-size:8pt;background:#eef5f3;padding:10px}li{margin:5px 0;overflow-wrap:anywhere}a{color:#096d68}.note{border-left:4px solid #e68c69;padding:10px;background:#fff5ef;font-size:10pt}</style><h1>AlgoX-Ray</h1><p style="font-size:15pt">Counterexample-Driven Visual Debugging and Evidence-Grounded Hints for Algorithmic Problem Solving</p><p class="note">Implementation-grounded draft · 26 November 2026 · Author review required.<br>Not camera-ready. Original submission, reviewer wording and venue format remain to be reconciled.</p>' + article + '<h2>References</h2>' + refhtml + '</html>')
    write("docs/reviewer_response/response_draft.md", f'''# Draft response to reviewers — Paper 20

Author review required. This response is based on the review themes summarized in the project plan, not a newly retrieved verbatim review. Insert exact reviewer quotations and final page/line references only after reconciling the original submission and current venue template. No response has been sent.

| Review theme | Implemented revision | Evidence and remaining limit |
|---|---|---|
| Only one authored example | Two bounded problems, six buggy fixtures and two controls; one pinned external QuixBugs fixture | fixtures/catalog.json; eight known source files, no student corpus or blinded holdout |
| Generator tailored to a bug | General legal generators and seeded random comparison; equal discovery budgets, no trace/shrink in either arm | benchmarks/config.json; {summary['total_runs']} actual trials; all sources reviewed, so independence from design choices is not proven |
| No actual submitted-code trace | Python line/call/return/exception recording, bounded snapshots, replay checks and source-hash gating | backend/src/algoxray/worker.py; trusted local solve(payload) CLI; semantics for two fixtures only |
| Missing screenshots | Actual desktop, binary and mobile browser captures | docs/screenshots; docs/ui-verification.json |
| Missing reproducible artifact | Source, locked install, {tests} passing fresh-environment tests and raw trial files | README.md; docs/clean-verification.json; public repository URL still pending |
| Related work incomplete | Scoped discussion of Python Tutor, Code Hunt, ITAP, CodeHelp, CodeAid and Hypothesis | docs/RELATED_WORK.md; no exhaustive novelty claim |
| Unused or malformed references | Draft has a fresh internally cited bibliography | Must still reconcile original reference numbers 8/9 and any malformed DOI; no claim that the original PDF was repaired |
| Long future-work discussion | Replacement draft reports implemented features and measured limits | docs/manuscript_draft.md; final venue page count/template not yet confirmed |

Suggested revision statement:

Thank you for the review. We have implemented a bounded local prototype and replaced unverified illustrative claims with newly collected technical results and explicit limitations. The revision reports known authored/curated fixtures, a random baseline, actual execution traces, reproducibility checks and source-gated evidence references. We do not claim general diagnostic accuracy, a novel test generator or an educational benefit from these experiments. Historical example counts and event IDs should be removed unless supported by a preserved original run. The new experiments do not retroactively validate earlier unperformed experiments.

Before submission: reconcile this response with each exact review item, correct the original manuscript transparently, supply final page references and the artifact URL required by the committee, and confirm the presentation category. Committee acceptance and publication decisions remain external.
''')
    write("docs/demo/demo_script_ar.md", '''# عرض AlgoX-Ray — نحو 5 دقائق

## قبل العرض

افتح start.bat ثم http://127.0.0.1:8000. لا يلزم إنترنت للتشغيل بعد التثبيت. لا تشغّل benchmark أثناء العرض. جهّز docs/poster.pdf وملف نتائج التجارب كنسخة احتياطية.

## 0:00–0:40 — المشكلة

«لما حل خوارزمية يفشل، معرفة الجواب الصحيح وحدها مو دائماً كافية لفهم الخطأ. النموذج يربط حالة فشل متحققاً منها بخطوات الكود الفعلية وتلميحات عليها دليل واضح.»

## 0:40–2:00 — أول تجربة

اختر Dijkstra ثم «إغلاق العقدة مبكراً». اترك Hypothesis والبذرة 2026 وابدأ. اشرح الفرق بين المتوقع والمرصود. قارن الشاهد الأصلي والمصغر؛ قل إن التصغير أفضل جهد وليس برهاناً على أصغر حالة ممكنة. لا تحفظ عدد المحاولات أو الحجم من ورقة قديمة: اقرأ القيم المعروضة فعلياً.

## 2:00–3:00 — الدليل والتلميحات

حرّك شريط الأحداث. المتغيرات تمثل الحالة قبل السطر المضاء. افتح H1 ثم H2، ووضح أن H2 سؤال تعليمي. عند ظهور H3 اضغط رابط الحدث: هذه ملاحظة مدعومة بتتبع هذا المصدر بالتحديد. H4 اتجاه مفاهيمي، وليس حلاً برمجياً جاهزاً. صدّر JSON واشرح وجود source hash وclaim/event IDs وإعادة التشغيل.

## 3:00–3:40 — حدود النظام

اختر Binary Search والحل الذي يفوّت العنصر الأخير؛ أدخل {"array":[7],"target":7} لإظهار المثال المصغر. جرّب الحل الصحيح: عدم العثور على خطأ ضمن الميزانية لا يثبت صحة الكود. الملف المحلي الجديد يدعم solve(payload) من CLI بعد المراجعة؛ التشخيص المحدد قد يمتنع عنه عند غياب adapter موثوق. لا تفتح استقبال أكواد مجهولة.

## 3:40–4:30 — القياس

افتح «نتائج التجارب». لدينا 320 تشغيلاً على 8 ملفات مصدر، وليس 320 طالباً أو برنامجاً مستقلاً. المقارنة تشمل Random وHypothesis وتكشف العينة الصغيرة المعروفة. اقرأ الوسيط من الجدول؛ لا تدّع تفوق Hypothesis إذا كانت البيانات لا تظهره. فحص الادعاءات الآلي ليس دراسة تعلم أو تحكيماً بشرياً مستقلاً.

## 4:30–5:00 — النهاية والأسئلة

«الناتج الحالي نموذج محلي قابل للتجربة وإعادة التشغيل؛ الخطوة البحثية التالية توسيع بيانات مستقلة وتقييم صحة التشخيص والفائدة التعليمية بطريقة مناسبة.»

إذا تعطل العرض: افتح docs/poster.pdf والصور الحقيقية وresults/clean-check-evidence.json. لا تقل إن لقطة محفوظة تنفيذ حي.
''')
    write("docs/progress.md", f'''# سجل التنفيذ — 26 نوفمبر 2026

## تم التحقق منه

- محرك CLI وAPI وواجهة عربية محلية لـDijkstra وBinary Search.
- توليد قانوني، مرجعان لـDijkstra، checker متعدد الإجابات لـBinary Search، إعادة تشغيل وتصغير وتتبع وتصدير أدلة.
- تشخيصان خاصان بمصادر مراجعة مع الامتناع عند غياب الدليل؛ دعم ملفات solve(payload) المحلية عبر CLI.
- {tests} اختباراً نجحت من بيئة افتراضية جديدة على الجهاز نفسه؛ {len(ui['journeys'])} مساراً للواجهة نجح.
- {summary['total_runs']} تجربة محفوظة: {bugs}/{bug_trials} تشغيلات الأخطاء لها شاهد، و{false}/{controls} اتهامات للحلول الضابطة؛ العينة 8 ملفات مصدر فقط.
- تدقيق آلي منفصل: {audit['claims_supported']}/{audit['claims_checked']} ادعاء متكرر اجتاز predicates، مع {audit['replay_matches']}/{audit['replay_attempts']} إعادة متطابقة. ليس دراسة بشرية.
- بوستر ومسودة بحث ورد للمحكمين وسيناريو عرض مولدة من النتائج المحفوظة؛ تحتاج مراجعة المؤلف العلمية والتنسيقية.

## نطاق التسليم

هذه نسخة محلية محدودة بمسألتين. BFS وMerge Sort وDP ودراسة الطلاب ودعم الأكواد العدائية ليست منفذة. كانت توسعات مقترحة في الخطة الأولى، ولا تعرض كميزات حالية. تصنيف العرض النهائي ومتطلبات التسجيل والنشر لم تؤكدها هذه البرمجة.

## ما يتطلب متابعة المؤلف

1. مطابقة المسودة والرد مع الورقة الأصلية والنص الكامل للتحكيم، وتصحيح الادعاءات القديمة غير المتحققة بشفافية.
2. تأكيد قالب اللجنة وعدد الصفحات وفئة العرض وهوية المؤلفين؛ مسودة PDF ليست camera-ready.
3. اختيار مستودع عام/مجهول مناسب ونشر artifact عند الحاجة. لا يوجد رابط GitHub منشور أو commit مخترع.
4. مراجعة المصادر والاقتباسات وفق تعليمات المؤتمر؛ لم يجر فحص تشابه آلي.
5. رفع النسخة والتسجيل ومراسلة اللجنة إجراءات لم تنفذ تلقائياً.

النتائج الحالية تثبت تشغيل هذا النموذج ضمن نطاقه، ولا تضمن قبول البحث أو جائزة.
''')
    write("docs/environment.md", f'''# Verified environment

- Evaluation Python: {summary['environment']['python']}
- Evaluation platform: {summary['environment']['platform']}
- Full evaluated dependency pins: requirements.lock.txt
- Evaluated source/protocol SHA256: {summary['codebase_sha256']}
- Evaluation raw directory: results/benchmarks/{summary['raw_directory']}
- Fresh-install verification: {clean['method']}
- Browser verification: Chromium-based browser {ui['browser']}; desktop 1440×1100 and mobile 390×844.
- No Node build step, cloud model, API key or remote asset request is needed at runtime.

Fresh installation needs Python 3.12 and package-index access. The lock records the working Windows environment. Portability beyond tested Python/OS versions is not claimed. Initial installation verification encountered a clock-resolution-dependent test fixture; it was replaced with a deterministic file-counter fixture, then the full fresh-environment check was rerun. The application replay-validation policy was not weakened.
''')
    write("docs/HANDOFF.md", '''# تسليم المشروع

المجلد على جهاز Windows: D:\\icips. شغّل start.bat ثم http://127.0.0.1:8000. لإعادة التثبيت استخدم setup.bat. اقرأ README.md قبل إضافة حل جديد.

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
.\\.venv\\Scripts\\python.exe -m pytest backend/tests -q
.\\.venv\\Scripts\\python.exe tools/verify_browser.py
.\\.venv\\Scripts\\python.exe benchmarks/run.py --config benchmarks/config.json
.\\.venv\\Scripts\\python.exe benchmarks/evidence_audit.py
.\\.venv\\Scripts\\python.exe tools/build_report.py
.\\.venv\\Scripts\\python.exe tools/export_pdfs.py
```

التقييم الجديد ينشئ مجلداً مؤرخاً؛ لا تعدل نتائج قديمة يدوياً. build_report يعيد بناء المسودات من آخر ملخص محفوظ ويتطلب ملفات التحقق. export_pdfs يستخدم Edge أو Chrome المثبت مع Playwright الاختياري. ملفات المصدر الجديدة تستلزم إعادة التقييم إذا تغيرت المكونات المشمولة في بصمته.

نسخة التنزيل تحتوي المصدر والأصول المحلية وملخصات القياس والتحقق والأمثلة والصور وسجلات أحدث مقارنة محفوظة. السجلات الكاملة لكل تجربة موجودة على جهازك؛ بياناتها قابلة لإعادة التوليد بالأوامر أعلاه. لا تتضمن النسخة .venv أو إعدادات Rider أو بيانات اعتماد. لا يوجد نشر عام أو رفع للمؤتمر تلقائياً.
''')
    graph = '''<svg viewBox="0 0 650 280" role="img" aria-label="Three-vertex counterexample"><defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="none" stroke="#146c66" stroke-width="2"/></marker></defs><g stroke="#146c66" stroke-width="5" fill="none" marker-end="url(#arrow)"><path d="M138 184 L299 70"/><path d="M351 70 L517 184"/><path d="M144 216 L502 216"/></g><g font-size="29" font-family="Arial" fill="#146c66"><text x="207" y="100">1</text><text x="436" y="100">1</text><text x="318" y="255">3</text></g><g fill="#112e3c"><circle cx="102" cy="215" r="42"/><circle cx="326" cy="48" r="42"/><circle cx="550" cy="215" r="42"/></g><g fill="white" text-anchor="middle" font-size="32" font-family="Arial"><text x="102" y="226">0</text><text x="326" y="59">1</text><text x="550" y="226">2</text></g></svg>'''
    screenshot_uri = "data:image/jpeg;base64," + base64.b64encode((ROOT / "docs/screenshots/dijkstra-desktop.jpg").read_bytes()).decode()
    poster = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>AlgoX-Ray — technical prototype poster</title>
<style>@page{{size:420mm 594mm;margin:0}}*{{box-sizing:border-box}}body{{margin:0;background:#eaf2ef;color:#17313c;font:15pt/1.3 Arial,sans-serif}}.poster{{width:420mm;min-height:594mm;padding:15mm 16mm 12mm;background:#edf4f1}}header{{background:#102e3c;color:#fff;border-radius:9mm;padding:11mm 12mm 10mm}}.eyebrow{{font-size:16pt;letter-spacing:2px;color:#a5e7d5}}h1{{font-size:61pt;letter-spacing:-3px;line-height:1.02;margin:6mm 0}}.subtitle{{font-size:24pt;line-height:1.22;max-width:330mm;margin:0}}.author{{font-size:16pt;color:#b9d1d6;margin:6mm 0 0}}.status{{font-size:13pt;margin-top:4mm;color:#d2e4e5}}.lead{{font-size:21pt;line-height:1.3;margin:7mm 1mm}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:5mm;margin-bottom:8mm}}.metric{{border-top:2mm solid #137b6a;padding:5mm;background:white;border-radius:2mm}}.metric strong{{display:block;font-size:39pt;line-height:1.1}}.metric span{{font-size:14pt}}.columns{{display:grid;grid-template-columns:1fr 1fr;gap:8mm}}section{{background:#fff;border-radius:5mm;padding:5mm;margin-bottom:4mm;break-inside:avoid}}h2{{font-size:22pt;line-height:1.15;margin:0 0 4mm;color:#0f6c5c}}h3{{font-size:18pt;margin:5mm 0 2mm}}p{{margin:0 0 3mm}}.small{{font-size:12pt;line-height:1.32}}.tag{{font-size:13pt;color:#44606a;text-transform:uppercase;letter-spacing:1px}}.steps{{margin:0;padding-left:7mm}}.steps li{{padding-bottom:2mm}}svg{{width:100%;height:58mm}}.answer{{background:#edf6f1;padding:4mm;border-radius:3mm;font:18pt/1.6 Consolas,monospace}}table{{border-collapse:collapse;width:100%;font-size:12pt;line-height:1.35}}td,th{{text-align:left;padding:3mm 1.5mm;border-bottom:1px solid #d4e3df}}th{{color:#0d6f60}}.caution{{background:#fff1e9;border-top:2mm solid #e3946e}}footer{{border-top:1px solid #b6d0c9;padding-top:5mm;font-size:12pt;line-height:1.45}}code{{overflow-wrap:anywhere}}a{{color:#0f6c5c}}@media screen{{.poster{{margin:0 auto}}}}</style>
<main class="poster"><header><div class="eyebrow">VERIFIED WITNESS → RECORDED EXECUTION → INSPECTABLE FEEDBACK</div><h1>AlgoX-Ray</h1><p class="subtitle">Counterexample-Driven Visual Debugging and Evidence-Grounded Hints for Algorithmic Problem Solving</p><p class="author">Hussam Eddin Alwan · Local research prototype · 26 November 2026</p><div class="status">Poster draft for author review. Affiliation and final venue format to be confirmed.</div></header>
<p class="lead">Show a reproducible failure, then show the recorded state that supports each specific debugging observation.</p>
<div class="metrics"><div class="metric"><strong>{summary['total_runs']}</strong><span>technical trials · 8 source files</span></div><div class="metric"><strong>{bugs}/{bug_trials}</strong><span>buggy trials with a verified witness</span></div><div class="metric"><strong>{false}/{controls}</strong><span>accusations in control trials</span></div></div>
<div class="columns"><div><section><div class="tag">01 · Implemented workflow</div><h2>From failure to evidence</h2><ol class="steps"><li>Generate legal inputs within an explicit problem contract.</li><li>Compare outputs with the reference; cross-check Dijkstra with a second oracle.</li><li>Replay and reduce while preserving the observed failure.</li><li>Record real Python events and bounded state snapshots.</li><li>Reveal staged hints with claim and event references.</li></ol><p class="small">Hypothesis supplies generation and shrinking. Random testing is a baseline. No LLM or cloud service is required.</p></section>
<section><div class="tag">02 · Recorded example</div><h2>A smaller, inspectable failure</h2>{graph}<div class="answer">Observed: [0, 1, 3]<br>Reference: [0, 1, 2]</div><p class="small" style="margin-top:4mm">The reviewed buggy Dijkstra fixture skips an improving edge to an already seen vertex. The evidence links that observation to the actual <code>continue</code> event. This manually supplied example is separate from the generated benchmark.</p></section>
<section><div class="tag">03 · Feedback policy</div><h2>Specific claims need evidence</h2><p class="small"><b>H1</b> Verified outcome · <b>H2</b> Educational question<br><b>H3</b> Supported event · <b>H4</b> Conceptual direction</p><img src="{screenshot_uri}" alt="Actual local prototype with graph, source trace and evidence" style="width:100%;height:45mm;object-fit:contain;border:1px solid #d4e3df;border-radius:2mm"><p class="small">Actual browser-verification capture; generated input may differ from the manual example above.</p><p class="small">H3/H4 require a complete matching trace, a reviewed source fingerprint and a registered predicate. Otherwise the prototype abstains. A question is not presented as a proven diagnosis.</p></section></div>
<div><section><div class="tag">04 · Actual technical evaluation</div><h2>Compare against random testing</h2><p class="small">8 known source files: 7 authored + 1 pinned, MIT-licensed QuixBugs adaptation. 6 buggy, 2 correct controls. 20 seeds × 2 generators. Per trial: 100 candidates / 5 seconds; no shrinking or tracing in either discovery arm.</p>{results_html}<p class="small" style="margin-top:4mm">Times are medians to a confirmed witness, including worker startup and verification. No censored or excluded runs occurred. Random was faster on this sample; Hypothesis superiority is not established.</p></section>
<section><div class="tag">05 · Implementation checks</div><h2>Reproducible local artifact</h2><p><b>{tests}</b> automated tests passed in a fresh environment on the same Windows machine.<br><b>{len(ui['journeys'])}</b> browser journeys passed, including export and mobile layout.</p><p class="small">Separate automated audit: {audit['runs']} runs, {audit['complete_traces']} complete traces, {audit['replay_matches']}/{audit['replay_attempts']} matching replays, {audit['claims_supported']}/{audit['claims_checked']} claim instances passing evidence predicates. This is not independent human factuality evaluation.</p><p class="small">Dijkstra: directed graphs, 2–8 vertices, positive weights. Binary search: sorted arrays, duplicates accepted. JSON exports preserve inputs, source hash, versions, attempts, events and claim links.</p></section>
<section class="caution"><div class="tag">06 · Claims and limits</div><h2>Feasibility within a small scope</h2><p class="small">Repeated seeds are not independent programs or learners. All eight sources were reviewed; there is no blinded holdout or student dataset. Semantic diagnosis covers two authored fixtures. No learning benefit, general root-cause accuracy or globally minimal witness is established.</p><p class="small">Local trusted-code prototype. The runner is not a hostile-code sandbox. Failure not found means inconclusive, not correct. Conference acceptance and publication are external decisions.</p></section></div></div>
<footer><b>Prior work:</b> Python Tutor · Code Hunt (SBST 2014) · ITAP · CodeHelp (2023) · CodeAid (CHI 2024). Hypothesis and NetworkX are attributed dependencies; QuixBugs provenance is preserved.<br><b>Reproduce:</b> README.md · benchmarks/config.json · docs/MEASURED_RESULTS.md · results/summary.json<br><b>Traceable artifact:</b> evaluated source/protocol SHA256 <code>{summary['codebase_sha256']}</code><br>Full references: docs/RELATED_WORK.md. Public repository URL and venue-specific formatting remain pending author review.</footer></main></html>'''
    assert demo["observed_output"] == [0, 1, 3] and demo["expected_output"] == [0, 1, 2]
    write("docs/poster.html", poster)
    write("docs/report-build.json", json.dumps({"created_at": datetime.now(timezone.utc).isoformat(),
          "measured_source_sha256": summary["codebase_sha256"], "benchmark_directory": summary["raw_directory"],
          "test_count": tests, "ui_journeys": len(ui["journeys"]), "status": "drafts_generated",
          "author_review_required": True}, indent=2))
    print(json.dumps({"drafts_generated": True, "tests": tests, "trials": summary["total_runs"]}))


if __name__ == "__main__":
    main()
