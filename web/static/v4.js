"use strict";
const $=id=>document.getElementById(id);
let token="",demos={},activeDemo="hamburgers",result=null,side="student",index=0,sources={},busy=false,analysisId=null,profileSelection=null,activeIntake=null,preparedStatement=null,benchmarkResult=null;
async function api(path,body){
 const opts=body===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json","X-AlgoXRay-Token":token},body:JSON.stringify(body)};
 const response=await fetch(path,opts);const data=await response.json();if(!response.ok){const error=Error(typeof data.detail==="string"?data.detail:JSON.stringify(data.detail));error.payload=data.detail;throw error}return data;
}
function msg(id,value){$(id).textContent=value}
function aiOptions(){return {model:$("model").value,cloud_consent:$("cloud-consent").checked,use_cache:$("use-cache").checked&&$("model").value.startsWith("qwen2.5-coder:")}}
async function refreshModels(){const h=await api("/api/v4/health");msg("health","Ollama: "+h.model.status+" · "+h.model.models.join(", ")+" | Gemini: "+(h.gemini.configured?"key configured":"key missing")+" | OpenRouter: "+(h.openrouter.configured?"key configured":"key missing")+" | Groq: "+(h.groq.configured?"key configured":"key missing"));msg("cache-state","Cache: "+h.cache.entries+"/"+h.cache.max_entries+" · "+h.cache.bytes+" bytes | Qwen Cloud: "+h.qwen_cloud.configuration_state);const q=({...h.gemini.budget,...h.openrouter.budget,...h.groq.budget,...h.qwen_cloud.budget})[$("model").value];msg("quota",q?"طلبات الموقع خلال آخر 24 ساعة: "+q.local_attempts_24h+"/"+q.local_cap_24h+" · آخر دقيقة: "+q.local_attempts_60s+"/"+q.local_cap_60s+" (ليست الحصة المتبقية لدى المزود)":"النموذج المحلي لا يستهلك حصة سحابية");}
$("refresh-models").onclick=()=>refreshModels().catch(e=>msg("health",e.message));
$("model").onchange=()=>{$("cloud-consent").checked=false;refreshModels().catch(e=>msg("health",e.message))};

function setBusy(value){busy=value;for(const id of ["candidate","patch-reviewed","package","reviewed","trusted","packages","demo","generator","guided","spectrum","count","reduce-count","observe-run","plain-benchmark","scaling-benchmark","manual-stdin","manual-expected","sample-reviewed","sample-comparison","size-field","size-values","timing-repetitions","timing-seconds","prepare-statement","statement","statement-kind","manual-samples","draft-schema","problem-url","approve","run","draft","load","correct","mutant","propose","verify-patch","model","cloud-consent","import-problem","draft-reference","profile-run","source","profile-case","ai","clear-cache","use-cache","audit-reference"])$(id).disabled=value}
async function packages(selected){const p=await api("/api/v4/packages");$("packages").replaceChildren();for(const x of p){const opt=document.createElement("option");opt.value=x.key;opt.textContent=x.manifest.title+" · "+x.key.slice(0,8);$("packages").append(opt)}if(selected)$("packages").value=selected;}
function loadDemo(){activeIntake=null;preparedStatement=null;$("intake-review").hidden=true;$("manual-samples").value="";activeDemo=$("demo").value;const d=demos[activeDemo];if(!d)return;$("package").value=JSON.stringify(d.package,null,2);$("statement").value=d.package.manifest.statement;$("source").value=d.mutant;$("reviewed").checked=false;$("trusted").checked=false;msg("approval","مسودة مثال؛ يجب المراجعة قبل الاعتماد.");}
$("load").onclick=loadDemo;
$("correct").onclick=()=>{$("source").value=demos[activeDemo].correct;$("trusted").checked=false};
$("mutant").onclick=()=>{$("source").value=demos[activeDemo].mutant;$("trusted").checked=false};
function displayIntake(r){
 activeIntake=r.intake;preparedStatement=r.statement;
 $("intake-review").hidden=false;msg("intake-review",JSON.stringify(r.intake,null,2));$("reviewed").checked=false;
}
function resetIntake(){activeIntake=null;preparedStatement=null;$("intake-review").hidden=true;$("reviewed").checked=false}
$("statement").addEventListener("input",resetIntake);
$("manual-samples").addEventListener("input",resetIntake);
$("statement-kind").addEventListener("change",resetIntake);
async function prepareCurrent(){
 if(activeIntake&&preparedStatement===$("statement").value)return activeIntake;
 const raw=$("manual-samples").value.trim();
 const r=await api("/api/v4/packages/intake",{kind:$("statement-kind").value,text:$("statement").value,samples:raw?JSON.parse(raw):[]});
 displayIntake(r);return activeIntake;
}
$("prepare-statement").onclick=async()=>{if(busy)return;setBusy(true);try{await prepareCurrent();msg("approval","Prepared; review statement and examples before drafting.")}catch(e){msg("approval",e.message)}finally{setBusy(false)}};
$("draft").onclick=async()=>{if(busy)return;setBusy(true);msg("approval","توليد مسودة باستخدام الموديل المختار...");try{const intake=await prepareCurrent();let d=await api("/api/v4/packages/draft",{statement:$("statement").value,schema_version:Number($("draft-schema").value),intake,...aiOptions()});$("package").value=JSON.stringify({manifest:d.manifest,reference:"",controls:[],provenance:d.provenance,...(d.intake?{intake:d.intake}:{})},null,2);$("reviewed").checked=false;$("draft-review").hidden=false;msg("draft-review",JSON.stringify(d.constraint_review,null,2));msg("approval",d.warning)}catch(e){if(e.payload?.draft?.manifest){$("package").value=JSON.stringify({manifest:e.payload.draft.manifest,reference:"",controls:[]},null,2);$("reviewed").checked=false;$("draft-review").hidden=false;msg("draft-review",JSON.stringify(e.payload,null,2))}msg("approval",e.message)}finally{setBusy(false);refreshModels().catch(()=>{})}};
$("import-problem").onclick=async()=>{if(busy)return;setBusy(true);try{const r=await api("/api/v4/packages/intake",{kind:"codeforces",url:$("problem-url").value});$("statement").value=r.statement;$("manual-samples").value=JSON.stringify(r.samples,null,2);displayIntake(r);$("import-samples").hidden=false;msg("import-samples",JSON.stringify({source:r.source_url,samples:r.samples},null,2));$("reviewed").checked=false;msg("approval",r.warning)}catch(e){msg("approval",e.message)}finally{setBusy(false)}};
$("draft-reference").onclick=async()=>{if(busy)return;setBusy(true);try{const p=JSON.parse($("package").value);const r=await api("/api/v4/packages/reference",{manifest:p.manifest,...aiOptions()});p.reference=r.reference;delete p.reference_alt;p.controls=[];$("package").value=JSON.stringify(p,null,2);$("reviewed").checked=false;msg("approval",r.warning+" — "+r.rationale)}catch(e){msg("approval",e.message)}finally{setBusy(false);refreshModels().catch(()=>{})}};
$("approve").onclick=async()=>{if(busy)return;setBusy(true);msg("approval","فحص المرجع ضمن Docker...");try{let p=JSON.parse($("package").value);let r=await api("/api/v4/packages/approve",{package:p,owner_reviewed:$("reviewed").checked});msg("approval",JSON.stringify(r.review,null,2));if(r.key)await packages(r.key)}catch(e){msg("approval",e.message)}finally{setBusy(false);refreshModels().catch(()=>{})}};
$("run").onclick=async()=>{if(busy)return;setBusy(true);analysisId=crypto.randomUUID().replaceAll("-","");$("cancel").hidden=false;$("results").hidden=true;$("benchmark-results").hidden=true;msg("status","تنفيذ الحالات والبحث وإعادة التحقق...");try{const source=$("source").value;result=await api("/api/v4/analyze",{package_key:$("packages").value,source,trusted_local_source:$("trusted").checked,use_ai:$("ai").checked,...aiOptions(),generator:$("generator").value,guided:$("guided").checked,spectrum:$("spectrum").checked,count:Number($("count").value),reduce_calls:Number($("reduce-count").value),analysis_id:analysisId});msg("status",result.status+" · "+(result.attempts||0)+" attempts");if(result.status==="observed_mismatch"){sources={student:source,reference:result.reference_source||""};side="student";index=0;show() }else msg("status",result.status+" — "+((result.scope||"No supported conclusion")+" | "+JSON.stringify(result.guidance||{})))}catch(e){msg("status",e.message)}finally{analysisId=null;$("cancel").hidden=true;setBusy(false);refreshModels().catch(()=>{})}};
$("cancel").onclick=async()=>{const id=analysisId;if(!id)return;for(let i=0;i<12&&analysisId===id;i++){try{await api("/api/v4/analysis/"+id+"/cancel",{});msg("status","Cancellation requested");return}catch(e){await new Promise(r=>setTimeout(r,150))}}};
function show(){
 $("repair-panel").hidden=result.status!=="observed_mismatch";
 msg("result-title",result.status==="profiled_execution"?"3. قياس تنفيذ واحد · "+result.kind:"3. الشاهد وأدلة التنفيذ");
 profileSelection=null;$("ast-tree").dataset.sourceKey="";$("candidate").value="";$("patch-reviewed").checked=false;
 for(const id of ["patch-status","patch-diff","repair-history-view"])msg(id,"");
 if(result.package_sha256)refreshRepairs().catch(()=>{});
 const w=result.witness;const manual=result.status==="manual_observation";
 $("results").hidden=false;$("benchmark-results").hidden=true;
 $("reference").disabled=manual;$("cmp-reference").closest("div").hidden=manual;
 $("expected").previousElementSibling.textContent=manual?"خرج عينة معلوم (إن روجع)":w.judgment?.reference_output_is_example?"مثال خرج مقبول (ليس الوحيد)":"المرجع";
 $("actual").previousElementSibling.textContent=manual?"خرج البرنامج":"الطالب";
 msg("stdin",w.stdin);msg("expected",manual?(result.judgment.expected??"لا يوجد مرجع متحقق"):w.reference.stdout);msg("actual",w.student.stdout||w.student.detail||w.student.status);
 if(manual)msg("result-title","ملاحظة تنفيذ مستقل — "+result.kind+" · "+result.judgment.status);
 msg("scope",result.scope+(w.judgment?" | "+JSON.stringify(w.judgment):"")+" | replay: "+result.replay_count+" | trace: "+w.student.trace_status+" | AI: "+result.ai_status+" · "+(result.ai_model||""));
 const reduction=result.reduction;
 $("reduction-panel").hidden=!reduction;
 if(reduction){
   msg("reduction-summary", "Size / magnitude: "+reduction.original_complexity.join(" / ")+" → "+reduction.reduced_complexity.join(" / ")+" · "+reduction.probes+"/"+reduction.budget+" probes");
   msg("reduction-original",result.original_witness?.stdin||JSON.stringify(result.original_case));
   msg("reduction-best",w.stdin);
   msg("reduction-evidence",JSON.stringify({signature:reduction.signature,accepted_steps:reduction.accepted.length,original_replays:reduction.original_replay_count||0,reduced_replays:reduction.reduced_replay_count,stop:reduction.stop_reason,scope:reduction.scope},null,2));
 }
 setupComparison();showRanking();render();showExecutionDiagnostics();showAI();showLocalization();showBranchRanking();
}
function jumpToEvidence(line,eventId,endLine=line){
 side="student";const events=result.witness.student.events||[];
 const pos=events.findIndex(e=>eventId?e.event_id===eventId:e.line===line);
 if(pos>=0)index=pos;profileSelection={line,end_line:endLine};
 $("graph-frame").value="all";$("graph-kind").value="all";render();
 $("code").scrollIntoView({block:"center",behavior:"smooth"});
}
function evidenceButton(label,line,eventId,endLine){
 const b=document.createElement("button");b.className="finding-jump";b.dir="ltr";b.textContent=label;
 b.onclick=()=>jumpToEvidence(line,eventId,endLine||line);return b;
}
function showExecutionDiagnostics(){
 const d=result.execution_diagnostics,panel=$("execution-diagnostics"),container=$("execution-findings");
 panel.hidden=!d;container.replaceChildren();if(!d)return;
 const timeout=d.status==="timeout";
 msg("execution-summary",timeout?"تجاوز البرنامج مهلة التنفيذ وأُوقف. الملاحظات أدناه تربط الأعراض بالأسطر المسجلة؛ لا تثبت وحدها وجود حلقة لا نهائية أو سبب نهائي للخطأ.":result.kind==="match"?"طابق الخرج المرجع على هذا المدخل. القياس يصف تنفيذاً واحداً؛ لا يثبت صحة الحل لكل المدخلات.":"راجع حالة التنفيذ والمخرجات واللقطات المسجلة لهذا المدخل.");
 for(const f of d.findings||[]){
  const card=document.createElement("div");card.className="diagnostic-card";
  const title=document.createElement("strong");title.textContent="تكرار قيم شرط الحلقة · L"+f.line+"–"+f.end_line;card.append(title);
  const p=document.createElement("p");p.textContent="الشرط "+f.condition_source+" أعطى true بنفس القيم في "+f.observed_repeated_headers+" فحوص مسجلة متتالية: "+Object.entries(f.condition_values).map(([k,v])=>k+" = "+JSON.stringify(v)).join("،");card.append(p);
  card.append(evidenceButton("L"+f.line+" · "+f.condition_source,f.line,f.last_event_id,f.end_line));
  for(const a of f.assignments||[]){
   const text=document.createElement("p");text.textContent="في السطر "+a.line+" بقيت "+a.variable+" = "+JSON.stringify(a.before)+" قبل التحديث وبعده. راجع هذا التحديث وحدود الحلقة.";card.append(text);
   card.append(evidenceButton("L"+a.line+" · "+a.source,a.line,a.before_event_id));
  }
  const note=document.createElement("p");note.textContent="هذه مقارنة للقطات داخل الجزء المسجل"+(d.trace_status==="truncated"?"؛ التتبع مقتطع والأعداد المرصودة حدود دنيا.":".");card.append(note);container.append(card);
 }
 if(timeout&&!(d.findings||[]).length){const p=document.createElement("p");p.textContent="لم تكفِ اللقطات لإثبات نمط تكرار مدعوم لقيم شرط الحلقة. يمكن أن يكون السبب بطئاً أو انتظاراً أو تكراراً غير مدعوم؛ لا نحدد سطر خطأ بالتخمين.";container.append(p)}
 if(timeout&&(d.timed_loops||[]).length){
  const p=document.createElement("p");p.textContent="أكثر الحلقات زيارةً في القياس — كثرة الزيارات لا تثبت الخطأ:";container.append(p);
  for(const loop of d.timed_loops)container.append(evidenceButton("L"+loop.line+"–"+loop.end_line+" · "+loop.kind+" · "+loop.hits+" visits",loop.line,null,loop.end_line));
 }
}
function showAI(){
 const state=result.ai_status||"disabled",ok=state==="ok";
 const errors={local_model_unavailable:"الموديل المحلي غير متاح؛ تأكد من تشغيل Ollama.",model_busy:"الموديل مشغول بطلب آخر.",invalid_model_json:"رد الموديل لم يكن JSON صالحاً.",invalid_model_schema:"رد الموديل لم يطابق المخطط المطلوب.",invalid_model_output:"تعذّر التحقق من رد الموديل.",local_model_incomplete_response:"انتهت ميزانية الرد قبل اكتماله.",inference_cancelled:"أُلغي طلب الموديل.",inference_deadline:"انتهت مهلة طلب الموديل."};
 const message=state==="disabled"?"لم يُطلب تحليل AI. فعّل «فرضيات الموديل المختار» ثم أعد البحث أو قياس الزمن.":ok?"اكتمل طلب الموديل. الفرضيات غير مؤكدة، والحقائق أدناه مفحوصة ضمن اللقطات المقدمة فقط.":"تعذّر تحليل AI: "+(errors[result.ai_error]||result.ai_error||state)+" أدلة التنفيذ تبقى متاحة.";
 msg("ai-state",message);
 $("hypotheses").replaceChildren();
 for(const h of result.hypotheses||[]){
  const div=document.createElement("div");div.className="hypothesis";
  const basis={recorded:"فرضية حول أحداث مسجلة",static:"فرضية ساكنة (لا تثبت تنفيذ السطر)",missing_condition:"فرضية شرط ناقص (لا تدعي وجود سطر منفذ)"};
  div.textContent=(h.status==="hypothesis"?(basis[h.basis]||"فرضية غير مؤكدة"):"إحالات غير مدعومة")+
    (h.conflicting_claims?" · يحتوي الرد على ادعاءات متناقضة":"")+" — "+h.text+" ("+h.event_ids.join(", ")+")";
  if(h.status==="hypothesis"){
   const b=document.createElement("button");b.textContent="L"+h.line+" · proposed location";
   const jump=()=>jumpToEvidence(h.line,h.basis==="recorded"?h.event_ids.find(i=>result.witness.student.events.some(e=>e.event_id===i&&e.line===h.line)):null);div.onclick=jump;b.onclick=e=>{e.stopPropagation();jump()};div.append(b);
  }
  $("hypotheses").append(div);
 }
 if(!($("hypotheses").children.length))msg("hypotheses",ok?"الموديل لم يرجع فرضية؛ لا نستنتج سبباً من فراغ الرد.":message);
 const statuses={matches_recorded_snapshot:"مطابق للقطة المسجلة",matches_recorded_condition:"مطابق للشرط المعاد حسابه",contradicted:"مناقض للقطة",unsupported:"غير مدعوم بالأدلة المقدمة"};
 const facts=result.ai_facts||[],branches=result.ai_branches||[];
 msg("facts",facts.length?facts.map(f=>f.event_id+" · "+f.variable+" = "+JSON.stringify(f.value)+" · "+(statuses[f.status]||f.status)).join("\n"):ok?"لم يرجع الموديل مطالبات بقيم متغيرات لفحصها.":message);
 msg("branch-facts",branches.length?branches.map(f=>f.event_id+" · L"+f.line+" · الشرط المقترح "+f.condition+" · "+(statuses[f.status]||f.status)).join("\n"):ok?"لم يرجع الموديل مطالبات عن شروط if/while لفحصها.":message);
 const context=result.ai_context||{};
 msg("ai-context",Object.keys(context).length?JSON.stringify(context,null,2):state==="disabled"?"لم يُجهّز سياق للموديل لأن التحليل غير مفعّل.":"لا يتوفر سياق موديل محفوظ لهذا الطلب.");
 if(result.status==="profiled_execution")msg("probes","اختبارات الفرضيات لا تُنفّذ ضمن قياس مدخل واحد. هي خيار مستقل «اختبارات موجهة بفرضيات AI» أثناء البحث عن الخطأ.");
 else if(!result.guidance||result.guidance.status==="disabled")msg("probes","اختبارات الفرضيات غير مفعّلة. فعّل الخيار المستقل إذا أردت تنفيذ حالات إضافية مقترحة من الموديل.");
 else msg("probes",JSON.stringify(result.guidance,null,2));
}
function setupComparison(){
 for(const s of ["student","reference"]){const events=result.witness[s].events||[];const slider=$("cmp-"+s);slider.max=Math.max(0,events.length-1);slider.value=Math.max(0,events.findIndex(e=>e.kind==="line"&&e.line>=1));drawComparison(s)}
 const view=$("matrix-view");view.replaceChildren();
 for(const [name,value] of Object.entries(result.witness.case||{})){
  if(!Array.isArray(value))continue;
  const rows=Array.isArray(value[0])?value:[value];const heading=document.createElement("p");heading.textContent=name;view.append(heading);const table=document.createElement("table");
  for(const row of rows){const tr=document.createElement("tr");for(const cell of row){const td=document.createElement("td");td.textContent=typeof cell==="object"?JSON.stringify(cell):String(cell);tr.append(td)}table.append(tr)}view.append(table)
 }
 if(!view.children.length)msg("matrix-view","لا توجد مصفوفة أو قائمة في المدخل المختار.")
}
function drawComparison(s){
 if(!result)return;const events=result.witness[s].events||[],ev=events[Number($("cmp-"+s).value)];msg("cmp-"+s+"-meta",ev?ev.event_id+" · L"+ev.line+" · "+ev.kind+" · "+result.witness[s].trace_status:"No trace");
 msg("cmp-"+s+"-locals",ev?JSON.stringify(ev.locals,null,2):"");
 const pre=$("cmp-"+s+"-code");pre.replaceChildren();(sources[s]||"").split("\n").forEach((line,i)=>{const span=document.createElement("span");span.textContent=String(i+1).padStart(3)+"  "+line;if(ev&&ev.line===i+1)span.className="active";pre.append(span)});
}
for(const s of ["student","reference"])$("cmp-"+s).oninput=()=>drawComparison(s);
function showRanking(){
 const container=$("ranking");container.replaceChildren();const ranking=result.suspiciousness||{};
 if(!ranking.ranked||!ranking.ranked.length){msg("ranking",ranking.status||"غير مفعل");return}
 for(const line of ranking.ranked.slice(0,20)){const b=document.createElement("button");b.textContent="L"+line.line+" · "+line.ochiai;b.onclick=()=>{side="student";index=result.witness.student.events.findIndex(e=>e.line===line.line);render()};container.append(b)}
}
$("graph-zoom").oninput=()=>{if(result)render()};
function svgEl(tag,attrs){const e=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);return e}
function refreshGraphFrames(g){
 const picker=$("graph-frame"),selected=picker.value;picker.replaceChildren();
 const all=document.createElement("option");all.value="all";all.textContent="كل الإطارات";picker.append(all);
 for(const frame of g.frames||[]){const o=document.createElement("option");o.value=frame.id;o.textContent=frame.id+" · "+frame.function;picker.append(o)}
 picker.value=Array.from(picker.options).some(o=>o.value===selected)?selected:"all";
}
function drawObservedGraph(g,events,ev){
 const container=$("graph");container.replaceChildren();
 const selectedFrame=$("graph-frame").value,kind=$("graph-kind").value,compact=$("graph-layout").value==="compact";
 const visibleIds=new Set(events.filter(e=>(selectedFrame==="all"||e.frame_id===selectedFrame)&&(kind==="all"||e.kind===kind)).map(e=>e.event_id));
 const candidates=g.nodes.filter(n=>n.event_ids.some(id=>visibleIds.has(id))),nodes=candidates.slice(0,128);
 const columns=compact?2:1,width=compact?680:440,boxWidth=compact?260:200,height=Math.max(100,Math.ceil(nodes.length/columns)*58+35);
 const positions=new Map(),svg=svgEl("svg",{viewBox:"0 0 "+width+" "+height,width,height});
 const defs=svgEl("defs",{}),marker=svgEl("marker",{id:"arrow",markerWidth:7,markerHeight:7,refX:6,refY:3,orient:"auto"});
 marker.append(svgEl("path",{d:"M0 0 L6 3 L0 6",stroke:"#94a3b8",fill:"#94a3b8"}));defs.append(marker);svg.append(defs);
 nodes.forEach((n,i)=>positions.set(n.id,{x:compact?30+(i%2)*320:110,y:16+Math.floor(i/columns)*58}));
 for(const [i,e] of g.edges.entries()){
  const a=positions.get(e.from),b=positions.get(e.to);if(!a||!b)continue;
  const bend=8+i%9*10;
  const pathData=e.from===e.to?"M "+(a.x+boxWidth)+" "+(a.y+12)+" C "+(a.x+boxWidth+40)+" "+(a.y-16)+" "+(a.x+boxWidth+40)+" "+(a.y+45)+" "+(a.x+boxWidth)+" "+(a.y+28):
   compact?"M "+(a.x+boxWidth/2)+" "+(a.y+40)+" C "+(a.x+boxWidth/2)+" "+(a.y+52)+" "+(b.x+boxWidth/2)+" "+(b.y-12)+" "+(b.x+boxWidth/2)+" "+b.y:
   "M "+a.x+" "+(a.y+20)+" H "+bend+" V "+(b.y+20)+" H "+(b.x-2);
  const path=svgEl("path",{d:pathData,"marker-end":"url(#arrow)"}),tip=svgEl("title",{});
  tip.textContent=e.count+" observed transitions";path.append(tip);svg.append(path);
 }
 const peak=Math.max(0,...nodes.map(n=>n.timing?.self_wall_ns||0));
 for(const n of nodes){
  const pos=positions.get(n.id),group=svgEl("g",{class:"node"+(ev&&n.event_ids.includes(ev.event_id)?" selected":""),tabindex:0,role:"button","aria-label":n.frame_id+" line "+n.line});
  group.append(svgEl("rect",{x:pos.x,y:pos.y,width:boxWidth,height:40,rx:7}));
  const label=svgEl("text",{x:pos.x+8,y:pos.y+24});
  label.textContent=n.frame_id+" · L"+n.line+" · "+n.event_ids.length+"×"+(n.timing?" · "+(n.timing.self_wall_ns/1e6).toFixed(3)+"ms":"");group.append(label);
  const tip=svgEl("title",{});tip.textContent=n.timing?"Self wall: "+(n.timing.self_wall_ns/1e6).toFixed(6)+" ms · CPU: "+(n.timing.self_cpu_ns/1e6).toFixed(6)+" ms":"Timing unavailable";group.append(tip);
  if(peak>0&&n.timing?.self_wall_ns>=peak*.6)group.classList.add("timing-hot");
  const jump=()=>{index=events.findIndex(e=>n.event_ids.includes(e.event_id)&&visibleIds.has(e.event_id));render()};
  group.onclick=jump;group.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();jump()}};svg.append(group);
 }
 const zoom=Number($("graph-zoom").value)/100;svg.style.width=(width*zoom)+"px";svg.style.height=(height*zoom)+"px";container.append(svg);
 msg("graph-status","عرض "+nodes.length+" من "+g.nodes.length+" عقدة مرصودة"+(candidates.length>128?" · حد العرض 128":"")+(ev&&!visibleIds.has(ev.event_id)?" · الحدث الحالي خارج المرشح":""));
}
function render(){
 const w=result.witness[side],events=w.events||[],g=result[side+"_graph"];index=Math.max(0,Math.min(index,events.length-1));const ev=events[index];
 $("slider").max=Math.max(0,events.length-1);$("slider").value=index;
 msg("step",(ev?ev.event_id+" · "+ev.kind+" · L"+ev.line:"No events")+" · "+w.trace_status);
 msg("locals",ev?JSON.stringify(ev.locals,null,2):"");
 const previous=ev?[...events.slice(0,index)].reverse().find(e=>e.frame_id===ev.frame_id):null;
 msg("previous-locals",previous?JSON.stringify(previous.locals,null,2):"لا توجد لقطة سابقة في هذا الإطار.");
 const snapshotChanges=[];
 for(const name of new Set([...Object.keys(previous?.locals||{}),...Object.keys(ev?.locals||{})])){
  const before=previous?.locals?.[name],after=ev?.locals?.[name];
  if(JSON.stringify(before)!==JSON.stringify(after))snapshotChanges.push({name,before:before===undefined?"not_recorded":before,after:after===undefined?"not_recorded":after});
 }
 msg("snapshot-changes",JSON.stringify(snapshotChanges,null,2));
 const frames=new Map((g.frames||[]).map(f=>[f.id,f]));let stack=[],id=ev&&ev.frame_id;
 while(id&&frames.has(id)&&stack.length<32){const f=frames.get(id);stack.push(f.id+" · "+f.function);id=f.parent}msg("stack",stack.reverse().join("\n"));
 const code=$("code");code.replaceChildren();(sources[side]||"").split("\n").forEach((line,i)=>{const span=document.createElement("span");span.textContent=String(i+1).padStart(3)+"  "+line;if(ev&&ev.line===i+1)span.classList.add("active");if(profileSelection&&profileSelection.line<=i+1&&profileSelection.end_line>=i+1)span.classList.add("profile-range");code.append(span)});
 refreshGraphFrames(g);drawObservedGraph(g,events,ev);
 $("changes").replaceChildren();for(const change of g.changes){const d=document.createElement("div");d.className="change";d.textContent=change.name+": "+JSON.stringify(change.before)+" → "+JSON.stringify(change.after)+" ("+change.before_event_id+"→"+change.after_event_id+")";$("changes").append(d)}
 $("relations").replaceChildren();
 for(const rel of [...g.relations.data,...g.relations.control]){
  const b=document.createElement("button");b.className="change";b.textContent=rel.write?JSON.stringify(rel.reads)+" → "+rel.write.name+"="+rel.write.value:"L"+rel.line+" → L"+rel.target_line+" · "+rel.condition;
  b.onclick=()=>{index=events.findIndex(e=>e.event_id===rel.after_event_id);render()};$("relations").append(b);
 }
 for(const rel of g.relations.def_use||[]){const b=document.createElement("button");b.className="change";b.textContent=rel.name+"="+rel.value+" · "+rel.producer_event_id+" → "+rel.consumer_event_id;b.onclick=()=>{index=events.findIndex(e=>e.event_id===rel.consumer_event_id);render()};$("relations").append(b)}
 if(!$("relations").children.length)msg("relations","لا توجد علاقة مدعومة ضمن النطاق الحالي.");
 $("loops").replaceChildren();
 for(const loop of g.loop_summary?.loops||[]){
  const b=document.createElement("button");b.className="change";
  b.textContent=loop.frame_id?"L"+loop.line+" · "+loop.frame_id+" · رأس الحلقة: "+loop.header_visits+" · دخول الجسم المرصود: "+loop.observed_body_entries+" · "+loop.status:"L"+loop.line+" · "+loop.status;
  b.onclick=()=>{const first=loop.body_event_ids?.[0]||loop.header_event_ids?.[0];const pos=events.findIndex(e=>e.event_id===first);if(pos>=0){index=pos;render()}};$("loops").append(b);
 }
 if(!$("loops").children.length)msg("loops","لا توجد حلقات مدعومة مرصودة في هذا الجزء من التتبع.");
 renderProfile();msg("output-chain",JSON.stringify(g.output_chain||{},null,2));msg("static-cfg",JSON.stringify(g.static_cfg||{},null,2));renderAst(g,events);showBranchCoverage(g);
}
for(const id of ["graph-frame","graph-kind","graph-layout"])$(id).onchange=()=>{if(result)render()};
let graphDrag=null;
$("graph").addEventListener("pointerdown",e=>{if(e.button!==0||e.target.closest(".node"))return;graphDrag={x:e.clientX,y:e.clientY,left:$("graph").scrollLeft,top:$("graph").scrollTop};$("graph").setPointerCapture(e.pointerId)});
$("graph").addEventListener("pointermove",e=>{if(!graphDrag)return;$("graph").scrollLeft=graphDrag.left-(e.clientX-graphDrag.x);$("graph").scrollTop=graphDrag.top-(e.clientY-graphDrag.y)});
for(const kind of ["pointerup","pointercancel","lostpointercapture"])$("graph").addEventListener(kind,()=>{graphDrag=null});

$("student").onclick=()=>{side="student";index=0;profileSelection=null;render()};$("reference").onclick=()=>{side="reference";index=0;profileSelection=null;render()};$("prev").onclick=()=>{index--;render()};$("next").onclick=()=>{index++;render()};$("slider").oninput=()=>{index=Number($("slider").value);render()};$("export").onclick=()=>{if(!result)return;const u=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=u;a.download="algoxray-v4-evidence.json";a.click();URL.revokeObjectURL(u)};
(async()=>{try{token=(await api("/api/session")).custom_code_token;await refreshModels();demos=await (await fetch("/static/v4-demos.json")).json();loadDemo();await packages()}catch(e){msg("health",e.message)}})();

function repairBody(){return {package_key:result.package_sha256,source:result.student_source,case:result.witness.case,original_case:result.original_case||null}}
$("propose").onclick=async()=>{if(busy||!result)return;setBusy(true);msg("patch-status","Generating a proposal using the selected model...");try{const r=await api("/api/v4/repair/propose",{...repairBody(),...aiOptions()});$("candidate").value=r.candidate;$("patch-reviewed").checked=false;msg("patch-status",r.status+" — "+r.rationale);msg("patch-diff",r.diff||"")}catch(e){msg("patch-status",e.message)}finally{setBusy(false);refreshModels().catch(()=>{})}};
$("verify-patch").onclick=async()=>{
 if(busy||!result)return;
 setBusy(true);analysisId=crypto.randomUUID().replaceAll("-","");$("cancel").hidden=false;
 msg("patch-status","Testing candidate against original and reduced witnesses and regression cases...");
 const candidate=$("candidate").value;
 try{
  const r=await api("/api/v4/repair/verify",{...repairBody(),candidate,reviewed:$("patch-reviewed").checked,analysis_id:analysisId});
  if(r.analysis_id!==analysisId||candidate!==$("candidate").value)return;
  msg("patch-status",JSON.stringify(r,null,2));await refreshRepairs()
 }catch(e){msg("patch-status",e.message)}
 finally{analysisId=null;$("cancel").hidden=true;setBusy(false);refreshModels().catch(()=>{})}
};
$("candidate").addEventListener("input",()=>{$("patch-reviewed").checked=false;msg("patch-status","");msg("patch-diff","")});

async function refreshRepairs(){
 if(!result)return;
 const rows=await api("/api/v4/repairs/"+result.package_sha256);$("repair-history").replaceChildren();
 for(const r of rows){const opt=document.createElement("option");opt.value=r.key;opt.textContent=r.status+" · "+r.key.slice(0,10);$("repair-history").append(opt)}
}
$("load-repair").onclick=async()=>{try{const key=$("repair-history").value;if(!key)return;const r=await api("/api/v4/repair/version/"+key);msg("repair-history-view",JSON.stringify(r,null,2))}catch(e){msg("repair-history-view",e.message)}};

function invalidateResult(){if(!busy){result=null;benchmarkResult=null;$("results").hidden=true;$("benchmark-results").hidden=true;profileSelection=null}}
$("source").addEventListener("input",invalidateResult);
$("profile-case").addEventListener("input",invalidateResult);
for(const id of ["manual-stdin","manual-expected","size-field","size-values","timing-repetitions","timing-seconds"])$(id).addEventListener("input",invalidateResult);
$("sample-reviewed").addEventListener("change",invalidateResult);
$("sample-comparison").addEventListener("change",invalidateResult);

for(const id of ["correct","mutant","load"])$(id).addEventListener("click",invalidateResult);
$("profile-run").onclick=async()=>{
 if(busy)return;
 let caseValue=null;
 try{caseValue=$("profile-case").value.trim()?JSON.parse($("profile-case").value):null}catch(e){msg("status","مدخل JSON غير صالح");return}
 setBusy(true);analysisId=crypto.randomUUID().replaceAll("-","");$("cancel").hidden=false;$("results").hidden=true;$("benchmark-results").hidden=true;msg("status","قياس التنفيذ للطالب والمرجع...");
 try{
  const source=$("source").value;
  result=await api("/api/v4/profile",{package_key:$("packages").value,source,case:caseValue,trusted_local_source:$("trusted").checked,use_ai:$("ai").checked,...aiOptions(),analysis_id:analysisId});
  msg("status",result.status+" · "+(result.kind||""));
  if(result.status==="profiled_execution"){sources={student:source,reference:result.reference_source||""};side="student";index=0;show()}
 }catch(e){msg("status",e.message)}finally{analysisId=null;$("cancel").hidden=true;setBusy(false);refreshModels().catch(()=>{})}
};
function profileRows(){
 const p=result?.[side+"_graph"]?.profile||{};
 const key=$("profile-cost").value+"_"+$("profile-clock").value+"_ns";
 return [...(p[$("profile-level").value]||[])].sort((a,b)=>(b[key]||0)-(a[key]||0)||a.line-b.line);
}
function renderProfile(){
 const p=result[side+"_graph"].profile||{status:"unavailable"};
 const ns=n=>Number.isFinite(n)?(n/1e6).toFixed(3):"—";
 msg("profile-summary",(side==="student"?"الطالب":"المرجع")+" · "+p.status+" · زمن التنفيذ "+ns(p.execution_wall_ns)+" ms · CPU "+ns(p.execution_cpu_ns)+" ms · كلفة أداة التتبع "+ns(p.callback_wall_ns)+" ms · زمن الطلب مع الحاوية "+(result.witness[side].elapsed_ms??"—")+" ms");
 const tbody=$("profile-table").tBodies[0];tbody.replaceChildren();
 const rows=profileRows(),key=$("profile-cost").value+"_"+$("profile-clock").value+"_ns",peak=Math.max(0,...rows.map(r=>r[key]||0));
 for(const row of rows){
  const tr=document.createElement("tr"),name=document.createElement("td"),button=document.createElement("button");
  button.textContent=(row.kind?row.kind+" "+row.name:row.function+" · "+row.frame_id)+" · L"+row.line+(row.end_line&&row.end_line!==row.line?"–"+row.end_line:"");
  button.onclick=()=>{profileSelection={line:row.line,end_line:row.end_line||row.line};const events=result.witness[side].events||[];const i=events.findIndex(e=>e.kind==="line"&&e.line>=row.line&&e.line<=(row.end_line||row.line)&&(!row.frame_id||e.frame_id===row.frame_id));if(i>=0)index=i;render();msg("profile-detail",i>=0?"تم تحديد البلوك في الكود والانتقال إلى حدثه.":"لم يسجل التتبع حدثاً لهذا البلوك؛ قد يكون غير منفذ أو خارج الجزء المسجل.")};
  name.append(button);tr.append(name);
  for(const value of [row.hits,ns(row[key]),row.hits?ns(row[key]/row.hits):"—"]){const td=document.createElement("td");td.textContent=String(value);tr.append(td)}
  const cell=document.createElement("td"),bar=document.createElement("meter");bar.min=0;bar.max=peak||1;bar.value=row[key]||0;bar.setAttribute("aria-label","Relative measured time");cell.append(bar);tr.append(cell);tbody.append(tr);
 }
 if(!rows.length)msg("profile-detail","لا توجد قياسات متاحة لهذا التنفيذ.");
}
for(const id of ["profile-level","profile-clock","profile-cost"])$(id).onchange=()=>{if(result)renderProfile()};
$("profile-csv").onclick=()=>{
 if(!result)return;
 const columns=["kind","name","function","frame_id","line","end_line","hits","self_wall_ns","self_cpu_ns","inclusive_wall_ns","inclusive_cpu_ns"];
 const quote=v=>'"'+String(v??"").replaceAll('"','""')+'"';
 const csv=[columns,...profileRows().map(r=>columns.map(c=>r[c]))].map(r=>r.map(quote).join(",")).join("\r\n");
 const url=URL.createObjectURL(new Blob(["\ufeff"+csv],{type:"text/csv;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="algoxray-"+side+"-timing.csv";a.click();URL.revokeObjectURL(url);
};

$("clear-cache").onclick=async()=>{if(busy)return;try{await api("/api/v4/cache/clear",{});await refreshModels()}catch(e){msg("cache-state",e.message)}};

$("audit-reference").onclick=async()=>{if(busy)return;setBusy(true);try{const r=await api("/api/v4/packages/audit",{package:JSON.parse($("package").value),owner_reviewed:$("reviewed").checked,max_cases:16});$("reference-audit").hidden=false;msg("reference-audit",JSON.stringify(r,null,2))}catch(e){$("reference-audit").hidden=false;msg("reference-audit",e.message)}finally{setBusy(false)}};

async function runIndependent(path,body){
 if(busy)return;
 setBusy(true);analysisId=crypto.randomUUID().replaceAll("-","");$("cancel").hidden=false;
 result=null;benchmarkResult=null;$("results").hidden=true;$("benchmark-results").hidden=true;msg("status","Executing isolated program...");
 try{
  const source=$("source").value;
  const data=await api(path,{...body,source,trusted_local_source:$("trusted").checked,analysis_id:analysisId});
  if(data.analysis_id!==analysisId||source!==$("source").value)return;
  msg("status",data.status+" · "+(data.kind||data.stop_reason||""));
  if(data.status==="manual_observation"){
   result=data;sources={student:source,reference:""};side="student";index=0;show();
  }else if(data.status==="benchmark_observation"){
   benchmarkResult=data;showBenchmark();
  }
 }catch(e){msg("status",e.message)}
 finally{analysisId=null;$("cancel").hidden=true;setBusy(false)}
}
$("observe-run").onclick=()=>runIndependent("/api/v4/observe",{stdin:$("manual-stdin").value,
 expected:$("sample-reviewed").checked?$("manual-expected").value:null,expected_reviewed:$("sample-reviewed").checked,
 comparison:$("sample-comparison").value,mode:"trace_profile",seconds:Number($("timing-seconds").value)});
$("plain-benchmark").onclick=()=>runIndependent("/api/v4/benchmark",{stdin:$("manual-stdin").value,repetitions:Number($("timing-repetitions").value),seconds:Number($("timing-seconds").value)});
$("scaling-benchmark").onclick=()=>runIndependent("/api/v4/benchmark",{package_key:$("packages").value,size_field:$("size-field").value.trim(),
 sizes:$("size-values").value.split(",").map(x=>Number(x.trim())),repetitions:Number($("timing-repetitions").value),seconds:Number($("timing-seconds").value)});
function showBenchmark(){
 const b=benchmarkResult;if(!b)return;
 $("benchmark-results").hidden=false;
 msg("benchmark-summary",b.stop_reason+" · "+b.physical_executions+" worker executions · "+b.elapsed_ms+" ms session");
 msg("benchmark-scope",b.scope);msg("benchmark-growth",JSON.stringify(b.growth,null,2));
 const tbody=$("benchmark-table").tBodies[0];tbody.replaceChildren();
 const ms=n=>Number.isFinite(n)?(n/1e6).toFixed(4):"—";
 for(const point of b.points){
  const s=point.summary,tr=document.createElement("tr");
  for(const v of [point.size??"manual",s.completed+"/"+s.requested,ms(s.wall_ns?.median),ms(s.cpu_ns?.median),
   s.wall_ns?ms(s.wall_ns.min)+" – "+ms(s.wall_ns.max):"—",s.timeouts,point.correctness]){
   const td=document.createElement("td");td.textContent=String(v);tr.append(td);
  }tbody.append(tr);
 }
 const view=$("benchmark-chart");view.replaceChildren();
 const rows=b.points.filter(p=>Number.isFinite(p.size)&&Number.isFinite(p.summary.wall_ns?.median));
 if(rows.length<2){msg("benchmark-chart","At least two measured sizes are needed for a curve.");return}
 const xMin=Math.min(...b.points.map(p=>p.size)),xMax=Math.max(...b.points.map(p=>p.size));
 const yMax=Math.max(1,...rows.map(p=>p.summary.wall_ns.max));
 const x=v=>50+520*(v-xMin)/Math.max(1,xMax-xMin),y=v=>215-175*v/yMax;
 const svg=svgEl("svg",{viewBox:"0 0 620 255",role:"img","aria-label":"Measured wall time medians by input size"});
 svg.style.width="100%";svg.style.maxWidth="720px";
 svg.append(svgEl("path",{d:"M50 20 V215 H590",stroke:"currentColor",fill:"none"}));
 const units=svgEl("text",{x:55,y:15,fill:"currentColor","font-size":12});units.textContent="Wall time (ms)";svg.append(units);
 let previous=null;
 for(const p of b.points){
  const wall=p.summary.wall_ns;
  if(!wall||p.summary.completed!==p.summary.requested){previous=null;continue}
  const px=x(p.size),py=y(wall.median);
  if(previous)svg.append(svgEl("line",{x1:previous[0],y1:previous[1],x2:px,y2:py,stroke:"#2563eb","stroke-width":2}));
  svg.append(svgEl("line",{x1:px,y1:y(wall.min),x2:px,y2:y(wall.max),stroke:"currentColor","stroke-width":1}));
  const circle=svgEl("circle",{cx:px,cy:py,r:4,fill:"#2563eb"}),tip=svgEl("title",{});
  tip.textContent=p.size+": "+ms(wall.median)+" ms, "+p.correctness;circle.append(tip);svg.append(circle);
  const label=svgEl("text",{x:px,y:235,fill:"currentColor","font-size":11,"text-anchor":"middle"});label.textContent=String(p.size);svg.append(label);
  previous=[px,py];
 }
 view.append(svg);
}
$("benchmark-export").onclick=()=>{
 if(!benchmarkResult)return;
 const url=URL.createObjectURL(new Blob([JSON.stringify(benchmarkResult,null,2)],{type:"application/json"}));
 const a=document.createElement("a");a.href=url;a.download="algoxray-benchmark.json";a.click();URL.revokeObjectURL(url);
};

function showLocalization(){
 const view=$("localization-rows"),bounds=$("bounds-findings");view.replaceChildren();bounds.replaceChildren();
 const loc=result?.evidence_localization||{};
 msg("localization-scope",loc.scope||"لا تتوفر أدلة كافية لترشيح موضع.");
 const effect=loc.effect_site;
 msg("effect-site",effect?"موضع ظهور الأثر: L"+effect.line+" · "+effect.kind:"لم يحدد موضع ظهور الأثر من اللقطات.");
 for(const row of loc.ranked||[]){
  const div=document.createElement("div");div.className="diagnostic-card";
  const button=document.createElement("button");button.textContent="L"+row.line+" · "+row.score.toFixed(3)+" · suspected";
  button.onclick=()=>jumpToEvidence(row.line,row.event_ids?.[0]);div.append(button);
  for(const signal of row.signals){
   const p=document.createElement("p");p.textContent=signal.kind+" (+"+signal.weight+"): "+signal.detail;div.append(p);
  }view.append(div);
 }
 if(!view.children.length)msg("localization-rows","لا يوجد ترشيح مسند كافٍ؛ قد يكون الشرط أو الكود المفقود سبباً محتملاً.");
 for(const finding of loc.loop_bounds||[]){
  const div=document.createElement("div");div.className="diagnostic-card";
  const b=document.createElement("button");b.textContent="L"+finding.line+" · "+finding.range_source;
  b.onclick=()=>jumpToEvidence(finding.line,finding.header_event_id);div.append(b);
  const p=document.createElement("p");p.textContent=finding.array+" length "+finding.array_length+
   " · recorded read indices "+JSON.stringify(finding.observed_read_indices)+" · omitted "+JSON.stringify(finding.omitted_indices);div.append(p);
  const h=document.createElement("p");h.textContent=finding.hypothesis;div.append(h);bounds.append(div);
 }
}
function renderAst(g,events){
 const tree=g.structure,view=$("ast-tree");
 if(!tree){view.replaceChildren();msg("ast-scope","No source structure");return}
 const key=side+":"+tree.source_sha256;
 if(view.dataset.sourceKey===key)return;
 view.dataset.sourceKey=key;view.replaceChildren();
 msg("ast-scope",tree.status+" · "+tree.nodes.length+" nodes · "+tree.scope);
 const children=new Map(),nodes=new Map();
 for(const n of tree.nodes){
  nodes.set(n.id,n);
  const list=children.get(n.parent_id)||[];list.push(n);children.set(n.parent_id,list);
 }
 const eventLinks=tree.event_links||[];
 function branch(parent){
  const ul=document.createElement("ul");
  for(const n of children.get(parent)||[]){
   const li=document.createElement("li"),b=document.createElement("button");
   b.type="button";b.className="ast-node";b.textContent=n.label+(n.source_span?" · L"+n.source_span.line+":"+n.source_span.column_utf8:"");
   b.title=n.preview||n.kind;
   if(n.source_span){
    const link=eventLinks.find(e=>e.candidate_node_ids.includes(n.id));
    b.onclick=()=>{
     profileSelection={line:n.source_span.line,end_line:n.source_span.end_line};
     if(link){const pos=events.findIndex(e=>e.event_id===link.event_id);if(pos>=0)index=pos}
     render();$("code").scrollIntoView({block:"center"});
     msg("ast-scope",tree.status+" · "+n.id+" · "+(link?link.association+" / "+link.event_id:"Static node; no recorded event association."));
    };
   }else b.disabled=true;
   li.append(b);
   if(children.has(n.id)){
    const details=document.createElement("details"),summary=document.createElement("summary");
    summary.textContent="children ("+children.get(n.id).length+")";details.open=n.depth<2;
    details.append(summary,branch(n.id));li.append(details);
   }ul.append(li);
  }
  return ul;
 }
 view.append(branch(null));
}

function showBranchCoverage(g){
 const rows=$("branch-coverage"),b=g.branches||{};rows.replaceChildren();
 msg("branch-coverage-scope",b.scope||"لا تتوفر ملاحظات فروع لهذا المسار.");
 for(const r of b.observed||[]){
  const button=document.createElement("button");
  button.textContent="L"+r.line+" → L"+r.target_line+" · "+r.kind+" · "+r.count+"×";
  button.onclick=()=>{
   const id=r.event_pairs?.[0]?.[0];const pos=result.witness[side].events.findIndex(e=>e.event_id===id);
   if(pos>=0)index=pos;profileSelection={line:r.line,end_line:r.line};render();
  };rows.append(button);
 }
 if(!rows.children.length)msg("branch-coverage","لا توجد انتقالات فروع مدعومة ضمن اللقطات.");
}
function showBranchRanking(){
 const rows=$("branch-ranking");rows.replaceChildren();const b=result?.suspiciousness?.branches||{};
 for(const r of b.ranked||[]){
  const button=document.createElement("button");
  button.textContent="L"+r.line+" → L"+r.target_line+" · "+r.kind+" · "+r.ochiai+" · F"+r.failing_coverage+"/P"+r.passing_coverage;
  button.onclick=()=>jumpToEvidence(r.line,r.witness_event_pairs?.[0]?.[0]);rows.append(button);
 }
 if(!rows.children.length)msg("branch-ranking","ترتيب الفروع يحتاج عينات ناجحة وفاشلة كاملة؛ غير متاح في هذا الطلب.");
}
