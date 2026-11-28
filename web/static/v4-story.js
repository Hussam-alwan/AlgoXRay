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
 const textValue=v=>window.AlgoXRayLearning.value(v);
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
  const structured=window.AlgoXRayLearning.tableValue(v,old);if(structured)return structured;
  const a=Array.isArray(v)?v:(v&&["list","tuple"].includes(v.kind)&&Array.isArray(v.items)?v.items:null);
  if(a){
   const wrap=el("div","story-array");wrap.dir="ltr";wrap.setAttribute("role","list");
   const prev=Array.isArray(old)?old:old&&["list","tuple"].includes(old.kind)&&Array.isArray(old.items)?old.items:null;
   for(let i=0;i<Math.min(a.length,24);i++){
    const item=add(el("div","story-cell"),el("span","",i),el("strong","",textValue(a[i])));
    item.setAttribute("role","listitem");
    if(prev&&i<prev.length&&window.AlgoXRayLearning.changed(prev[i],a[i]))item.classList.add("story-changed");
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
  const host=section("كيف نفّذ برنامجك؟");
  host.id="story-timeline";
  if(!events.length){host.append(p("لا توجد خطوات مسجلة لهذا التنفيذ."));return {host,select:()=>false}}
  const actions=el("div","story-transport"),prev=button("السابق",()=>{stop();select(pos-1)}),next=button("التالي",()=>{stop();select(pos+1)});
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
  const slider=el("input","story-slider");slider.type="range";slider.dir="ltr";slider.id="story-slider";slider.min="0";slider.max=String(events.length-1);slider.setAttribute("aria-label","خطوة التنفيذ المسجلة");
  const rail=el("div","story-rail");rail.id="story-rail";rail.setAttribute("aria-label","أحداث التنفيذ");
  const grid=el("div","story-step-grid"),code=el("div","story-step-code"),data=el("div","story-step-data");
  const line=mono("pre","");line.classList.add("story-line-fallback");const meta=p("");meta.id="story-frame";
  const detail=button("عرض السطر في المخطط التفصيلي",()=>{const e=events[pos];onEvidence?.(e.line,e.event_id)});
  const delta=el("div","story-values");delta.id="story-values";
  add(code,el("h4","","الكود عند الخطوة"),meta);
  const previousByFrame=new Map();
  const previousEvents=events.map(e=>{const previous=previousByFrame.get(e.frame_id);previousByFrame.set(e.frame_id,e);return previous});
  const learning=window.AlgoXRayLearning.build(report,events,previousEvents,lines,i=>{stop();select(i)});
  const inspector=learning.host;
  const explanation=inspector.querySelector("#learning-explain"),relation=inspector.querySelector("#learning-relations");
  const context=inspector.querySelector("#learning-source"),frames=inspector.querySelector("#learning-frames");
  add(code,context,line,detail);add(data,explanation,relation,delta);
  const prediction=inspector.querySelector("#learning-predict"),keyNav=inspector.querySelector(".learning-key-nav");
  if(w.trace_status!=="complete")host.append(el("p","story-trace-status","التتبع جزئي أو غير مكتمل. يعرض الرسم الأحداث المتوفرة."));
  add(grid,code,data);
  add(actions,add(el("div","story-step-buttons"),prev,play,next),progress,keyNav);
  add(host,add(el("div","story-controls"),actions,slider,rail),grid,prediction,frames);
  let pos=0;
  function select(i){
   if(!Number.isInteger(i)||i<0||i>=events.length)return false;
   const previousChip=rail.children[pos];
   if(previousChip){previousChip.removeAttribute("aria-current");previousChip.tabIndex=-1}
   pos=i;const e=events[i];slider.value=String(i);progress.textContent=(i+1)+" / "+events.length;
   slider.setAttribute("aria-valuetext",`الخطوة ${i+1} من ${events.length}`);
   prev.disabled=i===0;next.disabled=i===events.length-1;
   line.textContent=e.line>0?"L"+e.line+"  "+(lines[e.line-1]??""):"بداية إطار التنفيذ";meta.textContent=(labelKind[e.kind]||"حدث مسجل")+" · "+e.event_id+" · "+(e.function||"")+" · "+(e.frame_id||"");
   const current=e.locals||{};
   const previous=previousEvents[i];
   const prior=previous?.locals||{};
   const names=Object.keys(current);
   const changed=names.filter(k=>known(current[k])&&(!known(prior[k])||window.AlgoXRayLearning.changed(prior[k],current[k])));
   const ordered=[...changed,...names.filter(k=>!changed.includes(k))];
   delta.replaceChildren();
   let chartShown=false;
   for(const k of ordered.slice(0,12)){
    const v=current[k],old=prior[k],different=window.AlgoXRayLearning.changed(old,v);
    const card=el("div","story-variable");card.dataset.variable=k;
    add(card,add(el("div","story-var-title"),mono("strong",k),different?el("span","story-change-label","تغيّر مرصود"):null));
    if(different){
     const before=add(el("div","story-snapshot"),el("span","story-note","اللقطة السابقة"),values(old));
     const after=add(el("div","story-snapshot"),el("span","story-note","اللقطة الحالية"),values(v,old));
     add(card,add(el("div","story-transition"),before,el("span","story-arrow","→"),after));
    }else card.append(values(v,old));
    if(!chartShown){
     const chart=window.AlgoXRayLearning.numericBars(v,old);
     if(chart){
      chartShown=true;
      const d=el("details","learning-array-details");d.open=Boolean(chart.querySelector(".learning-reorder"));
      add(d,el("summary","",d.open?"تغيّرت مواضع القيم":"رسم القيم العددية"),chart);
      if(d.open)card.querySelector(".story-var-title").after(d);else card.append(d);
     }
    }
    delta.append(card);
   }
   if(!ordered.length)delta.append(p("لم تُسجل متغيرات محلية في هذه اللقطة."));
   if(ordered.length>12||e.snapshot_meta?.omitted_locals)delta.append(p("بعض القيم غير معروضة أو غير مسجلة. راجع اللقطة التفصيلية."));
   learning.render(i);
   const activeLine=context.querySelector('[aria-current="step"]');
   line.hidden=Boolean(activeLine);line.id=activeLine?"":"story-line";
   if(activeLine)activeLine.id="story-line";
   // Scroll only the rail, never move the page unexpectedly.
   const selected=rail.children[i];
   if(selected){selected.setAttribute("aria-current","step");selected.tabIndex=0;rail.scrollLeft=selected.offsetLeft-rail.clientWidth/2+selected.offsetWidth/2}
   return true;
  }
  events.forEach((e,i)=>{
   const b=button("",()=>{stop();select(i)});b.classList.add("story-step-chip");b.dataset.pos=String(i);b.dataset.eventId=e.event_id;b.dir="ltr";b.tabIndex=-1;
   add(b,el("small","",e.event_id),el("strong","","L"+e.line));b.title=(labelKind[e.kind]||e.kind)+" · "+e.function;rail.append(b);
  });
  rail.addEventListener("keydown",e=>{
   if(!e.target.closest(".story-step-chip"))return;
   const target={ArrowLeft:Math.max(0,pos-1),ArrowRight:Math.min(events.length-1,pos+1),Home:0,End:events.length-1}[e.key];
   if(!Number.isInteger(target))return;
   e.preventDefault();stop();select(target);rail.children[target].focus({preventScroll:true});
  });
  slider.oninput=()=>{stop();select(Number(slider.value))};
  const firstArray=events.findIndex(e=>Object.values(e.locals||{}).some(v=>Array.isArray(v)||v?.kind==="list"));const first=firstArray>=0?firstArray:events.findIndex(e=>Object.keys(e.locals||{}).length);select(first<0?0:first);
  return {host,stop,selectEvent:id=>{stop();return select(events.findIndex(e=>e.event_id===id))},selectLine:n=>{stop();return select(events.findIndex(e=>e.line===n))}};
 }
 function compareWitness(report){
  const witness=report.witness;
  const host=el("div","story-witness");
  const mismatch=report.kind==="wrong_answer";
  const sample=witness.judgment?.reference_output_is_example;
  const observed=witness.student;
  const expected=witness.reference;
  const output=(title,run,tone)=>{
   const text=run?.stdout;
   const body=typeof text==="string"&&text.length?text:
    run?.status==="ok"?"(بدون خرج)":run?.detail||"الخرج غير متاح";
   const cell=add(el("div","story-io-cell"),el("h4","",title),mono("pre",body));
   cell.dataset.tone=tone;
   return cell;
  };
  const input=add(el("details","story-witness-input"),el("summary","","مدخل حالة الفشل"),mono("pre",witness.stdin||""));
  const outputs=add(el("div","story-witness-outputs"),output("خرج برنامجك",observed,mismatch?"mismatch":""),
    output(sample?"مثال لخرج مقبول":"الخرج المرجعي",expected,"reference"));
  const traces=el("details","story-witness-traces");
  add(traces,el("summary","","قارن خطوات الحل والمرجع"),p("المساران على المدخل نفسه. حرّك مؤشر كل مسار بشكل مستقل."));
  const columns=el("div","story-compare-columns");
  for(const [run,title,source] of [[observed,"برنامجك",report.student_source],[expected,"الحل المرجعي",report.reference_source]]){
   const panel=add(el("div","story-compare-path"),el("h4","",title));
   const events=run?.events||[];
   if(!events.length){
    panel.append(p(run?.trace_status==="disabled"?"لم يُسجّل تتبع لهذا المسار.":"لا توجد خطوات محفوظة لهذا المسار."));
   }else{
    const lines=(source||"").split(/\r\n?|\n/);
    const count=el("span","story-counter"),range=el("input","story-slider");
    range.type="range";range.dir="ltr";range.min="0";range.max=String(events.length-1);
    range.value=String(Math.max(0,events.findIndex(e=>e.kind==="line")));
    range.setAttribute("aria-label","خطوات "+title);
    const snapshot=el("div","story-compare-snapshot");
    range.oninput=()=>{
     const index=Number(range.value),event=events[index];
     count.textContent=(index+1)+" / "+events.length;
     range.setAttribute("aria-valuetext",`الخطوة ${index+1} من ${events.length}`);
     snapshot.replaceChildren(p((labelKind[event.kind]||"حدث مسجل")+" · "+event.event_id));
     if(lines[event.line-1]!==undefined&&source)snapshot.append(mono("pre","L"+event.line+"  "+lines[event.line-1]));
     const entries=Object.entries(event.locals||{});
     for(const [name,value] of entries.slice(0,6))snapshot.append(add(el("div","story-compare-value"),mono("strong",name),values(value)));
     if(!entries.length)snapshot.append(p("لا توجد قيم محلية مسجلة في هذه اللقطة."));
     if(entries.length>6||event.snapshot_meta?.omitted_locals)snapshot.append(p("بعض القيم غير معروضة أو غير مسجلة."));
    };
    if(run.trace_status!=="complete")panel.append(p("هذا التتبع جزئي أو غير مكتمل."));
    add(panel,count,range,snapshot);range.oninput();
   }
   columns.append(panel);
  }
  traces.append(columns);
  return add(host,outputs,input,traces);
 }
 function findings(report,trace,onTrace){
  const loc=report.evidence_localization||{},rows=Array.isArray(loc.ranked)?loc.ranked:[];
  const sample=report.status==="codeforces_samples";
  const host=section(sample?"ماذا حدث على المثال المنشور؟":"ماذا حدث في حالة الفشل؟");
  host.id="story-findings";
  if(report.status!=="observed_mismatch"&&!report.sample_attention){
   host.append(p("هذه لقطة من التنفيذ، وليست حالة فشل مثبتة؛ لن نعرض أسطراً على أنها أخطاء."));
   return host;
  }
  if(sample){
   if(report.judgment.status==="example_difference")host.append(p("خرج البرنامج مختلف عن المثال المنشور. بعض المسائل تقبل أكثر من خرج، لذلك راجع النتيجة حسب نص المسألة."));
   if(report.kind==="timeout")host.append(p("تجاوز التنفيذ المهلة المحلية على هذا المدخل."));
  }else host.append(compareWitness(report));
  const lines=(report.student_source||"").split(/\r\n?|\n/);
  const candidates=rows.filter(r=>Number.isInteger(r.line)&&r.line>0&&r.line<=lines.length).slice(0,3);
  const judgment=report.witness?.judgment,reasonText={
   indices_not_distinct:"اختار الحل الفهرس نفسه مرتين؛ قاعدة المسألة تشترط فهرسين مختلفين.",
   index_out_of_bounds:"أحد الفهارس خارج حدود القائمة.",
   sum_does_not_match_target:"مجموع القيم المختارة لا يطابق الهدف.",
   solution_exists:"يوجد زوج صالح، بينما أفاد الحل بعدم وجود حل."
  };
  if(judgment?.status==="rejected"&&reasonText[judgment.reason])host.append(p(reasonText[judgment.reason]));
  if(report.witness.student.status==="exception"&&report.witness.student.detail)host.append(p("توقف البرنامج أثناء التشغيل: "+report.witness.student.detail+"."));
  const review=add(el("div","story-fault-review"),el("h4","","سطور تستحق المراجعة"),p("الترتيب مبني على الأدلة المتوفرة. قد يكون السبب في موضع آخر."));
  host.append(review);
  const reviewGrid=el("div","story-fault-grid"),reviewActions=el("div","story-fault-actions");
  if(candidates.length){
   const center=candidates[0].line,first=Math.max(1,center-4),last=Math.min(lines.length,center+6),map=el("div","story-code-map");map.id="story-code-map";map.dir="ltr";
   for(let i=first;i<=last;i++){
    const rank=candidates.findIndex(r=>r.line===i),row=el("div","story-code-row");
    if(rank>=0)row.dataset.rank=String(rank+1);
    add(row,el("span","story-line-number",i),mono("code",lines[i-1]||" "),rank>=0?el("span","story-rank",rank+1):null);
    map.append(row);
   }
   add(review,add(reviewGrid,map,reviewActions));
  }
  if(!candidates.length)host.append(p("الأدلة المتوفرة لا تكفي لتحديد سطر بعينه."));
  for(const [i,r] of candidates.entries()){
   const b=button("",()=>{
    const id=r.event_ids?.find(x=>report.witness.student.events?.some(e=>e.event_id===x&&e.line===r.line));
    const selected=id?trace.selectEvent?.(id):trace.selectLine?.(r.line);
    if(selected){onTrace?.();trace.host.scrollIntoView({block:"start"})}
    else onMissing.textContent="لا توجد لقطة لهذا السطر؛ الملاحظة تخص المصدر فقط.";
   });
   const onMissing=p("");onMissing.setAttribute("role","status");b.classList.add("story-finding");b.dataset.line=String(r.line);b.dataset.rank=String(i+1);
   const evidence=(r.signals||[]).map(s=>signalLabels[s.kind]).filter(Boolean);
   add(b,add(el("div","story-finding-top"),el("span","","شاهد دليل السطر"),mono("strong","L"+r.line)),
     el("span","story-note",evidence.join(" ")||"إشارة مسجلة في تقرير المحرك."));
   add(reviewActions,b,onMissing);
  }
  const bounds=(loc.loop_bounds||[]).find(b=>Number.isInteger(b.array_length)&&b.array_length>0&&b.array_length<=24&&Array.isArray(b.omitted_indices)&&Array.isArray(b.observed_read_indices));
  if(bounds){
   const skipped=bounds.omitted_indices.filter(Number.isInteger);
   if(skipped.length){
    const note=add(el("div","learning-fault-explanation"),el("strong","","ماذا توضّح الحلقة؟"),p("راجع هل تتطلب المسألة معالجة الفهارس خارج نطاق الحلقة."));
    host.append(note);
   }
   const strip=el("div","story-array story-range");strip.dir="ltr";
   for(let i=0;i<bounds.array_length;i++){
    const read=bounds.observed_read_indices.includes(i),omitted=bounds.omitted_indices.includes(i);
    const v=add(el("div","story-cell"),el("strong","",i),el("span","",read?"قراءة مرصودة":omitted?"خارج النطاق":"غير مؤكد"));v.classList.add(read?"story-read":omitted?"story-skipped":"story-unknown");strip.append(v);
   }
   add(host,el("h4","","فهارس القائمة "+bounds.array+" في الحلقة"),strip);
  }
  const hypotheses=(report.hypotheses||[]).filter(h=>h.status==="hypothesis"&&!h.conflicting_claims).slice(0,2);
  for(const h of hypotheses){
   const card=add(el("div","story-hypothesis"),el("strong","","تفسير مقترح من AI — غير مؤكد"),p(h.text));
   if(h.basis==="recorded"&&Array.isArray(h.event_ids)){
    const id=h.event_ids.find(id=>report.witness.student.events?.some(e=>e.event_id===id&&e.line===h.line));
    if(id)card.append(button("راجع اللقطة",()=>{if(trace.selectEvent?.(id)){onTrace?.();trace.host.scrollIntoView({block:"start"})}}));
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
 function hotspots(report,trace,onTrace){
  const profile=report.witness?.student?.profile;
  if(!profile||!Array.isArray(profile.lines))return null;
  const rows=profile.lines.filter(r=>Number.isFinite(r.self_wall_ns)&&r.self_wall_ns>0&&Number.isInteger(r.line)).sort((a,b)=>b.self_wall_ns-a.self_wall_ns).slice(0,4);
  if(!rows.length)return null;
  const host=section("زمن الأسطر أثناء التتبع","زمن تنفيذ السطر نفسه، باستثناء وقت الاستدعاءات المسجلة. "+(profile.status==="complete"?"":"القياس جزئي."));
  host.id="story-hotspots";const bars=el("div","story-bars");const max=rows[0].self_wall_ns;
  for(const r of rows){
   const b=button("",()=>{
    const event=report.witness.student.events?.find(e=>e.line===r.line&&e.frame_id===r.frame_id);
    if(event&&trace.selectEvent?.(event.event_id)){onTrace?.();trace.host.scrollIntoView({block:"start"})}
   });b.classList.add("story-bar-row");b.dataset.line=String(r.line);
   const fill=el("div","story-bar-fill");fill.style.width=(r.self_wall_ns/max*100)+"%";
   add(b,mono("span","L"+r.line+" · "+r.frame_id),add(el("div","story-bar-track"),fill),mono("strong",(r.self_wall_ns/1e6).toFixed(4)+" ms"));bars.append(b);
  }
  host.append(bars);return host;
 }
 function execution(report,onEvidence,onTrace){
  const host=el("div","story-execution");host.id="story-execution";
  if(!report?.witness)return host;
  const trace=timeline(report,onEvidence);
  if(report.status==="observed_mismatch")add(host,findings(report,trace,onTrace),shrink(report));
  if(report.sample_attention)host.append(findings(report,trace,onTrace));
  add(host,trace.host,hotspots(report,trace,onTrace));host.stopPlayback=()=>trace.stop?.();
  return host;
 }
 function performance(report){
  const host=section("زمن التشغيل دون تتبع","القياس يخص تنفيذ البرنامج على المدخلات المختارة.");
  host.id="story-performance";
  const points=Array.isArray(report?.points)?report.points:[];
  if(!points.length){host.append(p("لا توجد قياسات مكتملة."));return host}
  const scaling=points.length>1&&points.every(p=>Number.isFinite(p.size));
  const rows=scaling?points.map(q=>({label:(report.size_field||"size")+" = "+q.size,value:q.summary?.wall_ns?.median,status:q.summary?.completed===q.summary?.requested?"ok":"partial"})):
   (points[0].runs||[]).map((q,i)=>({label:"تشغيل "+(i+1),value:q.wall_ns,status:q.status}));
  const valid=rows.filter(q=>Number.isFinite(q.value)&&q.value>=0&&q.status==="ok");
  const max=Math.max(1,...valid.map(q=>q.value));
  const bars=el("div","story-bars");bars.id="story-performance-bars";
  for(const r of rows){
   const ok=valid.includes(r);const fill=el("div","story-bar-fill");fill.style.width=(ok?r.value/max*100:0)+"%";
   const row=add(el("div","story-bar-row"),el("span","",r.label),add(el("div","story-bar-track"),fill),mono("strong",ok?(r.value/1e6).toFixed(4)+" ms":r.status==="timeout"?"انتهت المهلة":"غير مكتمل"));
   bars.append(row);
  }
  const curve=window.AlgoXRayLearning.growth(report);
  const point=points[0],s=point.summary||{};
  if(!scaling){
   const cards=el("div","story-time-summary");
   if(Number.isFinite(s.wall_ns?.median)){
    for(const [title,v] of [["الوسيط",s.wall_ns?.median],["الأقل",s.wall_ns?.min],["الأعلى",s.wall_ns?.max]]){
     add(cards,add(el("div","story-metric"),el("span","",title),mono("strong",Number.isFinite(v)?(v/1e6).toFixed(4)+" ms":"—")));
    }
    host.append(cards);
   }else host.append(p("لم يكتمل أي تشغيل صالح لقياس الزمن."));
   if(rows.length)host.append(bars);
   if(valid.length)host.append(p("هذا القياس لمدخل واحد. تقدير النمو يحتاج إلى أحجام مختلفة."));
  }else{
   host.append(curve||bars);
   const g=report.growth||{};
   host.append(p(Number.isFinite(g.wall_log_log_exponent)?"ميل النمو المرصود على الأحجام المقاسة: "+g.wall_log_log_exponent.toFixed(2)+"؛ ليس إثباتاً لفئة التعقيد.":"البيانات غير كافية أو غير مستقرة لتقدير نمو موثوق."));
  }
  if(points.some(q=>q.correctness==="recorded_mismatch"))host.append(p("تنبيه: بعض القياسات تخص خرجاً غير مطابق للمرجع؛ السرعة لا تعني صحة الحل."));
  if(report.stop_reason!=="completed")host.append(p("القياس غير مكتمل: "+report.stop_reason));
  return host;
 }
 return {execution,performance};
})();
