'use strict';
const $ = id => document.getElementById(id);
const state = {problems: [], fixtures: [], problem: 'dijkstra_v1', result: null, step: 0, revealed: 0, original: false, cy: null, graphKey: '', timer: null, busy: false, mode: 'fixture', drafts: {}, filenames: {}, pinned: null, originals: {}};
const node = (tag, className, text) => { const element = document.createElement(tag); if (className) element.className = className; if (text !== undefined) element.textContent = text; return element; };
const display = value => value === undefined || value === null ? '—' : JSON.stringify(value).replaceAll('null', '∞');
const pretty = value => JSON.stringify(value, null, 2);
const problem = () => state.problems.find(p => p.id === state.problem);
const fixture = () => state.fixtures.find(f => f.id === $('fixture-select').value);
const activeCase = () => state.result?.case ? (state.original ? state.result.original_case : state.result.case) : (state.result?.manual_check?.case || state.pinned?.input || problem()?.example);
const activeEvent = () => !state.original ? state.result?.events[state.step] : null;

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    const detail = data.detail;
    const error = new Error(typeof detail === 'string' ? detail : detail?.message || JSON.stringify(detail || data));
    error.line = detail?.line; error.column = detail?.column; error.status=response.status; throw error;
  }
  return data;
}

function showError(message) { $('error-message').textContent = message; $('error-message').hidden = !message; }
function stopPlaying() { clearInterval(state.timer); state.timer = null; $('play-steps').textContent = '▶ تشغيل'; }
function setBusy(value) {
  state.busy = value;
  $('cancel-analysis').hidden = !value;
  $('cancel-analysis').disabled = !value;
  $('analyze-button').disabled = value;
  $('analyze-button').classList.toggle('busy', value);
  $('analyze-label').textContent = value ? 'جارٍ التحليل…' : 'ابدأ التحليل';
  for (const selector of ['fixture-select', 'strategy', 'seed', 'budget', 'shrink', 'manual-case', 'source-editor', 'trusted-local-code', 'mode-custom', 'mode-fixture', 'load-template', 'load-bug-example', 'import-code', 'code-file', 'case-input', 'pin-witness', 'clear-witness', 'fresh-process']) $(selector).disabled = value;
  document.querySelectorAll('[data-problem]').forEach(button => button.disabled = value);
  $('mode-custom').disabled = value || state.customCodeEnabled === false;
}

function setProblem(id) {
  if (state.busy) return;
  saveDraft(); stopPlaying(); state.pinned = null; state.problem = id; state.result = null; state.original = false; state.step = 0; state.revealed = 0;
  document.querySelectorAll('[data-problem]').forEach(button => button.classList.toggle('active', button.dataset.problem === id));
  const select = $('fixture-select'); select.replaceChildren();
  const entries = state.fixtures.filter(f => f.problem_id === id);
  for (const entry of entries) select.append(new Option(entry.name_ar, entry.id));
  const defaultId = ({dijkstra_v1:'dijkstra_premature_visited',binary_search_v1:'binary_missing_last',max_subarray_v1:'max_subarray_empty_bug'})[id];
  if (entries.some(f => f.id === defaultId)) select.value = defaultId;
  $('problem-description').textContent = problem().description_ar + ' · ' + (problem().contract_version || id);
  if (!entries.length && state.customCodeEnabled) state.mode='custom';
  $('case-input').value = pretty(problem().example);
  syncSourceMode(); renderResult(); showError('');
}

function renderSource(source) {
  const code = source?.source || '';
  $('source-name').textContent = source?.filename || (source?.id ? source.id + '.py' : 'submission.py');
  $('source-hash').textContent = source?.source_sha256 ? 'SHA256 ' + source.source_sha256.slice(0, 12) : '';
  const fragment = document.createDocumentFragment();
  code.split(/\r\n|\r|\n/).forEach((text, i) => {
    const row = node('div', 'code-line'); row.dataset.line = String(i + 1);
    row.append(node('span', 'line-number', String(i + 1)), node('span', 'line-text', text || ' ')); fragment.append(row);
  });
  $('code-container').replaceChildren(fragment);
}

function drawGraph(input) {
  const key = JSON.stringify(input);
  if (state.cy && state.graphKey === key) { updateGraph(); return; }
  state.cy?.destroy(); state.cy = null; state.graphKey = key;
  if (!input) return;
  if (!window.cytoscape) { drawFallback(input); return; }
  const elements = [];
  for (let i = 0; i < input.n; i++) elements.push({data: {id: 'n' + i, label: String(i)}, classes: i === input.source ? 'source' : ''});
  input.edges.forEach(([u, v, weight], i) => elements.push({data: {id: 'e' + i, source: 'n' + u, target: 'n' + v, label: String(weight), u, v}}));
  state.cy = window.cytoscape({container: $('graph-container'), elements,
    layout: {name: 'circle', padding: 58, startAngle: -Math.PI / 2}, userZoomingEnabled: true, userPanningEnabled: false,
    minZoom: 0.4, maxZoom: 2.5, wheelSensitivity: 0.2,
    style: [
      {selector: 'node', style: {'background-color': '#f6fafb', 'border-width': 1.5, 'border-color': '#b7ccd5', width: 43, height: 43, label: 'data(label)', color: '#587783', 'font-family': 'Consolas, monospace', 'font-size': 14, 'text-valign': 'center', 'text-halign': 'center'}},
      {selector: 'edge', style: {width: 1.4, 'line-color': '#b6cbd3', 'target-arrow-color': '#a9c2cc', 'target-arrow-shape': 'triangle', 'arrow-scale': 0.8, 'curve-style': 'bezier', label: 'data(label)', 'font-size': 11, 'font-family': 'Consolas, monospace', color: '#8aa3af', 'text-background-color': '#fff', 'text-background-opacity': 1, 'text-background-padding': '5px', 'text-rotation': 'autorotate'}},
      {selector: 'node.source', style: {'background-color': '#e1f2e9', 'border-color': '#79b59b', color: '#3b856c'}},
      {selector: 'node.mismatch', style: {'border-color': '#d49b86', 'background-color': '#fff1e9', color: '#b47761'}},
      {selector: 'node.current', style: {'border-color': '#9096bd', 'background-color': '#ececf8', color: '#676c9c'}},
      {selector: 'node.candidate', style: {'border-width': 3, 'border-color': '#7ba995'}},
      {selector: 'edge.current-edge', style: {'line-color': '#67a58b', 'target-arrow-color': '#67a58b', width: 2.6, color: '#52856e'}}
    ]});
  updateGraph();
}

function drawFallback(input) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg'); svg.setAttribute('viewBox', '0 0 600 280'); svg.setAttribute('width', '100%'); svg.setAttribute('height', '280');
  const positions = Array.from({length: input.n}, (_, i) => [300 + 110 * Math.cos(i * 2 * Math.PI / input.n), 140 + 90 * Math.sin(i * 2 * Math.PI / input.n)]);
  for (const [u, v, weight] of input.edges) {
    const line = document.createElementNS(ns, 'line'); line.setAttribute('x1', positions[u][0]); line.setAttribute('y1', positions[u][1]); line.setAttribute('x2', positions[v][0]); line.setAttribute('y2', positions[v][1]); line.setAttribute('stroke', '#b3c7cd'); svg.append(line);
    const text = document.createElementNS(ns, 'text'); text.setAttribute('x', (positions[u][0] + positions[v][0]) / 2); text.setAttribute('y', (positions[u][1] + positions[v][1]) / 2 - 5); text.setAttribute('font-size', '12'); text.setAttribute('fill', '#72909b'); text.textContent = weight; svg.append(text);
  }
  positions.forEach(([x, y], i) => {const circle = document.createElementNS(ns, 'circle'); circle.setAttribute('cx', x); circle.setAttribute('cy', y); circle.setAttribute('r', '22'); circle.setAttribute('fill', i === input.source ? '#e0f0e8' : '#f4f8fa'); circle.setAttribute('stroke', '#a5bfc7'); svg.append(circle); const label = document.createElementNS(ns, 'text'); label.setAttribute('x', x); label.setAttribute('y', y + 5); label.setAttribute('text-anchor', 'middle'); label.textContent = i; svg.append(label);});
  $('graph-container').replaceChildren(svg);
}

function updateGraph() {
  if (!state.cy) return;
  const event = activeEvent(), result = state.result;
  const local = result?.submission.adapter_id === 'dijkstra_seen_v1' && event?.function === 'solve' ? event.locals : {};
  state.cy.elements().removeClass('current candidate mismatch current-edge');
  if (result?.failure_kind === 'wrong_answer' && !state.original && result.case && Array.isArray(result.observed_output)) {
    result.observed_output.forEach((v, i) => { if (v !== result.expected_output[i]) state.cy.getElementById('n' + i).addClass('mismatch'); });
  }
  if (Number.isInteger(local.u)) state.cy.getElementById('n' + local.u).addClass('current');
  if (Number.isInteger(local.v)) state.cy.getElementById('n' + local.v).addClass('candidate');
  state.cy.edges().forEach(edge => {if (edge.data('u') === local.u && edge.data('v') === local.v) edge.addClass('current-edge');});
}

function drawArray(input) {
  const local = activeEvent()?.locals || {}, fragment = document.createDocumentFragment();
  if (!input.array.length) fragment.append(node('div', 'empty-array', 'مصفوفة فارغة · الهدف ' + input.target));
  input.array.forEach((v, i) => {
    const cell = node('div', 'array-cell');
    const known = state.result?.submission.adapter_id === 'binary_last_v1';
    const roles = activeEvent()?.function === 'solve' ? (state.result?.diagnosis?.trace_roles || (known && {lower: 'lo', upper: 'hi'})) : null;
    const lower = roles && local[roles.lower], upper = roles && local[roles.upper];
    if (Number.isInteger(lower) && Number.isInteger(upper) && i >= lower && i <= upper) cell.classList.add('in-range');
    if (known && roles && i === local.mid) cell.classList.add('current');
    if (v === input.target) cell.classList.add('target');
    const proof = state.original ? null : state.result?.witness_explanation;
    if (proof?.kind === 'max_subarray' && i >= proof.start && i < proof.end_exclusive) cell.classList.add('in-range');
    cell.append(node('strong', '', String(v)), node('small', '', String(i))); fragment.append(cell);
  });
  $('array-container').replaceChildren(fragment);
}

function renderCase() {
  const input = activeCase(); if (!input) return;
  const kind=problem()?.visualization;
  const graph = kind==='graph' && Number.isInteger(input.n) && Array.isArray(input.edges);
  const array = kind==='array' && Array.isArray(input.array);
  $('graph-container').hidden = !graph; $('array-container').hidden = !array;
  $('generic-case').hidden = graph || array; if(!graph && !array) $('generic-case').textContent=pretty(input);
  $('graph-title').textContent = graph ? 'استكشف الغراف' : array ? 'استكشف المصفوفة' : 'استكشف المدخل (JSON)';
  $('case-size').textContent = graph ? `${input.n} nodes / ${input.edges.length} edges` : array ? `${input.array.length} items${input.target === undefined ? "" : " / target " + input.target}` : "";
  $('case-json').textContent = pretty(input);
  $('graph-caption').textContent = !state.result?.case ? (state.result?.manual_check ? 'المدخل الذي فُحص' : state.pinned ? 'الشاهد المحفوظ لإعادة الفحص' : 'معاينة · دون نتيجة تحليل') : state.original ? 'الشاهد الأصلي · النتائج والتتبع للحالة المصغرة' : 'شاهد مؤكد · حالة التشغيل المتتبّعة';
  $('show-reduced').classList.toggle('active', !state.original); $('show-original').classList.toggle('active', state.original);
  $('show-original').disabled = !state.result?.original_case;
  if (graph) drawGraph(input); else if(array) drawArray(input);
}

function renderStep() {
  const events = state.result?.events || [], event = activeEvent();
  $('step-range').max = Math.max(0, events.length - 1); $('step-range').value = state.step;
  $('step-count').textContent = `${events.length ? state.step + 1 : 0} / ${events.length}`;
  for (const id of ['previous-step', 'next-step', 'play-steps', 'step-range']) $(id).disabled = !events.length || state.original;
  $('previous-step').disabled ||= state.step === 0;
  $('next-step').disabled ||= state.step === events.length - 1;
  $('step-description').textContent = state.original ? 'عد إلى الحالة المصغرة لمشاهدة تنفيذها الفعلي.' : event ? `السطر ${event.line} · ${event.function} · ${event.frame_id || '—'}${event.parent_frame_id ? ' ← ' + event.parent_frame_id : ''} · ${event.kind === 'line' ? 'الحالة قبل التنفيذ' : event.kind}` : 'لا يوجد تتبع مسجّل لهذا التشغيل.';
  $('code-container').querySelectorAll('.current').forEach(line => line.classList.remove('current'));
  if (event) {
    const row = $('code-container').querySelector(`[data-line="${event.line}"]`);
    row?.classList.add('current');
    if (row) $('code-container').scrollTop = Math.max(0, row.offsetTop - 100);
  }
  const vars = $('variables-container'); vars.replaceChildren();
  const entries = Object.entries(event?.locals || {});
  if (!entries.length) vars.append(node('div', 'muted-placeholder', state.original ? 'الخطوات المسجلة تخص الحالة المصغرة.' : 'لا توجد متغيرات مختارة عند هذه الخطوة.'));
  for (const [key, value] of entries) {const row = node('div', 'variable-row'); row.append(node('span', 'variable-name', key), node('span', 'variable-value', display(value))); vars.append(row);}
  renderCase();
}

function renderHints() {
  const container = $('hints-container'); container.replaceChildren();
  const hints = state.result?.hints || [];
  if (!hints.length) {
    const empty = node('div', 'empty-hints'); empty.append(node('span', '', '✧'), node('h3', '', state.result ? 'لا يوجد شاهد مؤكد لتفسيره' : 'الفهم يبدأ بمثال'), node('p', '', state.result ? 'انتهاء الميزانية لا يثبت صحة الحل.' : 'شغّل التحليل لإظهار التلميحات المرتبطة بالدليل.')); container.append(empty);
  }
  for (const hint of hints.slice(0, state.revealed)) {
    const card = node('article', 'hint-card'); card.dataset.tier = hint.tier;
    const paragraph = node('p');
    let cursor = 0;
    for (const match of hint.text.matchAll(/\d+ → \d+/g)) {
      paragraph.append(document.createTextNode(hint.text.slice(cursor, match.index)));
      const isolated = node('bdi', '', match[0]); isolated.dir = 'ltr'; paragraph.append(isolated);
      cursor = match.index + match[0].length;
    }
    paragraph.append(document.createTextNode(hint.text.slice(cursor)));
    card.append(node('span', 'hint-tier', hint.tier + (hint.kind === 'educational_question' ? ' · سؤال للتفكير' : hint.tier === 'H4' ? ' · اتجاه للمراجعة' : ' · ملاحظة مدعومة')), paragraph);
    const ids = hint.event_ids || hint.claim_ids.flatMap(id => state.result.claims.find(c => c.claim_id === id)?.event_ids || []);
    if (ids.length) {const button = node('button', '', 'افتح الحدث الذي يدعم التلميح ↗'); button.type = 'button'; button.addEventListener('click', () => { const i = state.result.events.findIndex(e => e.event_id === ids[0]); if (i >= 0) {state.original = false; state.step = i; stopPlaying(); renderStep();} }); card.append(button);}
    container.append(card);
  }
  $('reveal-hint').disabled = state.revealed >= hints.length;
  $('reveal-hint').textContent = !hints.length ? 'التلميحات تظهر عند تأكيد الفشل' : state.revealed === 0 ? 'اكشف التلميح الأول ←' : state.revealed >= hints.length ? 'كل التلميحات المتاحة ظاهرة' : 'أحتاج تلميحاً إضافياً ←';
  $('diagnostic-note').textContent = state.result?.diagnostic_status === 'supported' ? 'ملاحظة محددة مدعومة بالمصدر والتنفيذ المسجّل؛ افحص الدليل وحدودها.' : state.result?.status === 'witness_found' ? 'أكدنا الفشل؛ التشخيص المحدد غير متاح بدليل كافٍ لهذا المصدر.' : 'التشخيص المحدد يتطلب أحداثاً تدعمه.';
}

function renderResult() {
  const result = state.result, found = result?.status === 'witness_found';
  $('status-banner').className = 'status-banner' + (found ? ' found' : result ? ' inconclusive' : '');
  $('status-title').textContent = found ? ({wrong_answer: 'وجدنا حالة تؤكد اختلاف النتيجة', exception: 'وجدنا حالة يتوقف عليها الحل', timeout: 'وجدنا حالة تتجاوز مهلة التشغيل', contract_violation: 'وجدنا خرجاً يخالف عقد المسألة'}[result.failure_kind]) : result ? (result.status === 'cancelled' ? 'أُلغي التحليل' : result.status === 'infrastructure_error' ? 'تعطل عامل التنفيذ — لا حكم على الحل' : result.status === 'inconclusive' ? 'لم نجد خطأ ضمن الميزانية' : 'تعذر استكمال التحقق') : 'جاهز لاكتشاف حالة الفشل';
  $('status-description').textContent = found ? `أعيد الفشل ${result.verification.replay_matches} مرات من ${result.verification.replay_attempts}. يمكنك الآن فحص الحالة والتنقل في تنفيذها.` : result ? (result.status === 'cancelled' ? 'أوقف العامل ولم يصدر حكم على الحل.' : result.error || 'هذه نتيجة بحث محدود؛ لا تمثل إثباتاً لصحة الحل.') : 'اختر حلاً ثم ابدأ التحليل. الرسم الحالي معاينة للمدخل التوضيحي فقط.';
  $('status-symbol').textContent = found ? '↳' : result ? '◷' : '◌';
  $('run-label').textContent = result ? 'RUN ' + result.run_id.slice(-10).toUpperCase() : 'NO RUN YET';
  $('run-label').title = result?.run_id || '';
  $('actual-output').textContent = result?.failure_kind === 'exception' ? result.exception.type : display(result?.manual_check?.status === 'pass' ? result.manual_check.observed : result?.observed_output);
  $('expected-output').textContent = display(result?.manual_check?.status === 'pass' ? result.manual_check.expected : result?.expected_output);
  $('trace-badge').textContent = ({complete: 'تنفيذ مسجّل', truncated: 'تتبع محدود', failed: 'تعذر التتبع', not_run: 'دون تتبع'}[result?.trace_status]) || 'في انتظار التشغيل';
  $('download-evidence').disabled = !result;
  $('run-statistics').textContent = result ? `${result.statistics.discovery_candidates} مرشح قبل الاكتشاف · ${result.statistics.total_solver_calls} تشغيل للحل · ${result.events.length} حدث مسجّل · ${Math.round(result.statistics.elapsed_ms)} ms` : 'يمكنك تنزيل المدخل والنتيجة والتتبع والتلميحات في ملف واحد بعد التشغيل.';
  if (state.pinned && result?.manual_check?.status === 'pass') {
    $('status-title').textContent = 'التعديل اجتاز الشاهد المحفوظ';
    $('status-description').textContent = 'طابق الناتج عقد المسألة على هذا المدخل. ابدأ بحثاً جديداً لفحص مدخلات أخرى.';
  }
  renderHints(); renderStep(); renderDiagnosis(); renderWitness();
}

$('cancel-analysis').addEventListener('click', async () => {
  const id = state.analysisId;
  if (!state.busy || !id) return;
  $('cancel-analysis').disabled = true;
  $('status-description').textContent='جارٍ طلب إيقاف التحليل…';
  const active=()=>state.busy && state.analysisId===id;
  // The local-session request may still be pending when the user clicks cancel.
  // Retry only the not-yet-registered response; never claim cancellation on 404.
  const deadline=Date.now()+10000;
  while(active()){
    try {
      await request('/api/analysis/'+id+'/cancel',{method:'POST'});
      if(active()) $('status-description').textContent='طُلب إيقاف العامل…';
      return;
    } catch(error){
      if(!active()) return;
      if(error.status!==404 || Date.now()>=deadline){
        showError(error.message); $('cancel-analysis').disabled=false; return;
      }
      await new Promise(resolve=>setTimeout(resolve,100));
    }
  }
});
async function runAnalysis(event) {
  event.preventDefault(); if (state.busy) return; stopPlaying(); showError('');
  let manual = null;
  try {if ($('manual-case').checked) { manual = JSON.parse($('case-input').value); if (!manual || typeof manual !== 'object' || Array.isArray(manual)) throw Error(); }} catch {showError('صيغة JSON غير صالحة. راجع الفواصل والأقواس.'); return;}
  const seed = Number($('seed').value), budget = Number($('budget').value);
  if (!Number.isInteger(seed) || seed < 0 || seed > 4294967295 || !Number.isInteger(budget) || budget < 1 || budget > 500) {showError('راجع البذرة وميزانية المرشحات.'); return;}
  const custom = state.mode === 'custom', source = editorSource();
  if (!custom && !fixture()) {showError('لا يوجد مثال مسجل لهذه المسألة. استخدم كودك المحلي إن كان متاحاً.'); return;}
  if (custom && !source.trim()) {showError('الصق كود Python أو افتح ملف .py أولاً.'); $('source-editor').focus(); return;}
  if (custom && new TextEncoder().encode(source).length > 32768) {showError('حجم الكود الأقصى 32 KiB.'); return;}
  if (custom && !$('trusted-local-code').checked) {showError('فعّل تأكيد الكود المحلي الموثوق أسفل المحرر أولاً.'); return;}
  state.result = null; state.step = 0; state.revealed = 0; state.original = false; renderResult();
  setBusy(true); $('status-title').textContent = 'جارٍ البحث والتحقق من الشاهد…'; $('status-description').textContent = 'التصغير وإعادة التشغيل والتتبع مراحل حقيقية وقد تستغرق بعض الوقت.';
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 75000);
  const id = Array.from(crypto.getRandomValues(new Uint8Array(16)), n=>n.toString(16).padStart(2,'0')).join('');
  state.analysisId = id;
  try {
    const payload = {analysis_id: id, problem_id: state.problem, options: {seed, strategy: $('strategy').value, max_examples: budget, shrink: $('shrink').checked, diagnostic_samples: 3, fresh_process: $('fresh-process').checked}, case: manual};
    const headers = {'Content-Type': 'application/json'};
    if (custom) {
      const session = await request('/api/session');
      headers['X-AlgoXRay-Token'] = session.custom_code_token;
      payload.source = source; payload.trusted_local_code = true;
    } else payload.fixture_id = fixture().id;
    const result = await request('/api/analyze', {method: 'POST', headers, signal: controller.signal, body: JSON.stringify(payload)});
    state.result = result; state.step = 0; state.revealed = 0; state.original = false;
    const first = result.diagnosis?.event_ids?.[0];
    if (first) state.step = Math.max(0, result.events.findIndex(e => e.event_id === first));
    renderSource(result.submission); renderResult();
  } catch (error) {
    renderResult(); showError(error.name === 'AbortError' ? 'انتهت مهلة انتظار الواجهة. تحقق من سجل المحرك قبل بدء تحليل آخر.' : 'تعذر التحليل: ' + error.message + (error.line ? ' — السطر ' + error.line : ''));
    if (error.line && custom) {renderSource({source, filename: state.filenames[state.problem] || 'submission.py'}); jumpToEditorLine(error.line);}
  } finally {clearTimeout(timer); state.analysisId = null; setBusy(false);}
}


async function loadOptionBBenchmarks(revision='v1') {
  const target = $(revision==='v1'?'option-b-benchmark-state':'option-b-v2-state'), table = $(revision==='v1'?'option-b-benchmark-table':'option-b-v2-table');
  table.replaceChildren(); target.replaceChildren(node('h2', '', 'تقييم Option B · '+revision));
  try {
    const data = await request('/api/option-b/benchmark-summary?revision='+revision);
    if (data.status === 'not_run') {target.append(node('p', 'report-intro', 'لا توجد نتائج منفذة لهذه النسخة بعد. الأرقام التاريخية أعلاه منفصلة.')); return;}
    target.append(node('p', 'report-intro', `${data.run_count} تشغيل على ${data.corpus_count} ملف حلّ · التحكيم البشري: ${data.human_review}`));
    const t = node('table', 'results-table'), head = node('thead'), hr = node('tr'), body = node('tbody');
    for (const label of ['المسألة','الطريقة','كشف الخطأ','اتهام الصحيح','تشخيص مدعوم','تصغير']) hr.append(node('th','',label));
    head.append(hr); t.append(head);
    for (const r of data.rows) {const tr = node('tr'); for (const v of [r.problem,r.variant,`${r.buggy_found}/${r.buggy_runs}`,`${r.control_accusations}/${r.control_runs}`,r.specific,r.reduced]) tr.append(node('td','',String(v))); body.append(tr);}
    t.append(body); table.append(t,node('p','report-note','هذه نتائج تقنية على ملفات مصدر؛ لا تمثل طلاباً مستقلين أو فائدة تعليمية مقاسة.'));
  } catch(error) {target.append(node('p','error-message',error.message));}
}

async function loadBenchmarks() {
  void loadOptionBBenchmarks('v1');
  void loadOptionBBenchmarks('v2');
  const target = $('benchmark-state'), table = $('benchmark-table');
  target.replaceChildren(node('p', 'report-intro', 'تحميل بيانات التجارب…')); table.replaceChildren();
  try {
    const data = await request('/api/benchmark-summary');
    if (data.status === 'not_run') {target.replaceChildren(node('h2', '', 'لم تُشغّل التجارب بعد'), node('p', 'report-intro', 'شغّل benchmarks/run.py لحفظ نتائج فعلية. لن تظهر أرقام تقديرية مكان البيانات.')); return;}
    target.replaceChildren(node('h2', '', data.release ? 'تقييم تاريخي محفوظ · ' + data.release : 'تقييم تاريخي محفوظ'), node('p', 'report-intro', `${data.total_runs} تشغيل على ${data.fixture_count} حلول، ببذور وإعدادات محفوظة.`), node('p', 'report-caption', `Python ${data.environment.python} / ${data.created_at} / ${data.codebase_sha256.slice(0, 12)}`));
    const t = node('table', 'results-table'), head = node('thead'), header = node('tr');
    for (const label of ['المسألة', 'الطريقة', 'اكتشاف الأخطاء', 'اتهام الصحيح', 'وسيط الاكتشاف']) header.append(node('th', '', label)); head.append(header); t.append(head);
    const body = node('tbody');
    for (const row of data.rows) {const tr = node('tr'); tr.append(node('td', '', row.problem_id === 'dijkstra_v1' ? 'Dijkstra' : 'Binary Search'), node('td', '', row.strategy), node('td', 'numeric', `${row.buggy_found} / ${row.buggy_runs}`), node('td', 'numeric', `${row.control_accusations} / ${row.control_runs}`), node('td', 'numeric', row.median_discovery_ms === null ? '—' : `${row.median_discovery_ms.toFixed(1)} ms`)); body.append(tr);}
    if (data.audit) target.append(node('p', 'report-caption', `تشخيص مرتبط بالتنفيذ في ${data.audit.specific}/${data.audit.witnesses} شواهد · امتناع في ${data.audit.abstained} · تدقيق آلي`));
    t.append(body); table.append(t, node('p', 'report-note', 'تجارب على برامج محدودة؛ تكرار البذور لا يزيد عدد الحلول المستقلة. وسيط زمن الاكتشاف محسوب للتشغيلات المكتشفة فقط، والتصغير مستبعد من المقارنة. هذه ليست دراسة تعلم مع طلاب.'));
  } catch (error) {target.replaceChildren(node('p', 'error-message', error.message));}
}


function saveDraft() {
  if (state.mode === 'custom' && $('source-editor')) state.drafts[state.problem] = $('source-editor').value;
}
function editorSource() {
  const original = state.originals[state.problem];
  const visible = $('source-editor').value;
  return original !== undefined && original.replace(/^\uFEFF/, '').replace(/\r\n|\r/g, '\n') === visible ? original : visible;
}
function previewCustom() {
  return {source: editorSource(), filename: state.filenames[state.problem] || 'submission.py'};
}
function invalidateResult() {
  if (state.busy) return;
  stopPlaying(); state.result = null; state.step = 0; state.revealed = 0; state.original = false;
  renderSource(state.mode === 'custom' ? previewCustom() : fixture()); renderResult(); showError('');
}
function updateEditor() {
  const text = $('source-editor').value;
  $('editor-lines').textContent = Array.from({length: text.split('\n').length}, (_, i) => i + 1).join('\n');
  $('source-size').textContent = new TextEncoder().encode(editorSource()).length + ' / 32768 bytes';
}
function syncSourceMode() {
  const custom = state.mode === 'custom';
  $('custom-source-panel').hidden = !custom;
  document.querySelector('.fixture-control').hidden = custom;
  document.querySelector('.control-grid').classList.toggle('custom-mode', custom);
  for (const name of ['custom', 'fixture']) {
    $('mode-' + name).classList.toggle('active', state.mode === name);
    $('mode-' + name).setAttribute('aria-pressed', String(state.mode === name));
  }
  if (custom) {
    $('source-editor').value = state.drafts[state.problem] || '';
    $('editor-filename').textContent = state.filenames[state.problem] || 'submission.py';
    $('editor-contract').textContent = !['max_subarray_v1','binary_search_v1','dijkstra_v1'].includes(state.problem) ? problem().description_ar : state.problem === 'max_subarray_v1' ? 'استقبل payload["array"] وأعد أكبر مجموع لمقطع متصل غير فارغ.' : state.problem === 'binary_search_v1'
      ? 'الدالة solve(payload) تستقبل payload["array"] المرتبة وpayload["target"]، وتعيد فهرساً مطابقاً أو -1. طول المصفوفة 0–32؛ القيم من -20 إلى 20. استخدم return بدلاً من input أو طباعة الجواب.'
      : 'الدالة solve(payload) تستقبل n وedges وsource، وتعيد قائمة المسافات. الغراف موجه بسيط، 2–8 عقد، حتى 20 حافة فريدة دون حلقات، وأوزان صحيحة 1–20. استخدم return؛ المسافة غير القابلة للوصول يجب أن تكون None.';
    updateEditor();
  }
  renderSource(custom ? previewCustom() : fixture());
}
function setSourceMode(mode) {
  if (state.busy || (mode === 'custom' && state.customCodeEnabled === false)) return;
  saveDraft(); state.pinned = null; state.mode = mode; syncSourceMode(); invalidateResult();
}
function jumpToEditorLine(line) {
  const editor = $('source-editor'), lines = editor.value.split('\n');
  const start = lines.slice(0, Math.max(0, line - 1)).reduce((n, value) => n + value.length + 1, 0);
  editor.focus(); editor.setSelectionRange(start, start + (lines[line - 1]?.length || 0));
  editor.scrollTop = Math.max(0, (line - 3) * 24);
  $('editor-lines').scrollTop = editor.scrollTop;
  $('code-container').querySelectorAll('.review-line').forEach(row => row.classList.remove('review-line'));
  $('code-container').querySelector('[data-line="' + line + '"]')?.classList.add('review-line');
}
function renderDiagnosis() {
  const result = state.result, found = result?.status === 'witness_found';
  $('diagnosis-summary').hidden = !found;
  if (!found) return;
  const observation = result.diagnosis, supported = observation?.status === 'supported';
  const ranked = $('ranked-observations'); ranked.replaceChildren();
  for (const item of result.ranked_observations || []) {
    const button = node('button', 'secondary-button', `السطر ${item.line} · ملاحظة مسجلة (${item.event_ids.length})`);
    button.type = 'button'; button.addEventListener('click', () => {
      const index = result.events.findIndex(e => e.event_id === item.event_ids[0]);
      if (index >= 0) { state.original = false; state.step = index; stopPlaying(); renderStep(); }
    }); ranked.append(button);
  }
  if (ranked.children.length) ranked.prepend(node('p', '', 'مواضع مرتبطة بالدليل، وليست إثباتاً لسبب الخطأ.'));
  const spectrum = $('suspicion-ranking'); spectrum.replaceChildren();
  if (result.suspicion_ranking?.length) {
    spectrum.append(node('p','','ترتيب اشتباه إحصائي من تشغيلات ناجحة وفاشلة محدودة، وليس إثباتاً للسبب.'));
    for (const row of result.suspicion_ranking) {const b=node('button','secondary-button',`السطر ${row.line} · ${row.failed_covered}/${row.failed_total} فشل · ${row.passed_covered}/${row.passed_total} نجاح`); b.type='button'; b.addEventListener('click',()=>{const i=result.events.findIndex(e=>e.event_id===row.event_id); if(i>=0){state.original=false;state.step=i;stopPlaying();renderStep();}}); spectrum.append(b);}
  }
  const links = $('dynamic-dependencies'); links.replaceChildren();
  if(result.dynamic_dependencies?.length){
    links.append(node('p','','قراءات وكتابات عددية متحققة بين حدثين متتاليين (ليست سبباً مثبتاً).'));
    for(const link of result.dynamic_dependencies.slice(0,12)){
      const reads=Object.entries(link.reads).map(([k,v])=>k+'='+v).join(', ');
      const b=node('button','secondary-button','L'+link.line+': '+reads+' → '+link.write.name+'='+link.write.value); b.type='button';
      b.addEventListener('click',()=>{const i=result.events.findIndex(e=>e.event_id===link.after_event_id);if(i>=0){state.original=false;state.step=i;stopPlaying();renderStep();}});links.append(b);
    }
  }
  $('diagnosis-badge').textContent = supported ? 'موضع مدعوم بالتنفيذ' : 'شاهد مؤكد · افحص التتبع';
  $('diagnosis-text').textContent = supported ? observation.text : 'وجدنا مدخلاً يكشف فشل الحل، لكن لا يوجد دليل كافٍ لتحديد سبب منطقي بعينه في هذا الكود.';
  $('diagnosis-direction').textContent = supported ? (result.hints.find(h => h.tier === 'H4')?.text || 'افتح الحدث وافحص القيم المسجلة.') : 'قارن المتوقع بالناتج وتابع المتغيرات خطوة بخطوة. آخر سطر منفذ ليس بالضرورة سبب الخطأ.';
  $('jump-to-diagnosis').disabled = !result.events.length;
  $('jump-to-diagnosis').textContent = supported ? 'افتح السطر في التتبع ↗' : 'ابدأ تتبع الحالة ↗';
}
function jumpToDiagnosis() {
  const result = state.result;
  if (!result?.events.length) return;
  const first = result.diagnosis?.event_ids?.[0];
  state.step = first ? Math.max(0, result.events.findIndex(e => e.event_id === first)) : 0;
  state.original = false; stopPlaying(); renderStep();
  document.querySelector('.code-panel').scrollIntoView({behavior: 'smooth', block: 'center'});
}
function loadEditorExample(buggy) {
  if (state.busy) return;
  delete state.originals[state.problem];
  const id = ({binary_search_v1:'binary_missing_last',dijkstra_v1:'dijkstra_premature_visited',max_subarray_v1:'max_subarray_empty_bug'})[state.problem];
  const example = state.fixtures.find(f => f.id === id)?.source || state.fixtures.find(f=>f.problem_id===state.problem && f.label==='buggy')?.source || '';
  $('source-editor').value = !['max_subarray_v1','binary_search_v1','dijkstra_v1'].includes(state.problem) && !buggy ? 'def solve(payload):\n    raise NotImplementedError\n' : buggy ? example.replace(/\blo\b/g, 'left').replace(/\bhi\b/g, 'right').replace(/\barr\b/g, 'array')
    : state.problem === 'max_subarray_v1' ? 'def solve(payload):\n    array = payload["array"]\n    return array[0]\n' : state.problem === 'binary_search_v1' ? 'def solve(payload):\n    array = payload["array"]\n    target = payload["target"]\n    # اكتب خوارزمية البحث هنا\n    return -1\n'
    : 'def solve(payload):\n    n = payload["n"]\n    edges = payload["edges"]\n    source = payload["source"]\n    # اكتب الحل وأعد قائمة المسافات\n    return [None] * n\n';
  state.filenames[state.problem] = buggy ? 'example_with_bug.py' : 'submission.py';
  $('editor-filename').textContent = state.filenames[state.problem];
  saveDraft(); updateEditor(); invalidateResult();
}
$('mode-custom').addEventListener('click', () => setSourceMode('custom'));
$('mode-fixture').addEventListener('click', () => setSourceMode('fixture'));
$('source-editor').addEventListener('input', () => {saveDraft(); updateEditor(); invalidateResult();});
$('source-editor').addEventListener('scroll', () => $('editor-lines').scrollTop = $('source-editor').scrollTop);
$('source-editor').addEventListener('keydown', event => {
  if (event.key === 'Tab') {event.preventDefault(); event.target.setRangeText('    ', event.target.selectionStart, event.target.selectionEnd, 'end'); saveDraft(); updateEditor(); invalidateResult();}
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {event.preventDefault(); $('analysis-form').requestSubmit();}
});
$('load-template').addEventListener('click', () => loadEditorExample(false));
$('load-bug-example').addEventListener('click', () => loadEditorExample(true));
$('import-code').addEventListener('click', () => $('code-file').click());
$('code-file').addEventListener('change', async event => {
  const file = event.target.files?.[0]; if (!file || state.busy) return;
  if (!file.name.toLowerCase().endsWith('.py') || file.size > 32768) {showError('اختر ملف Python بامتداد .py وحجم لا يتجاوز 32 KiB.'); event.target.value = ''; return;}
  const problemId = state.problem;
  try {
    const source = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(await file.arrayBuffer());
    if (problemId !== state.problem || state.busy || state.mode !== 'custom') return;
    state.originals[problemId] = source;
    $('source-editor').value = source.replace(/^\uFEFF/, ''); state.filenames[problemId] = file.name; $('editor-filename').textContent = file.name;
    saveDraft(); updateEditor(); invalidateResult();
  } catch {showError('تعذر قراءة الملف. احفظه بترميز UTF-8 وحاول مجدداً.');}
  finally {event.target.value = '';}
});
$('jump-to-diagnosis').addEventListener('click', jumpToDiagnosis);

document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {stopPlaying(); document.querySelectorAll('.view').forEach(view => view.hidden = view.id !== 'view-' + button.dataset.view); document.querySelectorAll('[data-view]').forEach(item => item.classList.toggle('active', item === button)); $('breadcrumb-current').textContent = button.textContent.trim(); if (button.dataset.view === 'experiments') loadBenchmarks(); if (button.dataset.view === 'lab') setTimeout(() => state.cy?.resize(), 0);}));
document.querySelectorAll('[data-problem]').forEach(button => button.addEventListener('click', () => setProblem(button.dataset.problem)));
$('fixture-select').addEventListener('change', () => {stopPlaying(); state.result = null; state.step = 0; state.revealed = 0; state.original = false; renderSource(fixture()); renderResult(); showError('');});
$('analysis-form').addEventListener('submit', runAnalysis);
$('manual-case').addEventListener('change', () => $('case-input-label').hidden = !$('manual-case').checked);
$('show-original').addEventListener('click', () => {stopPlaying(); state.original = true; renderStep();});
$('show-reduced').addEventListener('click', () => {state.original = false; renderStep();});
$('previous-step').addEventListener('click', () => {stopPlaying(); state.step = Math.max(0, state.step - 1); renderStep();});
$('next-step').addEventListener('click', () => {stopPlaying(); state.step = Math.min(state.result.events.length - 1, state.step + 1); renderStep();});
$('step-range').addEventListener('input', () => {stopPlaying(); state.step = Number($('step-range').value); renderStep();});
$('play-steps').addEventListener('click', () => {if (state.timer) {stopPlaying(); return;} if (state.step >= state.result.events.length - 1) state.step = 0; $('play-steps').textContent = '❚❚ إيقاف'; state.timer = setInterval(() => {if (state.step >= state.result.events.length - 1) {stopPlaying(); return;} state.step++; renderStep();}, 450);});
$('reveal-hint').addEventListener('click', () => {state.revealed++; renderHints();});
$('download-evidence').addEventListener('click', () => {if (!state.result) return; const url = URL.createObjectURL(new Blob([pretty(state.result)], {type: 'application/json;charset=utf-8'})); const link = node('a'); link.href = url; link.download = 'algoxray_' + state.result.run_id + '.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);});
$('refresh-benchmarks').addEventListener('click', loadBenchmarks);
$('case-input').addEventListener('input', () => {state.pinned = null; invalidateResult();});
for (const id of ['seed', 'budget']) $(id).addEventListener('input', invalidateResult);
$('manual-case').addEventListener('change', () => {state.pinned = null; invalidateResult();});
for (const id of ['strategy', 'shrink']) $(id).addEventListener('change', () => {state.pinned = null; invalidateResult();});
window.addEventListener('resize', () => state.cy?.resize());

Promise.all([request('/api/health'), request('/api/problems'), request('/api/fixtures')]).then(([health, problems, fixtures]) => {
  state.problems = problems; state.fixtures = fixtures;
  $('author-nav').hidden = !health.custom_code;
  $('author-problem').replaceChildren(...problems.map(p=>new Option(p.name,p.id)));
  updateAuthorContract();
  const tabs = document.querySelector('.problem-tabs'); tabs.replaceChildren();
  problems.forEach((p,i) => {const button = node('button','problem-tab'); button.type = 'button'; button.dataset.problem = p.id; button.append(node('span','',String(i+1).padStart(2,'0')),document.createTextNode(p.name)); button.addEventListener('click',()=>setProblem(p.id)); tabs.append(button);});
  state.customCodeEnabled = health.custom_code;
  if (!health.custom_code) {
    state.mode = 'fixture';
    $('mode-custom').disabled = true;
    $('mode-custom').title = 'Custom code is disabled on this server';
  }
  $('connection-dot').classList.add('ready'); $('connection-text').textContent = 'المحرك متصل'; setProblem(state.problem);
}).catch(error => {$('connection-text').textContent = 'المحرك غير متاح'; showError('تعذر تحميل المحرك: ' + error.message); $('analyze-button').disabled = true;});

function renderWitness() {
  const pin = state.pinned, result = state.result, proof = result?.witness_explanation;
  $('witness-panel').hidden = !pin && !result?.case;
  $('pin-witness').hidden = !!pin || !result?.case;
  $('clear-witness').hidden = !pin;
  $('witness-heading').textContent = pin ? 'إعادة فحص الشاهد المحفوظ' : 'دليل من المدخل المصغّر';
  const detail = $('witness-detail'), values = $('witness-values');
  values.textContent = '';
  if (pin) {
    detail.textContent = 'عدّل الكود ثم ابدأ التحليل. ستُفحص نفس القيم التي فشل عليها الإصدار السابق.';
    values.textContent = 'previous ' + pin.hash.slice(0, 12) + '  ·  ' + JSON.stringify(pin.input);
  } else if (proof?.kind === 'shortest_path') {
    detail.textContent = 'هذا مسار بأقل كلفة وفق المرجعين. قارِن مجموع أوزان حوافه بالمسافة التي أعادها حلّك.';
    values.textContent = proof.vertices.join(' → ') + '    |    ' + (proof.weights.join(' + ') || '0') + ' = ' + proof.cost + '    |    returned ' + (proof.returned ?? '∞');
  } else if (proof?.kind === 'unreachable') {
    detail.textContent = 'تتبع الحواف الموجهة من المصدر يحصر العقد التي يمكن الوصول إليها. العقدة المختلفة خارج هذه المجموعة.';
    values.textContent = 'source ' + proof.source + '  ·  reachable {' + proof.reachable_vertices.join(', ') + '}  ·  target ' + proof.target;
  } else if (proof?.kind === 'max_subarray') {
    detail.textContent = 'هذا مقطع متصل غير فارغ يحقق أكبر مجموع وفق مرجعين مستقلين.';
    values.textContent = proof.segment.join(' + ') + ' = ' + proof.sum + ' · returned ' + proof.returned;
  } else if (proof?.kind === 'membership') {
    detail.textContent = 'قارن الفهرس الذي أعاده الحل بكل مواقع الهدف في الشاهد. يقبل المدقّق أي موقع مطابق.';
    values.textContent = 'target ' + proof.target + '  ·  indices [' + proof.matching_indices.join(', ') + ']  ·  returned ' + proof.returned;
  } else {
    detail.textContent = 'يمكنك اختبار تعديل على المدخل الذي أعاد إنتاج الفشل.';
  }
}
$('pin-witness').addEventListener('click', () => {
  const result = state.result;
  if (!result?.case || state.busy) return;
  state.pinned = {input: result.case, hash: result.submission.source_sha256};
  if (state.mode === 'fixture') {
    state.mode = 'custom';
    state.originals[state.problem] = result.submission.source;
    state.drafts[state.problem] = result.submission.source.replace(/^\uFEFF/, '');
    state.filenames[state.problem] = result.submission.filename;
    syncSourceMode();
  }
  $('manual-case').checked = true;
  $('case-input-label').hidden = false;
  $('case-input').value = pretty(result.case);
  $('shrink').checked = false;
  invalidateResult();
  $('source-editor').focus();
});
$('clear-witness').addEventListener('click', () => {
  state.pinned = null;
  $('manual-case').checked = false;
  $('case-input-label').hidden = true;
  $('shrink').checked = true;
  invalidateResult();
});

function updateAuthorContract(){
  const p=state.problems.find(p=>p.id===$('author-problem').value);
  if(!p) return;
  $('author-contract').textContent=p.description_ar+' · '+p.id;
  $('author-controls').value=pretty([{case:p.example,expected:null}]);
  $('author-result').textContent='Enter an independently known expected answer before running.';
}
$('author-problem').addEventListener('change',updateAuthorContract);
$('author-form').addEventListener('submit',async e=>{
  e.preventDefault(); $('author-run').disabled=true; $('author-result').textContent='Checking…';
  try{
    const controls=JSON.parse($('author-controls').value);
    const session=await request('/api/session');
    const report=await request('/api/packages/review',{method:'POST',headers:{'Content-Type':'application/json','X-AlgoXRay-Token':session.custom_code_token},body:JSON.stringify({problem_id:$('author-problem').value,controls})});
    $('author-result').textContent=pretty(report);
  }catch(error){$('author-result').textContent=error.message;}
  finally{$('author-run').disabled=false;}
});
