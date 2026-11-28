/* Educational projections of recorded AlgoXRay evidence. No new execution or AI inference.
 * Every timeline row comes from an event, and every chart point from a report.
 */
window.AlgoXRayStory=(()=>{
 "use strict";
 const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n};
 const add=(parent,...children)=>{parent.append(...children.filter(Boolean));return parent};
 const p=t=>el("p","story-note",t);
 const button=(t,fn)=>{const b=el("button","story-button",t);b.type="button";b.onclick=fn;return b};
 const mono=(tag,t)=>{const n=el(tag,"story-mono",t);n.dir="ltr";return n};
 const section=(title,sub)=>add(el("section","story-section"),el("h3","",title),sub?p(sub):null);
 const known=v=>v!==undefined&&!(v&&typeof v==="object"&&v.unavailable);
 const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
 const textValue=v=>!known(v)?"غير مسجل":typeof v==="string"?JSON.stringify(v):v===null?"None":typeof v==="boolean"?(v?"True":"False"):typeof v==="object"?JSON.stringify(v):String(v);
 const labelKind={line:"قبل السطر",call:"دخول الدالة",return:"عودة",exception:"استثناء"};
 const signalLabels={
  reported_exception_location:"العامل أبلغ عن استثناء في هذا السطر.",
  coverage_ochiai:"ظهر هذا السطر في تتبع حالات مرتبطة بالفشل.",
  observed_branch_ochiai:"ظهر انتقال فرع مرتبط بالحالات الفاشلة.",
  output_predecessor:"لقطة مرتبطة بالقيم السابقة للخرج.",
  repeated_condition:"تكرر رصد الشرط ضمن التتبع.",
  unchanged_assignment:"القيمة بقيت كما هي في اللقطات المدعومة.",
  range_index_omission:"نطاق الحلقة يتجاوز بعض فهارس القائمة المسجلة."
 };
 function values(v,old){
  const a=Array.isArray(v)?v:(v&&["list","tuple"].includes(v.kind)&&Array.isArray(v.items)?v.items:null);
  if(a){
   const wrap=el("div","story-array");wrap.dir="ltr";wrap.setAttribute("role","list");
   const prev=Array.isArray(old)?old:null;
   for(let i=0;i<Math.min(a.length,24);i++){
    const item=add(el("div","story-cell"),el("span","",i),el("strong","",textValue(a[i])));
    item.setAttribute("role","listitem");
    if(prev&&i<prev.length&&known(prev[i])&&known(a[i])&&!same(prev[i],a[i]))item.classList.add("story-changed");
    wrap.append(item);
   }
   if(v.truncated||a.length>24)wrap.append(el("span","story-more","… "+(v.size??a.length)+" items"));
   if(!a.length)wrap.append(el("span","story-more","[]"));
   return wrap;
  }
  const t=textValue(v);
  return mono("pre",t.length>1800?t.slice(0,1800)+"…":t);
 }
 function timeline(report,onEvidence){
  const w=report.witness?.student||{},events=Array.isArray(w.events)?w.events:[],lines=(report.student_source||"").split(/\r\n?|\n/);
  const host=section("كيف نفّذ برنامجك؟","حرّك المؤشر أو اختر خطوة لرؤية السطر والقيم المسجلة. اللقطات قبل تنفيذ السطر؛ لا نفترض قيم الأسطر غير المسجلة.");
  host.id="story-timeline";
  if(!events.length){host.append(p("لا توجد خطوات مسجلة لهذا التنفيذ."));return {host,select:()=>false}}
  const actions=el("div","story-transport"),prev=button("السابق",()=>select(pos-1)),next=button("التالي",()=>select(pos+1));
  prev.id="story-prev";next.id="story-next";
  const progress=el("strong","story-counter");progress.id="story-step";
  let playback=null;
  const play=button("تشغيل الخطوات",()=>{
   if(playback!==null){stop();return}
   if(pos===events.length-1)select(0);
   play.textContent="إيقاف";
   playback=setInterval(()=>{
    if(!host.isConnected||host.closest("[hidden]")||pos>=events.length-1){stop();return}
    select(pos+1);
   },650);
  });play.id="story-play";
  function stop(){if(playback!==null)clearInterval(playback);playback=null;play.textContent="تشغيل الخطوات"}
  const slider=el("input","story-slider");slider.type="range";slider.id="story-slider";slider.min="0";slider.max=String(events.length-1);slider.setAttribute("aria-label","خطوة التنفيذ المسجلة");
  const rail=el("div","story-rail");rail.id="story-rail";rail.setAttribute("aria-label","أحداث التنفيذ");
  const grid=el("div","story-step-grid"),code=el("div","story-step-code"),data=el("div","story-step-data");
  const line=mono("pre","");line.id="story-line";const meta=p("");meta.id="story-frame";
  const detail=button("عرض السطر في المخطط التفصيلي",()=>{const e=events[pos];onEvidence?.(e.line,e.event_id)});
  const delta=el("div","story-values");delta.id="story-values";
  add(code,el("h4","","السطر المحدد"),line,meta,detail);add(data,el("h4","","القيم في هذه اللحظة"),delta);
  add(grid,code,data);add(actions,prev,progress,play,next);add(host,actions,slider,rail,grid,
    p(w.trace_status==="complete"?"الخطوات المسجلة لهذا التنفيذ كاملة ضمن نطاق العامل.":"التتبع جزئي أو غير مكتمل؛ الرسم يعرض فقط الأحداث المتوفرة."));
  let pos=0;
  function select(i){
   if(!Number.isInteger(i)||i<0||i>=events.length)return false;
   pos=i;const e=events[i];slider.value=String(i);progress.textContent=(i+1)+" / "+events.length;
   prev.disabled=i===0;next.disabled=i===events.length-1;
   line.textContent=e.line>0?"L"+e.line+"  "+(lines[e.line-1]??""):"بداية إطار التنفيذ";meta.textContent=(labelKind[e.kind]||"حدث مسجل")+" · "+e.event_id+" · "+(e.function||"")+" · "+(e.frame_id||"");
   for(const b of rail.children){const active=Number(b.dataset.pos)===i;b.setAttribute("aria-current",active?"step":"false");}
   const current=e.locals||{};
   const previous=events.slice(0,i).reverse().find(x=>x.frame_id===e.frame_id);
   const prior=previous?.locals||{};
   const names=Object.keys(current);
   const changed=names.filter(k=>known(current[k])&&(!known(prior[k])||!same(current[k],prior[k])));
   const ordered=[...changed,...names.filter(k=>!changed.includes(k))];
   delta.replaceChildren();
   for(const k of ordered.slice(0,12)){
    const v=current[k],old=prior[k],different=known(v)&&known(old)&&!same(v,old);
    const card=el("div","story-variable");card.dataset.variable=k;
    add(card,add(el("div","story-var-title"),mono("strong",k),different?el("span","story-change-label","تغيّر مرصود"):null));
    if(different){
     const before=add(el("div","story-snapshot"),el("span","story-note","لقطة "+previous.event_id),values(old));
     const after=add(el("div","story-snapshot"),el("span","story-note","لقطة "+e.event_id),values(v,old));
     add(card,add(el("div","story-transition"),before,el("span","story-arrow","→"),after));
    }else card.append(values(v));
    delta.append(card);
   }
   if(!ordered.length)delta.append(p("لم تُسجل متغيرات محلية في هذه اللقطة."));
   if(ordered.length>12||e.snapshot_meta?.omitted_locals)delta.append(p("بعض القيم غير معروضة أو غير مسجلة. راجع اللقطة التفصيلية."));
   // Scroll only the rail, never move the page unexpectedly.
   const selected=rail.children[i];
   if(selected)rail.scrollLeft=selected.offsetLeft-rail.clientWidth/2+selected.offsetWidth/2;
   return true;
  }
  events.forEach((e,i)=>{
   const b=button("",()=>{stop();select(i)});b.classList.add("story-step-chip");b.dataset.pos=String(i);b.dataset.eventId=e.event_id;b.dir="ltr";
   add(b,el("small","",e.event_id),el("strong","","L"+e.line));b.title=(labelKind[e.kind]||e.kind)+" · "+e.function;rail.append(b);
  });
  slider.oninput=()=>{stop();select(Number(slider.value))};
  const firstArray=events.findIndex(e=>Object.values(e.locals||{}).some(v=>Array.isArray(v)||v?.kind==="list"));const first=firstArray>=0?firstArray:events.findIndex(e=>Object.keys(e.locals||{}).length);select(first<0?0:first);
  return {host,selectEvent:id=>{stop();return select(events.findIndex(e=>e.event_id===id))},selectLine:n=>{stop();return select(events.findIndex(e=>e.line===n))}};
 }
 function findings(report,trace){
  const loc=report.evidence_localization||{},rows=Array.isArray(loc.ranked)?loc.ranked:[];
  const host=section("أين أراجع الكود؟","ترتيب مبني على إشارات الأدلة المتاحة، لا نسبة احتمال ولا إثبات للسبب.");
  host.id="story-findings";
  if(report.status!=="observed_mismatch"){
   host.append(p("هذه لقطة من التنفيذ، وليست حالة فشل مثبتة؛ لن نعرض أسطراً على أنها أخطاء."));
   return host;
  }
  const lines=(report.student_source||"").split(/\r\n?|\n/);
  const candidates=rows.filter(r=>Number.isInteger(r.line)&&r.line>0&&r.line<=lines.length).slice(0,3);
  const judgment=report.witness?.judgment,reasonText={
   indices_not_distinct:"اختار الحل الفهرس نفسه مرتين؛ قاعدة المسألة تشترط فهرسين مختلفين.",
   index_out_of_bounds:"أحد الفهارس خارج حدود القائمة.",
   sum_does_not_match_target:"مجموع القيم المختارة لا يطابق الهدف.",
   solution_exists:"يوجد زوج صالح، بينما أفاد الحل بعدم وجود حل."
  };
  if(judgment?.status==="rejected"&&reasonText[judgment.reason])host.append(p(reasonText[judgment.reason]));
  if(report.kind==="exception"&&report.witness?.student?.detail)host.append(p("توقف البرنامج بسبب استثناء أبلغ عنه العامل: "+report.witness.student.detail+"."));
  if(candidates.length){
   const center=candidates[0].line,first=Math.max(1,center-4),last=Math.min(lines.length,center+6),map=el("div","story-code-map");map.id="story-code-map";map.dir="ltr";
   for(let i=first;i<=last;i++){
    const rank=candidates.findIndex(r=>r.line===i),row=el("div","story-code-row");
    if(rank>=0)row.dataset.rank=String(rank+1);
    add(row,el("span","story-line-number",i),mono("code",lines[i-1]||" "),rank>=0?el("span","story-rank",rank+1):null);
    map.append(row);
   }
   add(host,p("ترشيحات على الكود الفعلي (الأرقام ترتيب المراجعة فقط)."),map);
  }
  if(!candidates.length)host.append(p("وجدنا اختلافاً أو استثناء، لكن الأدلة لا تكفي لتحديد موضع السبب. قد يكون شرط أو سطر مفقوداً."));
  for(const [i,r] of candidates.entries()){
   const b=button("",()=>{
    const id=r.event_ids?.find(x=>report.witness.student.events?.some(e=>e.event_id===x&&e.line===r.line));
    const selected=id?trace.selectEvent?.(id):trace.selectLine?.(r.line);
    if(selected)trace.host.scrollIntoView({block:"start"});
    else onMissing.textContent="لا توجد لقطة لهذا السطر؛ الملاحظة تخص المصدر فقط.";
   });
   const onMissing=p("");b.classList.add("story-finding");b.dataset.line=String(r.line);b.dataset.rank=String(i+1);
   const evidence=(r.signals||[]).map(s=>signalLabels[s.kind]).filter(Boolean);
   add(b,add(el("div","story-finding-top"),el("span","","مرشح "+(i+1)),mono("strong","L"+r.line)),
     mono("pre",lines[r.line-1]),el("span","story-note",evidence.join(" ")||"إشارة مسجلة في تقرير المحرك."));
   add(host,b,onMissing);
  }
  const bounds=(loc.loop_bounds||[]).find(b=>Number.isInteger(b.array_length)&&b.array_length>0&&b.array_length<=24&&Array.isArray(b.omitted_indices)&&Array.isArray(b.observed_read_indices));
  if(bounds){
   const strip=el("div","story-array story-range");strip.dir="ltr";
   for(let i=0;i<bounds.array_length;i++){
    const read=bounds.observed_read_indices.includes(i),omitted=bounds.omitted_indices.includes(i);
    const v=add(el("div","story-cell"),el("span","","index"),el("strong","",i));v.classList.add(read?"story-read":omitted?"story-skipped":"story-unknown");strip.append(v);
   }
   add(host,el("h4","","فهارس القائمة "+bounds.array+" في الحلقة"),strip,
    p("الأخضر: قراءات مدعومة. البرتقالي: فهارس خارج النطاق المحسوب للحلقة. تحقق إن كانت المسألة تتطلب معالجتها."));
  }
  const hypotheses=(report.hypotheses||[]).filter(h=>h.status==="hypothesis"&&!h.conflicting_claims).slice(0,2);
  for(const h of hypotheses){
   const card=add(el("div","story-hypothesis"),el("strong","","تفسير مقترح من AI — غير مؤكد"),p(h.text));
   if(h.basis==="recorded"&&Array.isArray(h.event_ids)){
    const id=h.event_ids.find(id=>report.witness.student.events?.some(e=>e.event_id===id&&e.line===h.line));
    if(id)card.append(button("راجع اللقطة",()=>{if(trace.selectEvent?.(id))trace.host.scrollIntoView({block:"start"})}));
   }
   host.append(card);
  }
  if(loc.effect_site?.line)add(host,p("موضع ظهور الأثر: السطر "+loc.effect_site.line+"؛ قد يختلف عن موضع العيب."));
  return host;
 }
 function shrink(report){
  const r=report.reduction;
  const host=section("كيف صغّرنا حالة الفشل؟","المراحل المقبولة فعلاً، وليست جميع محاولات البحث أو ضماناً لأصغر حالة ممكنة.");
  host.id="story-shrink";
  if(!r||!Array.isArray(r.original_complexity)||!Array.isArray(r.reduced_complexity)){host.append(p("لا توجد مراحل تصغير لهذا التنفيذ."));return host}
  const steps=[{complexity:r.original_complexity,stdin:report.original_witness?.stdin},...(r.accepted||[])];
  const size=steps[0].complexity[0];
  const useSize=steps.some(x=>x.complexity?.[0]!==size);
  const k=useSize?0:1,metric=useSize?"حجم البنية (عدد العناصر/الحروف)":"مقياس القيم المستخدم في التصغير";
  const max=Math.max(1,...steps.map(x=>Number(x.complexity?.[k])||0));
  const barRows=el("div","story-bars");barRows.id="story-shrink-bars";
  const preview=mono("pre",steps[0].stdin||"");preview.id="story-shrink-input";
  const stepLabel=p("المدخل الأصلي");
  function selectStep(i){preview.textContent=steps[i].stdin||"";stepLabel.textContent=i?"المدخل بعد المرحلة "+i:"المدخل الأصلي";for(const b of barRows.children)b.setAttribute("aria-pressed",String(Number(b.dataset.step)===i))}

  for(const [i,s] of steps.entries()){
   const v=s.complexity?.[k];if(!Number.isFinite(v)||v<0)continue;
   const row=button("",()=>selectStep(i));row.classList.add("story-bar-row");row.dataset.step=String(i);row.setAttribute("aria-pressed",String(i===0));
   const fill=el("div","story-bar-fill");fill.style.width=(v/max*100)+"%";
   add(row,el("span","",i===0?"المدخل الأصلي":"مرحلة "+i),add(el("div","story-bar-track"),fill),mono("strong",v));
   row.title=(s.stdin||"").slice(0,500);barRows.append(row);
  }
  add(host,p(metric),barRows,stepLabel,preview,p("المحاولات: "+r.probes+" · مراحل مقبولة: "+(r.accepted||[]).length+" · إعادات تحقق المدخل الأخير: "+(r.reduced_replay_count||0)));
  if(!r.accepted?.length)host.append(p(r.probes?"لم نعثر على مدخل أصغر ضمن الميزانية المستخدمة.":"لم تُنفّذ محاولات تصغير في هذا الطلب."));else selectStep(steps.length-1);
  return host;
 }
 function hotspots(report,trace){
  const profile=report.witness?.student?.profile;
  if(!profile||!Array.isArray(profile.lines))return null;
  const rows=profile.lines.filter(r=>Number.isFinite(r.self_wall_ns)&&r.self_wall_ns>0&&Number.isInteger(r.line)).sort((a,b)=>b.self_wall_ns-a.self_wall_ns).slice(0,4);
  if(!rows.length)return null;
  const host=section("أين استغرق التنفيذ وقتاً؟","زمن السطر الذاتي أثناء التتبع، باستثناء زمن استدعاءات الطفل المسجلة. ليس زمن التشغيل العادي. "+(profile.status==="complete"?"القياس مكتمل ضمن نطاق العامل.":"القياس جزئي."));
  host.id="story-hotspots";const bars=el("div","story-bars");const max=rows[0].self_wall_ns;
  for(const r of rows){
   const b=button("",()=>{
    const event=report.witness.student.events?.find(e=>e.line===r.line&&e.frame_id===r.frame_id);
    if(event&&trace.selectEvent?.(event.event_id))trace.host.scrollIntoView({block:"start"});
   });b.classList.add("story-bar-row");b.dataset.line=String(r.line);
   const fill=el("div","story-bar-fill");fill.style.width=(r.self_wall_ns/max*100)+"%";
   add(b,mono("span","L"+r.line+" · "+r.frame_id),add(el("div","story-bar-track"),fill),mono("strong",(r.self_wall_ns/1e6).toFixed(4)+" ms"));bars.append(b);
  }
  host.append(bars);return host;
 }
 function execution(report,onEvidence){
  const host=el("div","story-execution");host.id="story-execution";
  if(!report?.witness)return host;
  const trace=timeline(report,onEvidence);
  if(report.status==="observed_mismatch")add(host,findings(report,trace),shrink(report));
  add(host,trace.host,hotspots(report,trace));
  return host;
 }
 function performance(report){
  const host=section("زمن التشغيل الفعلي","قياسات دون تتبع؛ الأعمدة تمثل تشغيلات مستقلة أو وسيط الزمن لكل حجم عند قياس النمو. لا نخلط زمن الحاوية أو التتبع مع زمن البرنامج.");
  host.id="story-performance";
  const points=Array.isArray(report?.points)?report.points:[];
  if(!points.length){host.append(p("لا توجد قياسات مكتملة."));return host}
  const scaling=points.length>1&&points.every(p=>Number.isFinite(p.size));
  const rows=scaling?points.map(q=>({label:(report.size_field||"size")+" = "+q.size,value:q.summary?.wall_ns?.median,status:q.summary?.completed===q.summary?.requested?"ok":"partial",suffix:q.summary?.completed+"/"+q.summary?.requested})):
   (points[0].runs||[]).map((q,i)=>({label:"تشغيل "+(i+1),value:q.wall_ns,status:q.status,suffix:q.status}));
  const valid=rows.filter(q=>Number.isFinite(q.value)&&q.value>=0&&q.status==="ok");
  const max=Math.max(1,...valid.map(q=>q.value));
  const bars=el("div","story-bars");bars.id="story-performance-bars";
  for(const r of rows){
   const ok=valid.includes(r);const fill=el("div","story-bar-fill");fill.style.width=(ok?r.value/max*100:0)+"%";
   const row=add(el("div","story-bar-row"),el("span","",r.label),add(el("div","story-bar-track"),fill),mono("strong",ok?(r.value/1e6).toFixed(4)+" ms":r.status==="timeout"?"انتهت المهلة":"غير مكتمل"));
   bars.append(row);
  }
  host.append(bars);
  const point=points[0],s=point.summary||{};
  if(!scaling){
   const cards=el("div","story-time-summary");
   for(const [title,v] of [["الوسيط",s.wall_ns?.median],["الأقل",s.wall_ns?.min],["الأعلى",s.wall_ns?.max]]){
    add(cards,add(el("div","story-metric"),el("span","",title),mono("strong",Number.isFinite(v)?(v/1e6).toFixed(4)+" ms":"—")));
   }host.append(cards);
   host.append(p("هذا مدخل واحد؛ لا يمكن استنتاج معدل نمو الزمن أو التعقيد منه."));
  }else{
   const g=report.growth||{};
   host.append(p(Number.isFinite(g.wall_log_log_exponent)?"ميل النمو المرصود على الأحجام المقاسة: "+g.wall_log_log_exponent.toFixed(2)+"؛ ليس إثباتاً لفئة التعقيد.":"البيانات غير كافية أو غير مستقرة لتقدير نمو موثوق."));
  }
  if(points.some(q=>q.correctness==="recorded_mismatch"))host.append(p("تنبيه: بعض القياسات تخص خرجاً غير مطابق للمرجع؛ السرعة لا تعني صحة الحل."));
  if(report.stop_reason!=="completed")host.append(p("القياس غير مكتمل: "+report.stop_reason));
  return host;
 }
 return {execution,performance};
})();
