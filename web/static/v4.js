"use strict";
const $=id=>document.getElementById(id);
let token="",demos={},activeDemo="hamburgers",result=null,side="student",index=0,sources={},busy=false,analysisId=null,profileSelection=null;
async function api(path,body){
 const opts=body===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json","X-AlgoXRay-Token":token},body:JSON.stringify(body)};
 const response=await fetch(path,opts);const data=await response.json();if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:JSON.stringify(data.detail));return data;
}
function msg(id,value){$(id).textContent=value}
function aiOptions(){return {model:$("model").value,cloud_consent:$("cloud-consent").checked}}
async function refreshModels(){const h=await api("/api/v4/health");msg("health","Ollama: "+h.model.status+" · "+h.model.models.join(", ")+" | Gemini: "+(h.gemini.configured?"key configured":"key missing")+" | OpenRouter: "+(h.openrouter.configured?"key configured":"key missing")+" | Groq: "+(h.groq.configured?"key configured":"key missing"));const q=({...h.gemini.budget,...h.openrouter.budget,...h.groq.budget})[$("model").value];msg("quota",q?"طلبات الموقع خلال آخر 24 ساعة: "+q.local_attempts_24h+"/"+q.local_cap_24h+" · آخر دقيقة: "+q.local_attempts_60s+"/"+q.local_cap_60s+" (ليست الحصة المتبقية لدى المزود)":"النموذج المحلي لا يستهلك حصة سحابية");}
$("refresh-models").onclick=()=>refreshModels().catch(e=>msg("health",e.message));
$("model").onchange=()=>{$("cloud-consent").checked=false;refreshModels().catch(e=>msg("health",e.message))};

function setBusy(value){busy=value;for(const id of ["approve","run","draft","load","correct","mutant","propose","verify-patch","model","cloud-consent","import-problem","draft-reference","profile-run","source","profile-case"])$(id).disabled=value}
async function packages(selected){const p=await api("/api/v4/packages");$("packages").replaceChildren();for(const x of p){const opt=document.createElement("option");opt.value=x.key;opt.textContent=x.manifest.title+" · "+x.key.slice(0,8);$("packages").append(opt)}if(selected)$("packages").value=selected;}
function loadDemo(){activeDemo=$("demo").value;const d=demos[activeDemo];if(!d)return;$("package").value=JSON.stringify(d.package,null,2);$("statement").value=d.package.manifest.statement;$("source").value=d.mutant;$("reviewed").checked=false;$("trusted").checked=false;msg("approval","مسودة مثال؛ يجب المراجعة قبل الاعتماد.");}
$("load").onclick=loadDemo;
$("correct").onclick=()=>{$("source").value=demos[activeDemo].correct;$("trusted").checked=false};
$("mutant").onclick=()=>{$("source").value=demos[activeDemo].mutant;$("trusted").checked=false};
$("draft").onclick=async()=>{if(busy)return;setBusy(true);msg("approval","توليد مسودة باستخدام الموديل المختار...");try{let d=await api("/api/v4/packages/draft",{statement:$("statement").value,...aiOptions()});$("package").value=JSON.stringify({manifest:d.manifest,reference:"",controls:[]},null,2);$("reviewed").checked=false;msg("approval",d.warning)}catch(e){msg("approval",e.message)}finally{setBusy(false);refreshModels().catch(()=>{})}};
$("import-problem").onclick=async()=>{if(busy)return;setBusy(true);try{const r=await api("/api/v4/packages/import",{url:$("problem-url").value});$("statement").value=r.statement;$("import-samples").hidden=false;msg("import-samples",JSON.stringify({source:r.source_url,samples:r.samples},null,2));$("reviewed").checked=false;msg("approval",r.warning)}catch(e){msg("approval",e.message)}finally{setBusy(false)}};
$("draft-reference").onclick=async()=>{if(busy)return;setBusy(true);try{const p=JSON.parse($("package").value);const r=await api("/api/v4/packages/reference",{manifest:p.manifest,...aiOptions()});p.reference=r.reference;delete p.reference_alt;p.controls=[];$("package").value=JSON.stringify(p,null,2);$("reviewed").checked=false;msg("approval",r.warning+" — "+r.rationale)}catch(e){msg("approval",e.message)}finally{setBusy(false);refreshModels().catch(()=>{})}};
$("approve").onclick=async()=>{if(busy)return;setBusy(true);msg("approval","فحص المرجع ضمن Docker...");try{let p=JSON.parse($("package").value);let r=await api("/api/v4/packages/approve",{package:p,owner_reviewed:$("reviewed").checked});msg("approval",JSON.stringify(r.review,null,2));if(r.key)await packages(r.key)}catch(e){msg("approval",e.message)}finally{setBusy(false);refreshModels().catch(()=>{})}};
$("run").onclick=async()=>{if(busy)return;setBusy(true);analysisId=crypto.randomUUID().replaceAll("-","");$("cancel").hidden=false;$("results").hidden=true;msg("status","تنفيذ الحالات والبحث وإعادة التحقق...");try{const source=$("source").value;result=await api("/api/v4/analyze",{package_key:$("packages").value,source,trusted_local_source:$("trusted").checked,use_ai:$("ai").checked,...aiOptions(),generator:$("generator").value,guided:$("guided").checked,spectrum:$("spectrum").checked,count:Number($("count").value),analysis_id:analysisId});msg("status",result.status+" · "+(result.attempts||0)+" attempts");if(result.status==="observed_mismatch"){sources={student:source,reference:result.reference_source||""};side="student";index=0;show() }else msg("status",result.status+" — "+((result.scope||"No supported conclusion")+" | "+JSON.stringify(result.guidance||{})))}catch(e){msg("status",e.message)}finally{analysisId=null;$("cancel").hidden=true;setBusy(false);refreshModels().catch(()=>{})}};
$("cancel").onclick=async()=>{const id=analysisId;if(!id)return;for(let i=0;i<12&&analysisId===id;i++){try{await api("/api/v4/analysis/"+id+"/cancel",{});msg("status","Cancellation requested");return}catch(e){await new Promise(r=>setTimeout(r,150))}}};
function show(){$("repair-panel").hidden=result.status!=="observed_mismatch";msg("result-title",result.status==="profiled_execution"?"3. قياس تنفيذ واحد · "+result.kind:"3. الشاهد وأدلة التنفيذ");profileSelection=null;$("candidate").value="";$("patch-reviewed").checked=false;msg("patch-status","");msg("patch-diff","");msg("repair-history-view","");refreshRepairs().catch(()=>{});const w=result.witness;$("results").hidden=false;msg("stdin",w.stdin);msg("expected",w.reference.stdout);msg("actual",w.student.stdout||w.student.detail||w.student.status);msg("scope",result.scope+" | replay: "+result.replay_count+" | trace: "+w.student.trace_status+" | AI: "+result.ai_status+" · "+(result.ai_model||"")+" "+(result.ai_error||"")+" "+JSON.stringify(result.ai_usage||{}));$("hypotheses").replaceChildren();for(const h of result.hypotheses){const div=document.createElement("div");div.className="hypothesis";div.textContent=h.status+" — "+h.text+" ("+h.event_ids.join(", ")+")";if(h.status==="hypothesis")div.onclick=()=>{side="student";index=Math.max(0,w.student.events.findIndex(e=>e.event_id===h.event_ids[0]));render()};$("hypotheses").append(div)}if(!result.hypotheses.length)msg("hypotheses","لا توجد فرضيات متاحة؛ الأدلة لا تزال ظاهرة.");msg("facts",JSON.stringify(result.ai_facts||[],null,2));msg("probes",JSON.stringify(result.guidance||{},null,2));setupComparison();showRanking();render()}
function setupComparison(){
 for(const s of ["student","reference"]){const events=result.witness[s].events||[];const slider=$("cmp-"+s);slider.max=Math.max(0,events.length-1);slider.value=Math.max(0,events.findIndex(e=>e.kind==="line"&&e.line>=1));drawComparison(s)}
 const view=$("matrix-view");view.replaceChildren();
 for(const [name,value] of Object.entries(result.witness.case||{})){
  if(!Array.isArray(value))continue;
  const rows=Array.isArray(value[0])?value:[value];const heading=document.createElement("p");heading.textContent=name;view.append(heading);const table=document.createElement("table");
  for(const row of rows){const tr=document.createElement("tr");for(const cell of row){const td=document.createElement("td");td.textContent=String(cell);tr.append(td)}table.append(tr)}view.append(table)
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
function render(){const w=result.witness[side],events=w.events||[],g=result[side+"_graph"];index=Math.max(0,Math.min(index,events.length-1));const ev=events[index];$("slider").max=Math.max(0,events.length-1);$("slider").value=index;msg("step",(ev?ev.event_id+" · "+ev.kind+" · L"+ev.line:"No events")+" · "+w.trace_status);msg("locals",ev?JSON.stringify(ev.locals,null,2):"");const frames=new Map((g.frames||[]).map(f=>[f.id,f]));let stack=[],id=ev&&ev.frame_id;while(id&&frames.has(id)&&stack.length<32){const f=frames.get(id);stack.push(f.id+" · "+f.function);id=f.parent}msg("stack",stack.reverse().join("\n"));const code=$("code");code.replaceChildren();(sources[side]||"").split("\n").forEach((line,i)=>{const e=document.createElement("span");e.textContent=String(i+1).padStart(3)+"  "+line;if(ev&&ev.line===i+1)e.classList.add("active");if(profileSelection&&profileSelection.line<=i+1&&profileSelection.end_line>=i+1)e.classList.add("profile-range");code.append(e)});const container=$("graph");container.replaceChildren();let nodes=g.nodes.slice(0,128),positions=new Map(),svg=svgEl("svg",{viewBox:"0 0 440 "+Math.max(100,nodes.length*58+35),width:440,height:Math.max(100,nodes.length*58+35)});const defs=svgEl("defs",{}),marker=svgEl("marker",{id:"arrow",markerWidth:7,markerHeight:7,refX:6,refY:3,orient:"auto"});marker.append(svgEl("path",{d:"M0 0 L6 3 L0 6",stroke:"#94a3b8",fill:"#94a3b8"}));defs.append(marker);svg.append(defs);nodes.forEach((n,i)=>positions.set(n.id,{x:110,y:16+i*58}));for(const [i,e] of g.edges.entries()){const a=positions.get(e.from),b=positions.get(e.to);if(!a||!b)continue;const x=8+i%9*10;const d=e.from===e.to?"M 310 "+(a.y+12)+" C 390 "+(a.y-16)+" 390 "+(a.y+45)+" 310 "+(a.y+28):"M 110 "+(a.y+20)+" H "+x+" V "+(b.y+20)+" H 108";const path=svgEl("path",{d,"marker-end":"url(#arrow)"});const title=svgEl("title",{});title.textContent=e.count+" transitions";path.append(title);svg.append(path)}for(const n of nodes){const p=positions.get(n.id);const group=svgEl("g",{class:"node"+(ev&&n.event_ids.includes(ev.event_id)?" selected":""),tabindex:0,role:"button","aria-label":"line "+n.line});group.append(svgEl("rect",{x:p.x,y:p.y,width:200,height:40,rx:7}));const text=svgEl("text",{x:p.x+8,y:p.y+24});text.textContent=n.frame_id+" · L"+n.line+" · "+n.event_ids.length+"×"+(n.timing?" · "+(n.timing.self_wall_ns/1e6).toFixed(3)+"ms":"");const tip=svgEl("title",{});tip.textContent=n.timing?"Self wall: "+(n.timing.self_wall_ns/1e6).toFixed(6)+" ms · CPU: "+(n.timing.self_cpu_ns/1e6).toFixed(6)+" ms":"Timing unavailable";group.append(tip);if(n.timing&&n.timing.self_wall_ns>0){const peak=Math.max(...nodes.map(x=>x.timing?.self_wall_ns||0));group.classList.toggle("timing-hot",n.timing.self_wall_ns>=peak*.6)}group.append(text);const jump=()=>{index=events.findIndex(e=>e.event_id===n.event_ids[0]);render()};group.onclick=jump;group.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();jump()}};svg.append(group)}svg.style.width=(440*Number($("graph-zoom").value)/100)+"px";svg.style.height=(Math.max(100,nodes.length*58+35)*Number($("graph-zoom").value)/100)+"px";container.append(svg);$("changes").replaceChildren();for(const c of g.changes){let div=document.createElement("div");div.className="change";div.textContent=c.name+": "+JSON.stringify(c.before)+" → "+JSON.stringify(c.after)+" ("+c.before_event_id+"→"+c.after_event_id+")";$("changes").append(div)}$("relations").replaceChildren();for(const c of [...g.relations.data,...g.relations.control]){const div=document.createElement("button");div.className="change";div.textContent=c.write?JSON.stringify(c.reads)+" → "+c.write.name+"="+c.write.value:"L"+c.line+" → L"+c.target_line+" · "+c.condition;div.onclick=()=>{index=events.findIndex(e=>e.event_id===c.after_event_id);render()};$("relations").append(div)}for(const c of g.relations.def_use||[]){const b=document.createElement("button");b.className="change";b.textContent=c.name+"="+c.value+" · "+c.producer_event_id+" → "+c.consumer_event_id;b.onclick=()=>{index=events.findIndex(e=>e.event_id===c.consumer_event_id);render()};$("relations").append(b)}if(!$("relations").children.length)msg("relations","لا توجد علاقة مدعومة ضمن النطاق الحالي.");renderProfile();msg("output-chain",JSON.stringify(g.output_chain||{},null,2));msg("static-cfg",JSON.stringify(g.static_cfg||{},null,2))}
$("student").onclick=()=>{side="student";index=0;render()};$("reference").onclick=()=>{side="reference";index=0;render()};$("prev").onclick=()=>{index--;render()};$("next").onclick=()=>{index++;render()};$("slider").oninput=()=>{index=Number($("slider").value);render()};$("export").onclick=()=>{if(!result)return;const u=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=u;a.download="algoxray-v4-evidence.json";a.click();URL.revokeObjectURL(u)};
(async()=>{try{token=(await api("/api/session")).custom_code_token;await refreshModels();demos=await (await fetch("/static/v4-demos.json")).json();loadDemo();await packages()}catch(e){msg("health",e.message)}})();

function repairBody(){return {package_key:result.package_sha256,source:result.student_source,case:result.witness.case}}
$("propose").onclick=async()=>{if(busy||!result)return;setBusy(true);msg("patch-status","Generating a proposal using the selected model...");try{const r=await api("/api/v4/repair/propose",{...repairBody(),...aiOptions()});$("candidate").value=r.candidate;$("patch-reviewed").checked=false;msg("patch-status",r.status+" — "+r.rationale);msg("patch-diff",r.diff||"")}catch(e){msg("patch-status",e.message)}finally{setBusy(false);refreshModels().catch(()=>{})}};
$("verify-patch").onclick=async()=>{if(busy||!result)return;setBusy(true);msg("patch-status","Testing candidate against witness and regression cases...");try{const r=await api("/api/v4/repair/verify",{...repairBody(),candidate:$("candidate").value,reviewed:$("patch-reviewed").checked});msg("patch-status",JSON.stringify(r,null,2));await refreshRepairs()}catch(e){msg("patch-status",e.message)}finally{setBusy(false);refreshModels().catch(()=>{})}};

async function refreshRepairs(){
 if(!result)return;
 const rows=await api("/api/v4/repairs/"+result.package_sha256);$("repair-history").replaceChildren();
 for(const r of rows){const opt=document.createElement("option");opt.value=r.key;opt.textContent=r.status+" · "+r.key.slice(0,10);$("repair-history").append(opt)}
}
$("load-repair").onclick=async()=>{try{const key=$("repair-history").value;if(!key)return;const r=await api("/api/v4/repair/version/"+key);msg("repair-history-view",JSON.stringify(r,null,2))}catch(e){msg("repair-history-view",e.message)}};

function invalidateResult(){if(!busy){result=null;$("results").hidden=true;profileSelection=null}}
$("source").addEventListener("input",invalidateResult);
$("profile-case").addEventListener("input",invalidateResult);
for(const id of ["correct","mutant","load"])$(id).addEventListener("click",invalidateResult);
$("profile-run").onclick=async()=>{
 if(busy)return;
 let caseValue=null;
 try{caseValue=$("profile-case").value.trim()?JSON.parse($("profile-case").value):null}catch(e){msg("status","مدخل JSON غير صالح");return}
 setBusy(true);analysisId=crypto.randomUUID().replaceAll("-","");$("cancel").hidden=false;$("results").hidden=true;msg("status","قياس التنفيذ للطالب والمرجع...");
 try{
  const source=$("source").value;
  result=await api("/api/v4/profile",{package_key:$("packages").value,source,case:caseValue,trusted_local_source:$("trusted").checked,analysis_id:analysisId});
  msg("status",result.status+" · "+(result.kind||""));
  if(result.status==="profiled_execution"){sources={student:source,reference:result.reference_source||""};side="student";index=0;show()}
 }catch(e){msg("status",e.message)}finally{analysisId=null;$("cancel").hidden=true;setBusy(false)}
};
function profileRows(){
 const p=result?.[side+"_graph"]?.profile||{};
 const key=$("profile-cost").value+"_"+$("profile-clock").value+"_ns";
 return [...(p[$("profile-level").value]||[])].sort((a,b)=>(b[key]||0)-(a[key]||0)||a.line-b.line);
}
function renderProfile(){
 const p=result[side+"_graph"].profile||{status:"unavailable"};
 const ns=n=>Number.isFinite(n)?(n/1e6).toFixed(3):"—";
 msg("profile-summary",(side==="student"?"الطالب":"المرجع")+" · "+p.status+" · زمن التنفيذ "+ns(p.execution_wall_ns)+" ms · CPU "+ns(p.execution_cpu_ns)+" ms · كلفة أداة التتبع "+ns(p.callback_wall_ns)+" ms · تشغيل الحاوية والاتصال "+(result.witness[side].elapsed_ms??"—")+" ms");
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
