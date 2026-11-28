"use strict";

const by = id => document.getElementById(id);
const levels = {
  published: "العينات المنشورة", minimum: "الأدنى", maximum: "الأقصى",
  near_limits: "قرب الحدود", middle: "الوسط", varied: "حالات متنوعة"
};
const statusLabels = {
  observed_mismatch: "وجدنا حالة فشل مؤكدة",
  no_witness_found: "لم نجد فشلًا ضمن الاختبارات المنفّذة",
  oracle_unavailable: "تعذّر الحكم بسبب مشكلة في المرجع أو العامل",
  cancelled: "أُلغي التحليل",
  unstable: "لم يتكرر الفشل بثبات",
  inconclusive: "لم يكتمل الحكم على الحل"
};

let problems = [];
let run = null;
let current = null;
let repair = null;
let selectedWitness = null;
let shownHints = 0;

async function request(path, body) {
  const options = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  };
  const response = await fetch("/api/v4/catalog" + path, options);
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 409) throw Error("يوجد تحليل جارٍ. جرّب بعد اكتماله.");
    throw Error(typeof data.detail === "string" ? data.detail : "تعذّر تنفيذ الطلب. راجع المدخلات.");
  }
  return data;
}

const text = (id, value) => { by(id).textContent = value ?? ""; };

function clearResult() {
  current = repair = selectedWitness = null;
  by("results").hidden = true;
  text("status", "");
  text("recheck-result", "");
  by("checks").replaceChildren();
}

function showProblem() {
  clearResult();
  const problem = problems.find(item => item.id === by("problem").value);
  if (!problem) return;
  text("statement", problem.statement);
  by("problem-link").hidden = !problem.url;
  if (problem.url) by("problem-link").href = problem.url;
  const trust = {
    development_reference: "مرجع تطويري مع عينات وضوابط معلومة",
    curator_supplied_reference: "مرجع راجعه مجهّز المسألة",
    accepted_reported_by_curator: "مرجع أبلغ مجهّز المسألة عن قبول إرساله"
  };
  text("trust", trust[problem.trust_basis]);
}

function setBusy(busy) {
  for (const id of ["problem", "student-source", "manual-input", "analyze", "trace-run", "candidate", "recheck"]) {
    by(id).disabled = busy;
  }
  by("cancel").hidden = !busy;
  by("cancel").disabled = false;
}

function selectTab(selected) {
  for (const button of document.querySelectorAll(".catalog-tabs button")) {
    const active = button.id === "tab-" + selected;
    button.tabIndex = active ? 0 : -1;
    button.setAttribute("aria-selected", String(active));
    by(button.getAttribute("aria-controls")).hidden = !active;
  }
  if (selected === "judgment" && !by("lanterns").hidden) drawLanterns(selectedWitness);
}

function render(data, mode) {
  current = data;
  selectedWitness = data.witness ?? data.partial_observation?.witness ?? data.detail;
  const witness = selectedWitness;
  const report = data.run_report;
  const verdict = mode === "trace" && witness?.judgment?.status === "accepted" ?
    "خرج الحل يطابق المتوقع لهذا المدخل" : statusLabels[data.status] ?? data.status;
  text("verdict", verdict);
  const reason = report.stop_reason.includes("budget") ? " · توقّف عند حد الميزانية" : "";
  text("run-summary", report.physical_executions + " تشغيلًا للعامل · " +
    (report.elapsed_ms / 1000).toFixed(1) + " ثانية" + reason);
  by("witness").hidden = !witness;
  text("stdin", witness?.stdin);
  text("actual", witness?.student?.stdout || witness?.student?.status || "—");
  text("expected", witness?.reference?.stdout || witness?.reference?.known_expected || "—");
  by("lanterns").hidden = data.visualization !== "lanterns" || !witness?.case;
  const reduction = data.reduction ?? data.partial_observation?.reduction;
  by("reduction").hidden = !reduction;
  if (reduction) {
    text("reduction-summary", "تصغير الشاهد من " + reduction.original_complexity[0] + " إلى " +
      reduction.reduced_complexity[0] + " عنصرًا");
    text("original-input", data.original_witness?.stdin);
    text("reduction-detail", reduction.probes + " محاولة · " + reduction.reduced_replay_count +
      " إعادات مكتملة للشاهد النهائي" + (reduction.original_replay_status === "verified" ?
        " · تأكّد الشاهد الأصلي" : reduction.original_replay_status === "same_as_reduced" ?
          " · الأصل هو الشاهد المعروض" : " · تحقق الأصل غير مكتمل"));
  }
  by("levels").replaceChildren();
  if (data.search && mode === "search") {
    for (const [key, label] of Object.entries(levels)) {
      const count = data.search.levels[key];
      const item = document.createElement("li");
      item.dataset.run = String(count > 0);
      item.textContent = label + " · " + (count || "لم يُشغّل");
      by("levels").append(item);
    }
  }
  by("levels-title").hidden = mode !== "search";
  text("counters", data.search ? data.search.unique_executed + " مدخلًا في البحث الأولي · " +
    data.search.duplicate + " مكرر · " + data.search.rejected_invalid + " مرفوض" : "");
  const events = witness?.trace?.events ?? [];
  by("trace-controls").hidden = !events.length;
  by("step").max = Math.max(1, events.length);
  by("step").value = 1;
  text("trace-summary", events.length ? events.length + " حدثًا من حلّك · " +
    (witness.trace.trace_status === "truncated" ? "سجل الأحداث مقتطع" : "سجل الأحداث مكتمل") :
    "لا تتوفر أحداث تتبّع لهذه النتيجة.");
  showEvent();
  shownHints = 0;
  showHints();
  by("repair-form").hidden = data.status !== "observed_mismatch";
  by("candidate").value = data.student_source || "";
  by("results").hidden = false;
  selectTab(mode === "trace" && events.length ? "trace" : "judgment");
}

function showEvent() {
  const events = selectedWitness?.trace?.events ?? [];
  const position = Number(by("step").value) - 1;
  const event = events[position];
  const labels = { before_line: "قبل تنفيذ السطر", call: "دخول الدالة", return: "رجوع الدالة", exception: "استثناء" };
  text("event-label", event ? labels[event.snapshot_timing] + " · السطر " + event.line + " · " +
    event.function + " · " + event.frame_id + (event.parent_frame_id ? " ← " + event.parent_frame_id : "") : "");
  const sourceLine = event && current.student_source.split(/\r?\n/)[event.line - 1];
  text("active-line", sourceLine !== undefined && event ? event.line + "  " + sourceLine : "");
  text("locals", event ? JSON.stringify(event.locals, null, 2) : "");
  by("event-path").replaceChildren();
  events.slice(Math.max(0, position - 3), position + 4).forEach(item => {
    const index = events.indexOf(item);
    const entry = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.event_id + " · " + item.line;
    if (index === position) button.setAttribute("aria-current", "step");
    button.addEventListener("click", () => {
      by("step").value = index + 1;
      showEvent();
      by("event-path").querySelector('[aria-current="step"]')?.focus();
    });
    entry.append(button);
    by("event-path").append(entry);
  });
  by("previous-event").disabled = position <= 0;
  by("next-event").disabled = position >= events.length - 1;
}

function drawLanterns(witness) {
  const {positions, length} = witness.case;
  const canvas = by("lantern-plot");
  const width = canvas.clientWidth;
  if (!width) return;
  const pixelRatio = devicePixelRatio;
  canvas.width = width * pixelRatio;
  canvas.height = 130 * pixelRatio;
  const ctx = canvas.getContext("2d");
  ctx.scale(pixelRatio, pixelRatio);
  const margin = 20;
  const x = point => margin + point / length * (width - margin * 2);
  const radius = Number(witness.student.stdout?.trim());
  const sorted = [...positions].sort((a, b) => a - b);
  let coveredUntil = 0;
  const gaps = [];
  if (witness.student.stdout?.trim() && Number.isFinite(radius) && radius >= 0) {
    for (const position of sorted) {
      const start = Math.max(0, position - radius);
      const end = Math.min(length, position + radius);
      if (start > coveredUntil) gaps.push([coveredUntil, start]);
      coveredUntil = Math.max(coveredUntil, end);
      ctx.fillStyle = "#4abdaa";
      ctx.fillRect(x(start), 63, x(end) - x(start), 9);
    }
    if (coveredUntil < length) gaps.push([coveredUntil, length]);
    ctx.fillStyle = "#f5a971";
    for (const [start, end] of gaps) ctx.fillRect(x(start), 63, Math.max(1, x(end) - x(start)), 9);
  }
  ctx.strokeStyle = "#9daec3";
  ctx.beginPath();
  ctx.moveTo(x(0), 78);
  ctx.lineTo(x(length), 78);
  ctx.stroke();
  ctx.fillStyle = "#f5e0a5";
  for (const position of new Set(sorted)) {
    ctx.beginPath();
    ctx.arc(x(position), 50, 3.5, 0, 2 * Math.PI);
    ctx.fill();
  }
  ctx.fillStyle = "#e2eaf6";
  ctx.font = "13px system-ui";
  ctx.fillText("0", x(0), 103);
  ctx.textAlign = "right";
  ctx.fillText(String(length), x(length), 103);
  const gapList = gaps.slice(0, 4).map(pair => "[" + pair.join(", ") + "]").join("، ");
  text("lantern-summary", positions.length + " مصباحًا · طول الشارع " + length +
    (gaps.length ? " · أجزاء خارج التغطية: " + gapList + (gaps.length > 4 ? "…" : "") : ""));
}

function showHints() {
  const hints = current?.hints ?? [];
  const labels = {
    output_mismatch: "قارن خرج حلّك بالخرج المتوقع في تبويب النتيجة.",
    student_exception: "ابدأ من الاستثناء الظاهر في تبويب التتبّع.",
    inspect_before_output: "افحص القيم المسجلة قبل أسطر الحساب والطباعة.",
    compare_coverages: "قارن تغطية الطرفين بأكبر فجوة بين مصباحين متجاورين.",
    verify_patch: "جرّب الحل المعدّل على الشاهد وحالات إضافية من تبويب إعادة التحقق."
  };
  const components = { left_end: "الطرف الأيسر", right_end: "الطرف الأيمن", inner_gap: "نصف أكبر فجوة داخلية" };
  by("hint-list").replaceChildren();
  for (const hint of hints.slice(0, shownHints)) {
    const item = document.createElement("li");
    item.textContent = hint.key === "largest_gap" ?
      "أكبر مسافة مطلوبة في هذا المدخل جاءت من " +
      hint.largest.map(key => components[key] + " (" + hint.components[key] + ")").join(" و") + "." :
      labels[hint.key];
    by("hint-list").append(item);
  }
  by("no-hints").hidden = hints.length > 0;
  by("next-hint").hidden = shownHints >= hints.length;
}

async function start(mode, rechecking = false) {
  if (run) return;
  const problem = problems.find(item => item.id === by("problem").value);
  const source = rechecking ? current?.student_source : by("student-source").value;
  if (!problem || !source?.trim()) {
    text("status", "اختر مسألة وأضف حل Python.");
    return;
  }
  const body = { problem_id: problem.id, package_key: problem.key, source, mode,
    analysis_id: crypto.randomUUID().replaceAll("-", "") };
  if (mode === "trace") body.stdin = rechecking ? current.witness.stdin : by("manual-input").value;
  if (rechecking) {
    body.candidate = by("candidate").value;
    if (!body.candidate.trim()) {
      text("recheck-result", "ألصق الحل المعدّل أولًا.");
      return;
    }
    body.original_stdin = current.original_witness?.stdin || null;
  } else {
    clearResult();
  }
  run = body.analysis_id;
  setBusy(true);
  text("status", rechecking ? "إعادة تشغيل الشاهد والاختبارات الإضافية…" :
    mode === "trace" ? "تشغيل المدخل المحدد وجمع التتبّع…" : "تشغيل الاختبارات والبحث عن حالة فشل…");
  try {
    const result = await request(rechecking ? "/recheck" : "/analyze", body);
    if (run !== result.analysis_id) return;
    if (rechecking) {
      repair = result;
      text("recheck-result", result.status === "passed_named_tests" ? "اجتاز الحل المعدّل جميع الفحوص المحددة." :
        result.status === "cancelled" ? "أُلغيت إعادة التحقق." : "لم يجتز الحل المعدّل جميع الفحوص المحددة.");
      by("checks").replaceChildren();
      for (const row of result.checks ?? []) {
        const item = document.createElement("li");
        const label = { witness: "الشاهد المصغّر", original_witness: "الشاهد الأصلي",
          owner_control: "اختبار معلوم", generated_regression: "اختبار مولّد" };
        item.textContent = label[row.kind] + " · " + (row.status === "match" ? "اجتاز" :
          row.status === "oracle_unavailable" ? "تعذّر الحكم" : "خرج مختلف أو خطأ تشغيل");
        by("checks").append(item);
      }
    } else {
      render(result, mode);
    }
    text("status", "");
  } catch (error) {
    text("status", error.message);
  } finally {
    run = null;
    setBusy(false);
  }
}

by("editor").addEventListener("submit", event => { event.preventDefault(); start("search"); });
by("repair-form").addEventListener("submit", event => { event.preventDefault(); start("trace", true); });
by("trace-run").addEventListener("click", () => start("trace"));
by("problem").addEventListener("change", showProblem);
by("student-source").addEventListener("input", () => {
  if (current) text("status", "عدّلت الكود. التقرير الظاهر مرتبط بالتشغيل السابق.");
});
by("cancel").addEventListener("click", async () => {
  if (!run) return;
  const active = run;
  by("cancel").disabled = true;
  try {
    await request("/" + active + "/cancel", {});
    if (run === active) text("status", "طلبنا إلغاء التشغيل…");
  } catch (error) {
    if (run === active) {
      text("status", error.message);
      by("cancel").disabled = false;
    }
  }
});
by("step").addEventListener("input", showEvent);
by("previous-event").addEventListener("click", () => { by("step").stepDown(); showEvent(); });
by("next-event").addEventListener("click", () => { by("step").stepUp(); showEvent(); });
by("next-hint").addEventListener("click", () => { shownHints++; showHints(); });
const tabs = [...document.querySelectorAll(".catalog-tabs button")];
for (const tab of tabs) {
  tab.addEventListener("click", () => selectTab(tab.getAttribute("aria-controls")));
  tab.addEventListener("keydown", event => {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const direction = event.key === "ArrowLeft" ? 1 : -1;
    const next = tabs[(tabs.indexOf(tab) + direction + tabs.length) % tabs.length];
    selectTab(next.getAttribute("aria-controls"));
    next.focus();
  });
}
by("export").addEventListener("click", () => {
  if (!current) return;
  const blob = new Blob([JSON.stringify({analysis: current, ...(repair ? {recheck: repair} : {})}, null, 2)], {type: "application/json"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "algoxray-" + current.analysis_id + ".json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
});
window.addEventListener("resize", () => {
  if (selectedWitness && !by("judgment").hidden && !by("lanterns").hidden) drawLanterns(selectedWitness);
});

request("").then(result => {
  problems = result;
  for (const problem of problems) by("problem").append(new Option(problem.title, problem.id));
  if (problems.some(problem => problem.id === "cf492b")) by("problem").value = "cf492b";
  if (problems.length) showProblem();
  else text("status", "ما في مسائل منشورة حاليًا.");
}).catch(error => text("status", error.message));
