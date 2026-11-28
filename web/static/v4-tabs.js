/* Guided workspace tabs. Navigation is local and never invokes the engine.
 * Existing input, result, repair, and report nodes are moved, not cloned.
 */
window.AlgoXRayTabs=(()=>{
 "use strict";
 const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n};
 const add=(p,...children)=>{p.append(...children.filter(Boolean));return p};
 const button=(title,fn)=>{const b=el("button","",title);b.type="button";b.onclick=fn;return b};
 const primaryOps=new Set(["analysis","observe","profile","benchmark","codeforces_samples"]);
 const verdict={
  observed_mismatch:"وجدنا حالة فشل",no_witness_found:"لم نجد خطأ في الحالات المجربة",
  manual_observation:"سجلنا تنفيذ البرنامج",profiled_execution:"سجلنا تنفيذ حالة واحدة",
  benchmark_observation:"سجلنا قياسات الزمن",cancelled:"أُلغي التشغيل",
  oracle_unavailable:"تعذر الحكم بالمرجع",inconclusive:"النتيجة غير حاسمة",
  unstable:"تعذر تثبيت الشاهد",not_passed_or_inconclusive:"لم يكتمل التحقق"
 };
 function mount(o){
  const {main,intro,workspace,toolsPanel,results,fullPanel,fullProgress,cancel,benchPanel,benchDetails,advancedResult,reports,fullExport,footer}=o;
  const host=el("div","ux-tab-workspace");host.id="ux-tab-workspace";
  const anchor=el("div","ux-tab-anchor");anchor.id="ux-tab-anchor";
  const sticky=el("div","ux-tab-sticky"),nav=el("div","ux-tab-list");
  nav.id="ux-tab-list";nav.setAttribute("role","tablist");nav.setAttribute("aria-label","مساحة العمل");
  const progress=el("div","ux-tab-progress");progress.id="ux-tab-progress";
  const otherProgress=el("p","ux-description","جارٍ تنفيذ الطلب…");otherProgress.setAttribute("role","status");
  add(progress,fullProgress,otherProgress,cancel);add(sticky,nav,progress);add(host,anchor,sticky);
  const tabs={},panels={};
  const names=[["input","الإدخال"],["summary","الملخص"],["execution","التنفيذ"],["fault","مكان الخطأ"],["performance","الأداء"],["advanced","متقدم"]];
  for(const [id,title] of names){
   const b=button(title,()=>select(id,true));b.className="ux-tab";b.id="ux-tab-"+id;b.dataset.tab=id;
   b.setAttribute("role","tab");b.setAttribute("aria-controls","ux-tab-panel-"+id);
   b.setAttribute("aria-selected","false");b.tabIndex=-1;
   const panel=el("section","ux-tab-panel");panel.id="ux-tab-panel-"+id;
   panel.setAttribute("role","tabpanel");panel.setAttribute("aria-labelledby",b.id);
   panel.hidden=true;tabs[id]=b;panels[id]=panel;nav.append(b);host.append(panel);
  }
  const single=el("section","panel ux-single-summary");single.id="ux-tab-single-summary";
  const singleHeading=el("h2","","نتيجة التنفيذ"),singleVerdict=el("strong","ux-single-verdict"),singleScope=el("p","ux-description");
  add(single,singleHeading,singleVerdict,singleScope);
  const quick=el("div","ux-summary-links");quick.id="ux-summary-links";
  const qTrace=button("شاهد التنفيذ",()=>select("execution",true)),qFault=button("راجع مكان الخطأ",()=>select("fault",true)),
   qShrink=button("شاهد تصغير الحالة",()=>{select("fault",true);document.getElementById("story-shrink")?.scrollIntoView({block:"start"})}),
   qPerf=button("شاهد الأداء",()=>select("performance",true)),qAdvanced=button("التفاصيل المتقدمة",()=>select("advanced",true));
  qTrace.id="ux-summary-trace";qFault.id="ux-summary-fault";qShrink.id="ux-summary-shrink";qPerf.id="ux-summary-performance";
  add(quick,qTrace,qFault,qShrink,qPerf,qAdvanced);
  const settingsLink=button("إعدادات وأدوات إضافية",()=>{select("advanced",true);document.getElementById("ux-tools").open=true});
  settingsLink.className="ux-tab-settings-link";settingsLink.id="ux-tab-settings-link";
  const execSlot=el("div","ux-tab-story-slot"),faultSlot=el("div","ux-tab-story-slot"),hotSlot=el("div","ux-tab-story-slot");
  const emptyExec=add(el("section","panel ux-tab-empty"),el("h2","","التنفيذ"),el("p","","لا يوجد تتبع مسجل لهذا الطلب."));
  const emptyFault=add(el("section","panel ux-tab-empty"),el("h2","","مكان الخطأ"),el("p",""));
  const emptyPerf=add(el("section","panel ux-tab-empty"),el("h2","","الأداء"),el("p","","لا توجد قياسات متاحة لهذا الطلب. يمكن قياس الأداء من الأدوات الإضافية."));
  const exportPanel=add(el("section","panel"),el("h2","","التقرير الشامل"),el("p","ux-description","يتضمن التقرير الكود والمدخلات والمخرجات. شاركه فقط إذا رغبت بذلك."),fullExport);
  const techPanel=add(el("section","panel ux-tab-tech"),el("h2","","أدلة التنفيذ"),advancedResult);
  const benchTech=add(el("section","panel ux-tab-tech"),el("h2","","أدلة القياس"),benchDetails);
  add(panels.input,intro,workspace,settingsLink);
  add(panels.summary,results,single,quick,fullPanel);
  add(panels.execution,execSlot,emptyExec);
  add(panels.fault,faultSlot,emptyFault);
  add(panels.performance,benchPanel,hotSlot,emptyPerf);
  add(panels.advanced,toolsPanel,techPanel,benchTech,reports,exportPanel);
  main.insertBefore(host,footer);
  let active="input",story=null,record=null;
  let previousBusy=false,autoPending=false;
  function stopPlayback(){story?.stopPlayback?.();o.stopTechnicalPlayback?.()}
  function goTop(){anchor.scrollIntoView({block:"start",behavior:"instant"})}
  function select(id,navigate=false){
   if(!tabs[id]||tabs[id].hidden)return false;
   if(active!==id)stopPlayback();
   active=id;
   for(const [key] of names){
    const selected=key===id;tabs[key].setAttribute("aria-selected",String(selected));
    tabs[key].tabIndex=selected?0:-1;panels[key].hidden=!selected;
   }
   if(navigate){
    goTop();tabs[id].focus({preventScroll:true});
    tabs[id].scrollIntoView({block:"nearest",inline:"nearest"});
   }
   refreshProgress();
   return true;
  }
  nav.addEventListener("keydown",e=>{
   const focused=e.target.closest("[role=tab]");if(!focused)return;
   const available=names.map(([id])=>id).filter(id=>!tabs[id].hidden);let i=available.indexOf(focused.dataset.tab);
   const rtl=getComputedStyle(nav).direction==="rtl";
   if(e.key==="ArrowRight")i=(i+(rtl?-1:1)+available.length)%available.length;
   else if(e.key==="ArrowLeft")i=(i+(rtl?1:-1)+available.length)%available.length;
   else if(e.key==="Home")i=0;else if(e.key==="End")i=available.length-1;else return;
   e.preventDefault();select(available[i],true);
  });
  function refreshProgress(){
   const s=o.state();
   const showFull=!fullPanel.hidden&&(s.busy||active==="summary"||(active==="input"&&!hasResults(s)));
   fullProgress.hidden=!showFull;otherProgress.hidden=!s.busy||s.fullActive;
   progress.hidden=fullProgress.hidden&&otherProgress.hidden&&cancel.hidden;
  }
  function hasResults(s){
   return !results.hidden||!benchPanel.hidden||Boolean(s.fullReport?.phases?.length)||
     Boolean(record&&primaryOps.has(record.run_report?.operation)&&!s.reportHidden);
  }
  function clearStory(){
   story?.stopPlayback?.();story=null;execSlot.replaceChildren();faultSlot.replaceChildren();hotSlot.replaceChildren();
  }
  function installStory(root){
   clearStory();story=root;
   for(const [id,slot] of [["story-timeline",execSlot],["story-findings",faultSlot],["story-shrink",faultSlot],["story-hotspots",hotSlot]]){
    const n=root.querySelector("#"+id);if(n)slot.append(n);
   }
   refresh();
  }
  function noteReport(data){
   if(primaryOps.has(data.run_report?.operation)){
    record=data;autoPending=true;
   }
   refresh();
  }
  function refresh(){
   const s=o.state(),has=hasResults(s);
   // A report panel hidden by invalidation must not keep obsolete navigation alive.
   if(s.reportHidden&&!s.busy&&results.hidden&&benchPanel.hidden&&!s.fullReport?.phases?.length)record=null;
   if(results.hidden&&story)clearStory();
   for(const [id] of names)tabs[id].hidden=id!=="input"&&id!=="advanced"&&!has;
   const traceAvailable=!results.hidden&&execSlot.childElementCount>0;
   const faultAvailable=!results.hidden&&faultSlot.childElementCount>0;
   const hotAvailable=!results.hidden&&hotSlot.childElementCount>0;
   const measured=!benchPanel.hidden;
   const fault=s.result?.status==="observed_mismatch"||s.result?.sample_attention;
   tabs.fault.classList.toggle("ux-tab-alert",Boolean(fault&&has));
   tabs.fault.setAttribute("aria-label",fault?"مكان الخطأ، توجد ملاحظة تحتاج مراجعة":"مكان الخطأ");
   emptyExec.hidden=traceAvailable;emptyFault.hidden=faultAvailable;emptyPerf.hidden=hotAvailable||measured;
   emptyFault.querySelector("p").textContent=record?.status==="no_witness_found"||s.fullReport?.phases?.[0]?.data?.status==="no_witness_found"?
    "لم نجد حالة فشل في المدخلات المجربة؛ هذا لا يثبت صحة الحل لكل الحالات.":
    "لا توجد حالة فشل مؤكدة يمكن عرض موضعها في هذا الطلب.";
   techPanel.hidden=results.hidden;benchTech.hidden=!measured;exportPanel.hidden=fullExport.hidden;
   single.hidden=!has||Boolean(s.fullReport?.phases?.length)||!record;
   if(!single.hidden){singleVerdict.textContent=verdict[record.status]||"نتيجة مسجلة";singleScope.textContent=record.status==="no_witness_found"?
      "هذا الحكم يخص الحالات المجربة فقط.":record.status==="profiled_execution"?"هذا تنفيذ واحد، لا حكم عام على الصحة.":"راجع الأدلة المتاحة لهذا الطلب."}
   qTrace.hidden=!execSlot.querySelector("#story-slider");qFault.hidden=!faultAvailable;qShrink.hidden=!faultSlot.querySelector("#story-shrink-bars");
   qPerf.hidden=!(hotAvailable||measured);quick.hidden=!has;
   if(!has&&active!=="input"&&active!=="advanced")select("input",false);
   if(previousBusy&&!s.busy&&autoPending&&has){autoPending=false;select("summary",true)}
   if(!s.busy&&!has)autoPending=false;
   previousBusy=s.busy;
   refreshProgress();
  }
  // Attribute changes made by the original handlers (including old listeners)
  // are authoritative for invalidation and terminal/partial results.
  const observer=new MutationObserver(refresh);
  for(const target of [results,benchPanel,fullPanel,fullExport,cancel,document.getElementById("run-report-panel")])observer.observe(target,{attributes:true,attributeFilter:["hidden"]});
  select("input",false);refresh();
  return {select,refresh,installStory,noteReport,clearStory,stopPlayback};
 }
 return {mount};
})();
