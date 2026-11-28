/* AlgoXRay teaching projections. Pure local rendering; no execution or provider calls.
 * Snapshots are observations, not object identities, causal proofs or reconstructed heap.
 */
window.AlgoXRayLearning=(()=>{
 "use strict";
 const el=(tag,cls,t)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(t!==undefined)n.textContent=String(t);return n};
 const add=(n,...items)=>{n.append(...items.filter(Boolean));return n};
 const p=t=>el("p","learning-note",t);
 const mono=(tag,t)=>{const n=el(tag,"learning-mono",t);n.dir="ltr";return n};
 const btn=(title,action)=>{const n=el("button","learning-button",title);n.type="button";n.onclick=action;return n};
 const own=(o,k)=>Object.prototype.hasOwnProperty.call(o||{},k);
 // JSON numbers above JS safe integer precision may already have been rounded.
 const numeric=v=>typeof v==="number"&&Number.isFinite(v)&&(!Number.isInteger(v)||Number.isSafeInteger(v));
 const scalar=v=>v===null||typeof v==="boolean"||typeof v==="string"||numeric(v);
 const value=v=>v===undefined||v?.unavailable?"غير مسجل":v===null?"None":typeof v==="boolean"?(v?"True":"False"):typeof v==="string"?JSON.stringify(v):typeof v==="number"&&!numeric(v)?"عدد خارج دقة العرض":typeof v==="object"?JSON.stringify(v):String(v);
 const same=(a,b)=>scalar(a)&&scalar(b)&&Object.is(a,b);
 const array=v=>Array.isArray(v)?v:v&&["list","tuple"].includes(v.kind)&&Array.isArray(v.items)?v.items:null;
 const completeArray=v=>Array.isArray(v)||(v&&["list","tuple"].includes(v.kind)&&!v.truncated&&Array.isArray(v.items)&&v.size===v.items.length);
 const safeTree=v=>scalar(v)||(Array.isArray(v)&&v.every(safeTree));
 const changed=(a,b)=>safeTree(a)&&safeTree(b)&&JSON.stringify(a)!==JSON.stringify(b);
 // Describe only differences between comparable, fully recorded positions.
 function cellDiffs(old,now,prefix,limit=3){
  const out=[];
  function visit(a,b,path){
   if(out.length>=limit)return;
   if(scalar(a)&&scalar(b)){if(!same(a,b))out.push(path+": "+value(a)+" → "+value(b));return}
   if(!Array.isArray(a)||!Array.isArray(b)||a.length!==b.length)return;
   for(let i=0;i<a.length&&out.length<limit;i++)visit(a[i],b[i],path+"["+i+"]");
  }
  visit(old,now,prefix);return out;
 }
 function tableValue(v,old){
  const a=array(v),prior=array(old);
  const matrix=a&&a.length>0&&a.length<=24&&a.every(r=>Array.isArray(r)&&r.length>0&&r.length<=24&&r.every(x=>scalar(x)||x?.unavailable));
  if(matrix){
   const width=Math.max(...a.map(r=>r.length)),h=el("div","learning-matrix-wrap");
   const tbl=el("table","learning-matrix");tbl.dir="ltr";tbl.setAttribute("aria-label","جدول القيم المسجلة");
   const head=el("tr");add(head,el("th","","i/j"));for(let j=0;j<width;j++){const th=el("th","",j);th.scope="col";head.append(th)}
   tbl.append(add(el("thead"),head));
   const body=el("tbody");
   a.forEach((row,i)=>{const tr=el("tr"),th=el("th","",i);th.scope="row";tr.append(th);
    for(let j=0;j<width;j++){
     const exists=j<row.length,cur=row[j],before=prior?.[i]?.[j];
     const cell=el("td","",exists?value(cur):"—");cell.dataset.row=String(i);cell.dataset.col=String(j);
     if(exists&&scalar(before)&&scalar(cur)&&!same(before,cur)){cell.classList.add("learning-cell-changed");cell.title=value(before)+" → "+value(cur)}
     tr.append(cell);
    }body.append(tr)
   });
   tbl.append(body);add(h,tbl,p(v?.truncated?"جدول جزئي: يعرض الصفوف المسجلة فقط.":"صفوف وأعمدة اللقطة المسجلة؛ التلوين يوضح الخلايا التي اختلفت عن اللقطة السابقة المتاحة."));
   return h;
  }
  if(v?.kind==="dict"&&Array.isArray(v.entries)){
   const wrap=el("div","learning-dict"),rows=el("div","learning-dict-rows");
   for(const e of v.entries.slice(0,24)){
    if(!e||!own(e,"key")||!own(e,"value"))continue;
    add(rows,add(el("div","learning-dict-row"),mono("span",value(e.key)),el("span","","→"),mono("strong",value(e.value))));
   }
   return add(wrap,rows,p((v.truncated?"جزء من القاموس: ":"مفاتيح وقيم مسجلة: ")+v.size));
  }
  if(v?.kind==="set"&&Array.isArray(v.items)){
   const wrap=el("div","learning-set");wrap.dir="ltr";
   for(const item of v.items.slice(0,24))wrap.append(mono("span",value(item)));
   return add(el("div","learning-set-wrap"),wrap,p("مجموعة عناصر؛ ترتيب العرض ليس ترتيب التنفيذ."+(v.truncated?" اللقطة جزئية.":"")));
  }
  return null;
 }
 function numericBars(v,old){
  const a=array(v),b=array(old);
  if(!a||!a.length||a.length>24||!a.every(numeric))return null;
  // Common zero baseline; negative bars extend left. Magnitudes use same scale per snapshot pair.
  const validOld=b?.every(numeric)?b:[];
  const max=Math.max(1,...a.map(Math.abs),...validOld.map(Math.abs));
  const wrap=el("div","learning-number-bars");wrap.dir="ltr";wrap.setAttribute("aria-label","القيم العددية في اللقطة");
  a.forEach((n,i)=>{
   const fill=el("span","learning-number-fill");fill.style.width=(Math.abs(n)/max*50)+"%";fill.style.left=(n<0?50-Math.abs(n)/max*50:50)+"%";
   if(scalar(b?.[i])&&!same(n,b[i]))fill.classList.add("learning-cell-changed");
   const row=add(el("div","learning-number-row"),el("span","",i),add(el("div","learning-number-track"),fill),mono("strong",value(n)));row.dataset.index=String(i);wrap.append(row)
  });
  const outer=add(el("div","learning-array-chart"),wrap,p(v?.truncated?"قيم الجزء المسجل فقط. محور الصفر في المنتصف.":"محور الصفر في المنتصف؛ الأطوال تمثل القيم بنفس مقياس هذه المقارنة."));
  // A changed position is not proof of a swap, especially with duplicate values.
  if(completeArray(v)&&completeArray(old)&&b&&b.length===a.length&&b.every(numeric)&&new Set(a).size===a.length&&new Set(b).size===b.length&&a.every(x=>b.includes(x))){
   const movements=a.map((x,i)=>({x,from:b.indexOf(x),to:i})).filter(x=>x.from!==x.to);
   if(movements.length){
    const map=el("div","learning-reorder");
    for(const m of movements.slice(0,12)){
     const row=add(el("div","learning-movement"),mono("strong",value(m.x)),mono("span",String(m.from)+" → "+m.to));row.dataset.from=String(m.from);row.dataset.to=String(m.to);map.append(row)
    }
    add(outer,el("strong","learning-small-title","تغيّر مواضع القيم"),map,p("نفس القيم الفريدة في لقطتين بمواضع مختلفة. الأسهم تقارن المواضع فقط، ولا تثبت طريقة الفرز أو حدوث swap بعينه."));
   }
  }
  return outer;
 }
 function build(report,events,lines,jump){
  const host=el("div","learning-inspector");host.id="learning-inspector";
  const explain=el("div","learning-explain");explain.id="learning-explain";
  const relation=el("div","learning-relations");relation.id="learning-relations";
  const tree=el("div","learning-frames");tree.id="learning-frames";
  const context=el("div","learning-source");context.id="learning-source";
  const predict=el("details","learning-predict");predict.id="learning-predict";predict.append(el("summary","","جرّب توقع الخطوة التالية"));
  const question=el("div","learning-question");predict.append(question);
  const graph=report.student_graph||{},rels=graph.relations||{};
  const indexById=new Map(events.map((e,i)=>[e.event_id,i]));
  const go=id=>{const i=indexById.get(id);if(i!==undefined)jump(i)};
  const marks=events.map((e,i)=>{
   const prev=events.slice(0,i).reverse().find(x=>x.frame_id===e.frame_id);
   return i===0||["call","return","exception"].includes(e.kind)||Object.keys(e.locals||{}).some(k=>!own(prev?.locals,k)||changed(prev.locals[k],e.locals[k]));
  });
  const keyNav=el("div","learning-key-nav");
  let pos=0;
  const back=btn("التغيّر السابق",()=>{for(let i=pos-1;i>=0;i--)if(marks[i]){jump(i);break}}),forward=btn("التغيّر التالي",()=>{for(let i=pos+1;i<events.length;i++)if(marks[i]){jump(i);break}});
  back.id="learning-prev-change";forward.id="learning-next-change";
  add(keyNav,back,el("span","learning-note","انتقل إلى لقطة فيها قيمة جديدة أو تغيّر مدعوم أو حدث دالة."),forward);
  add(host,explain,relation,context,tree,predict,keyNav);
  function render(i){
   pos=i;const e=events[i],previous=events.slice(0,i).reverse().find(x=>x.frame_id===e.frame_id),cur=e.locals||{},prior=previous?.locals||{};
   explain.replaceChildren();
   const title=e.kind==="call"?"دخول إطار تنفيذ":e.kind==="return"?"حدث عودة من الإطار":e.kind==="exception"?"رُصد استثناء":"قبل تنفيذ السطر "+e.line;
   const what=el("strong","",title);what.id="learning-step-title";explain.append(what);
   const diffs=Object.keys(cur).filter(k=>own(prior,k)&&changed(prior[k],cur[k]));
   const added=Object.keys(cur).filter(k=>!own(prior,k)&&scalar(cur[k]));
   const items=el("div","learning-changes");items.id="learning-changes";
   for(const k of diffs.slice(0,4)){
    const row=el("div","learning-change");row.dataset.name=k;
    const old=prior[k],now=cur[k];
    if(scalar(old)&&scalar(now))add(row,mono("strong",k),mono("span",value(old)+" → "+value(now)));
    else{
     const cells=cellDiffs(old,now,k);
     add(row,mono("strong",k),cells.length?mono("span",cells.join(" · ")):el("span","","تغيّرت القيم المسجلة"));
    }
    items.append(row)
   }
   for(const k of added.slice(0,Math.max(0,4-diffs.length))){
    const row=add(el("div","learning-change"),mono("strong",k),mono("span",value(cur[k])));row.dataset.name=k;items.append(row)
   }
   if(items.children.length)add(explain,p(previous?"مقارنة مع اللقطة "+previous.event_id+" في الإطار نفسه. قد تكون هناك خطوات بينهما.":"قيم مسجلة عند دخول الإطار."),items);
   else explain.append(p(previous?"لا يظهر اختلاف قابل للمقارنة في القيم المعروضة. قد تكون هناك قيم غير مسجلة.":"هذه أول لقطة مسجلة لهذا الإطار."));
   if(e.kind==="return")explain.append(p("السجل الحالي لا يحتوي قيمة return نفسها؛ لا نستنتجها من المتغيرات المحلية."));
   if(e.kind==="exception"&&e.exception_type)explain.append(p("نوع الاستثناء المسجل: "+e.exception_type+". قد يعالجه البرنامج لاحقاً."));
   if(previous){
    if(items.children.length&&previous.line>0&&previous.line<=lines.length){
     const context=add(el("div","learning-previous-source"),p("السطر عند اللقطة السابقة (قبل تنفيذه إذا كانت من نوع line):"),mono("code","L"+previous.line+"  "+lines[previous.line-1]));
     explain.append(context);
    }
    explain.append(btn("شاهد اللقطة السابقة في هذا الإطار",()=>go(previous.event_id)));
   }
   // Only relations already recomputed and corroborated by the engine are shown.
   relation.replaceChildren();relation.hidden=true;
   const writes=(rels.data||[]).filter(r=>r.after_event_id===e.event_id&&r.frame_id===e.frame_id&&indexById.has(r.before_event_id)&&scalar(r.write?.value)&&Object.values(r.reads||{}).every(scalar));
   const controls=(rels.control||[]).filter(r=>r.after_event_id===e.event_id&&r.frame_id===e.frame_id&&indexById.has(r.before_event_id));
   const branches=(graph.branches?.observed||[]).filter(r=>r.event_pairs?.some(pair=>pair[1]===e.event_id&&indexById.has(pair[0])));
   if(writes.length||controls.length||branches.length){
    relation.hidden=false;relation.append(el("strong","","كيف يرتبط هذا التغيّر بالكود؟"));
    for(const r of writes.slice(0,3)){
     const reads=el("div","learning-flow-reads");for(const [k,v] of Object.entries(r.reads||{}))reads.append(add(el("div","learning-flow-value"),mono("span",k),mono("strong",value(v))));
     const flow=add(el("div","learning-flow"),reads,el("span","learning-flow-arrow","→"),add(el("div","learning-flow-value learning-flow-result"),mono("span",r.write.name),mono("strong",value(r.write.value))));flow.dataset.event=e.event_id;
     add(relation,flow,p("حساب بسيط متوافق مع اللقطتين "+r.before_event_id+" و"+e.event_id+" عند السطر "+r.line+"؛ ليس إثباتاً لكل الاعتماديات."),btn("شاهد سطر الحساب",()=>go(r.before_event_id)));
    }
    for(const r of controls.slice(0,2))add(relation,p("إعادة حساب شرط السطر "+r.line+" أعطت "+(r.condition?"True":"False")+"، والانتقال إلى السطر "+r.target_line+" رُصد فعلياً."),btn("شاهد الشرط",()=>go(r.before_event_id)));
    const label={condition_true:"فرع الشرط الصحيح",condition_false:"فرع الشرط الخاطئ",loop_body:"دخول جسم الحلقة",loop_exit:"خروج من الحلقة"};
    for(const r of branches.slice(0,2))relation.append(p((label[r.kind]||"انتقال تحكم")+" · L"+r.line+" → L"+r.target_line+" (مطابقة انتقال مسجل في CFG محدود)."));
   }
   context.replaceChildren();
   const code=el("div","learning-code");code.dir="ltr";
   if(e.line>0&&e.line<=lines.length){
    for(let l=Math.max(1,e.line-3);l<=Math.min(lines.length,e.line+3);l++){
     const row=add(el("div","learning-code-row"),el("span","",l),mono("code",lines[l-1]||" "));row.dataset.line=String(l);
     if(l===e.line){row.classList.add("learning-code-current");row.setAttribute("aria-current","step")}
     code.append(row)
    }
    add(context,el("strong","learning-small-title","السطر ضمن سياق الكود"),code)
   }
   // Frame genealogy observed up to the selected event, not an assumed live stack.
   tree.replaceChildren();
   const frames=new Map();
   for(const ev of events.slice(0,i+1)){
    if(!frames.has(ev.frame_id))frames.set(ev.frame_id,{id:ev.frame_id,parent:ev.parent_frame_id,fn:ev.function,first:ev.event_id,last:ev});
    else frames.get(ev.frame_id).last=ev;
   }
   tree.hidden=frames.size<=1;
   if(!tree.hidden){
    const ancestors=new Set();let id=e.frame_id;while(frames.has(id)&&!ancestors.has(id)){ancestors.add(id);id=frames.get(id).parent}
    const picked=[...frames.values()].filter(f=>ancestors.has(f.id));
    for(const f of frames.values())if(!ancestors.has(f.id)&&picked.length<32)picked.push(f);
    const ids=new Set(picked.map(f=>f.id)),visited=new Set();
    const list=el("ul","learning-tree");list.dir="ltr";
    function draw(f,parent,depth){
     if(visited.has(f.id)||depth>32)return;visited.add(f.id);
     const row=el("li","learning-tree-node");row.dataset.frame=f.id;
     if(f.parent&&ids.has(f.parent))row.dataset.parent=f.parent;
     const b=btn((f.fn==="<module>"?"main":f.fn||"frame")+" · "+f.id,()=>go(f.last.event_id));b.dir="ltr";
     if(f.id===e.frame_id){b.setAttribute("aria-current","step");b.classList.add("learning-frame-current")}
     const status=el("small","",f.last.kind==="return"?"حدث عودة":f.id===e.frame_id?"اللقطة الحالية":"إطار مرصود");
     const vals=Object.entries(f.last.locals||{}).filter(([k,v])=>scalar(v)).slice(0,3);
     const preview=el("div","learning-frame-values");
     for(const [k,v] of vals)preview.append(mono("span",k+" = "+value(v)));
     if(vals.length)preview.setAttribute("aria-label","قيم من آخر لقطة لهذا الإطار");
     add(row,b,status,vals.length?preview:null);parent.append(row);
     const kids=picked.filter(k=>k.parent===f.id&&!visited.has(k.id));
     if(kids.length){const sub=el("ul","learning-tree");row.append(sub);for(const k of kids)draw(k,sub,depth+1)}
    }
    for(const f of picked.filter(f=>!ids.has(f.parent)))draw(f,list,0);
    for(const f of picked)if(!visited.has(f.id))draw(f,list,0);
    add(tree,el("strong","","شجرة إطارات الاستدعاء المرصودة"),list,p("كل إطار يعرض بعض قيم آخر لقطة له. العلاقات مرصودة حتى الخطوة الحالية، وليست مكدساً حياً أو قيم عودة. اضغط إطاراً للرجوع إلى لقطته."));
    if(frames.size>picked.length)tree.append(p("بعض الإطارات غير معروضة؛ تم الاحتفاظ بإطارات السلسلة الحالية."));
   }
   question.replaceChildren();predict.open=false;predict.hidden=true;
   const next=events[i+1];
   if(e.kind==="line"&&next?.kind==="line"&&next.frame_id===e.frame_id){
    const k=Object.keys(cur).find(k=>own(next.locals,k)&&scalar(cur[k])&&scalar(next.locals[k])&&!same(cur[k],next.locals[k]));
    if(k){
     predict.hidden=false;question.dataset.variable=k;
     add(question,p("في اللقطة التالية المسجلة في الإطار نفسه، ما قيمة "+k+"؟"),p("هذا سؤال عن سجل التنفيذ، وليس تنفيذاً جديداً."));
     const feedback=el("p","learning-note");feedback.id="learning-feedback";feedback.setAttribute("role","status");
     const answers=el("div","learning-answer-options");
     const options=i%2?[next.locals[k],cur[k]]:[cur[k],next.locals[k]];
     for(const option of options){
      const b=btn(value(option),()=>{
       feedback.textContent=same(option,next.locals[k])?"مطابق للقيمة المسجلة.":"القيمة المسجلة هي "+value(next.locals[k])+". راجع اللقطة التالية.";
       for(const child of answers.children)child.disabled=true;
      });b.dataset.value=value(option);answers.append(b)
     }
     add(question,answers,feedback,btn("شاهد اللقطة التالية",()=>jump(i+1)));
    }
   }
   back.disabled=!marks.slice(0,i).some(Boolean);forward.disabled=!marks.slice(i+1).some(Boolean);
  }
  return {host,render};
 }
 function growth(report){
  const points=(report.points||[]).filter(q=>Number.isFinite(q.size)).slice().sort((a,b)=>a.size-b.size);
  if(points.length<2||new Set(points.map(q=>q.size)).size!==points.length)return null;
  const stats=q=>q.summary?.wall_ns;
  const usable=q=>q.summary?.completed===q.summary?.requested&&q.summary?.completed>0&&["min","median","max"].every(k=>Number.isFinite(stats(q)?.[k])&&stats(q)[k]>=0);
  const valid=points.filter(usable);if(!valid.length)return null;
  const ns="http://www.w3.org/2000/svg",svg=(tag,attrs,text)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n};
  const W=640,H=245,L=78,R=20,T=18,B=44,max=Math.max(1,...valid.map(q=>stats(q).max));
  const lo=points[0].size,hi=points.at(-1).size,x=n=>L+(n-lo)/(hi-lo)*(W-L-R),y=n=>T+(1-n/max)*(H-T-B);
  const canvas=svg("svg",{viewBox:"0 0 "+W+" "+H,role:"img","aria-label":"منحنى وسيط زمن التنفيذ حسب حجم المدخل مع نطاق أقل وأعلى قياس"});canvas.classList.add("learning-growth-svg");
  for(let i=0;i<=4;i++){const n=max*i/4;canvas.append(svg("line",{x1:L,x2:W-R,y1:y(n),y2:y(n),stroke:"#d9e1eb"}),svg("text",{x:L-8,y:y(n)+4,"text-anchor":"end","font-size":11},(n/1e6).toPrecision(3)))}
  canvas.append(svg("text",{x:12,y:12,"font-size":11},"ms"));
  for(const [i,q] of points.entries()){
   const px=x(q.size);canvas.append(svg("text",{x:px,y:H-16,"text-anchor":"middle","font-size":11},String(q.size)));
   if(!usable(q)){canvas.append(svg("text",{x:px,y:H-B-5,"text-anchor":"middle","font-size":10,fill:"#a15b0c"},"—"));continue}
   const s=stats(q),prev=points[i-1];
   if(prev&&usable(prev))canvas.append(svg("line",{x1:x(prev.size),y1:y(stats(prev).median),x2:px,y2:y(s.median),stroke:"#3158c8","stroke-width":2.5}));
   const group=svg("g",{"data-size":q.size});
   group.append(svg("title",{},String(q.size)+" · "+(s.median/1e6).toPrecision(4)+" ms"),svg("line",{x1:px,x2:px,y1:y(s.min),y2:y(s.max),stroke:"#8196c5","stroke-width":4}),svg("circle",{cx:px,cy:y(s.median),r:5,fill:q.correctness==="recorded_mismatch"?"#b42335":"#3158c8"}));canvas.append(group)
  }
  const host=add(el("div","learning-growth"),el("strong","","منحنى النمو المرصود"),canvas,p("حقل الحجم: "+(report.size_field||"size")+" · النقطة وسيط القياسات، والخط العمودي أقل/أعلى قياس. لا نصل النقاط عبر قياس ناقص، ولا نثبت فئة Big-O."));host.id="learning-growth";return host;
 }
 return {build,tableValue,numericBars,growth,scalar,changed,value};
})();
