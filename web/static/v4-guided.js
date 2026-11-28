/* Presentation layer for the guided AlgoXRay workspace.
 * The original controls, IDs, request handlers and owner-review rules are preserved.
 * ?view=expert leaves the full technical workspace intact.
 */
(function(){
 "use strict";
 const main=document.querySelector("main"),header=document.querySelector("header");
 const expert=new URLSearchParams(location.search).get("view")==="expert";
 const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text)e.textContent=text;return e};
 const append=(parent,...items)=>{for(const item of items)if(item)parent.append(item);return parent};
 const by=id=>document.getElementById(id);
 const label=id=>by(id).closest("label")||by(id);
 const field=id=>{const target=by(id),l=document.querySelector('label[for="'+id+'"]');return l?append(node("div","ux-field"),l,target):target};
 const heading=(section,n,title)=>{const h=section.querySelector("h2");h.textContent=title;const wrap=node("div","ux-heading");section.insertBefore(wrap,h);append(wrap,node("span","ux-step-number",n),h)};
 const desc=text=>node("p","ux-description",text);
 const disclosure=(title,id,items,open=false)=>{const d=node("details","ux-disclosure");d.id=id;d.open=open;const c=node("div","ux-disclosure-content");append(d,node("summary","",title),c);append(c,...items);return d};
 const link=node("a","",expert?"الواجهة المبسطة":"وضع الخبير");
 link.href=expert?"/v4":"/v4?view=expert";link.target="_blank";link.rel="noopener";link.title="فتح في تبويب جديد، مع إبقاء عملك الحالي";
 const headerActions=node("div","ux-header-actions");append(headerActions,header.querySelector("a"),link);header.append(headerActions);
 if(expert)return;
 document.body.classList.add("guided-workspace");
 header.querySelector("p").textContent="فهم الخوارزميات، بالأدلة.";
 const classic=headerActions.querySelector("a");classic.textContent="النسخة السابقة";classic.target="_blank";classic.rel="noopener";
 const problem=by("demo").closest(".panel"),codePanel=by("source").closest(".panel"),settings=by("health").closest(".status");
 const intro=append(node("div","ux-intro"),node("p","ux-eyebrow","مساحة عمل AlgoXRay"),node("h2","","افهم الكود. اكتشف الخطأ. حسّن الأداء."),desc("اختر هدفك، أضف برنامج Python، وشاهد ما يحدث فعلياً أثناء التنفيذ."));
 const modes=node("div","ux-modes");modes.setAttribute("role","group");modes.setAttribute("aria-label","هدف التحليل");
 let mode="diagnose";
 const modeButtons=[];
 for(const [id,n,title,detail] of [
  ["diagnose","01","تشخيص الخطأ","اعثر على حالة فشل صغيرة وافحص سببها المحتمل."],
  ["understand","02","فهم التنفيذ","شاهد خطوات الكود والقيم المتغيرة على مدخل تختاره."],
  ["performance","03","قياس الأداء","قس الزمن دون تتبع أو افحص نمو الزمن مع حجم المدخلات."]
 ]){
  const b=node("button","ux-mode");b.type="button";b.dataset.mode=id;b.setAttribute("aria-pressed",String(mode===id));
  append(b,node("span","ux-mode-index",n),node("strong","",title),node("small","",detail));modes.append(b);modeButtons.push(b);
 }
 main.prepend(intro,modes);
 const workspace=node("div","ux-workspace");modes.after(workspace);append(workspace,problem,codePanel);
 // Prepare the problem in a distinct section. Reviewing a reference remains explicit.
 const approved=label("packages");approved.classList.add("ux-field");
 const approval=by("approval"),reviewLabel=label("reviewed"),approve=by("approve"),audit=by("audit-reference");
 const demoToolbar=by("demo").closest(".toolbar"),importToolbar=by("problem-url").closest(".toolbar");
 const statementField=field("statement"),manualSamples=field("manual-samples");
 const statementKind=by("statement-kind").closest(".toolbar");
 const pkgField=field("package"),packagePreview=node("div","ux-package-preview");
 const packageJson=disclosure("تعديل العقد التقني JSON","ux-package-json",[pkgField]);
 const packageReview=disclosure("مراجعة المسألة والحل المرجعي","ux-package-review",[
  desc("قبل البحث عن الخطأ، راجع قيود المدخلات والحل المرجعي واختبارات مستقلة. مسودة الذكاء الاصطناعي لا تعد اعتماداً."),
  packagePreview,packageJson,reviewLabel,append(node("div","ux-actions"),approve,audit),by("reference-audit")
 ]);
 const newProblem=disclosure("إضافة مسألة جديدة","ux-new-problem",[
  desc("استورد مسألة من Codeforces أو اكتب نصها، ثم جهز قيودها وحلها المرجعي."),
  importToolbar,by("import-samples"),statementField,statementKind,manualSamples,by("intake-review"),
  append(node("div","ux-actions"),by("draft"),by("draft-reference")),by("draft-review")
 ]);
 // Keep all review controls reachable after loading or authoring a draft.
 const problemHint=desc("اختر مسألة معتمدة للبحث عن أخطاء الحل. يمكنك فهم التنفيذ أو قياسه دون مرجع.");
 const available=node("p","ux-description");available.id="ux-package-availability";
 const example=append(node("div","ux-example"),node("h3","","جرّب مثالاً جاهزاً"),desc("حمّل مثالاً بسيطاً للتجربة، ثم راجعه قبل اعتماد المرجع."),demoToolbar);
 const approvalMessage=node("p","ux-status-message");approvalMessage.hidden=true;
 const approvalDetails=disclosure("تفاصيل فحص المسألة","ux-approval-details",[approval]);approvalDetails.hidden=true;
 const ph=problem.querySelector("h2");problem.replaceChildren(ph,problemHint,approved,available,example,newProblem,packageReview,approvalMessage,approvalDetails);
 function syncApproval(){
  const raw=approval.textContent.trim();let state;
  try{state=JSON.parse(raw)}catch(e){}
  approvalDetails.hidden=!(state&&typeof state.passed==="boolean");
  approvalMessage.hidden=!raw;
  if(state&&typeof state.passed==="boolean"){
   approvalMessage.textContent=state.passed?"نجحت فحوص المرجع المستقلة وتم اعتماد المسألة.":"لم تنجح فحوص المسألة. راجع التفاصيل وعدّل المرجع أو الاختبارات.";
   approvalMessage.dataset.tone=state.passed?"positive":"warning";
  }else{
   approvalMessage.textContent=raw;approvalMessage.dataset.tone="neutral";
  }
 }
 new MutationObserver(syncApproval).observe(approval,{childList:true,subtree:true,characterData:true});
 syncApproval();
 by("demo").value="sum";
 heading(problem,"1","المسألة");
 approved.firstChild.textContent="المسألة المعتمدة ";
 approve.textContent="فحص واعتماد المسألة";approve.classList.add("ux-primary");
 by("load").textContent="تحميل المثال";by("correct").textContent="حل صحيح";by("mutant").textContent="حل فيه خطأ";
 by("draft").textContent="اقتراح قيود المسألة";by("draft-reference").textContent="اقتراح حل مرجعي";
 for(const id of ["load","draft","draft-reference"]){by(id).addEventListener("click",()=>{packageReview.open=true})}
 function renderPackagePreview(){
  packagePreview.replaceChildren();
  let p;
  try{p=JSON.parse(by("package").value)}catch(e){packagePreview.append(desc("لا توجد مسودة صالحة للعرض؛ افتح محرر العقد لمراجعتها."));return}
  if(!p||typeof p!=="object"){packagePreview.append(desc("مسودة غير صالحة."));return}
  const m=p.manifest||{};
  append(packagePreview,node("h3","",String(m.title||"مسودة المسألة")),desc(String(m.statement||"")));
  const fields=node("div","ux-constraints");
  for(const f of (Array.isArray(m.fields)?m.fields:[])){
   if(!f||typeof f!=="object")continue;
   const limits=(f.min!==undefined||f.max!==undefined)?String(f.min??"?")+" .. "+String(f.max??"?"):"";
   append(fields,append(node("div","ux-constraint"),node("strong","",String(f.name??"")),node("span","",String(f.kind??"")+" "+limits+(f.length_from?" · "+f.length_from:""))));
  }
  packagePreview.append(fields);
  const ref=node("pre","",typeof p.reference==="string"&&p.reference?p.reference:"لم يتم إعداد حل مرجعي بعد.");
  packagePreview.append(disclosure("معاينة الحل المرجعي","ux-preview-reference",[ref]));
  const controls=node("div","ux-control-preview");
  for(const c of (Array.isArray(p.controls)?p.controls:[])){
   if(!c||typeof c!=="object")continue;
   append(controls,append(node("div","ux-control-row"),node("pre","",JSON.stringify(c.case??null)),node("pre","",String(c.expected??""))));
  }
  if(!controls.children.length)controls.append(desc("أضف اختبارات مستقلة ونتائجها المتوقعة في محرر العقد قبل الاعتماد."));
  packagePreview.append(disclosure("الاختبارات المستقلة ("+controls.querySelectorAll(".ux-control-row").length+")","ux-preview-controls",[controls]));
  if(p.checker)packagePreview.append(desc("تستخدم المسألة حكماً دلالياً؛ راجع قاعدته في العقد التقني."));
  packagePreview.append(desc("المعاينة مختصرة. افتح العقد التقني لمراجعة جميع القيود والتعديل؛ التأكيد أدناه يتطلب مراجعة كاملة."));
 }
 by("package").addEventListener("input",()=>{by("reviewed").checked=false;renderPackagePreview()});
 new MutationObserver(renderPackagePreview).observe(approval,{childList:true,subtree:true});
 renderPackagePreview();
 function updateAvailable(){
  const count=by("packages").options.length;
  available.textContent=count?"المسائل المعتمدة متاحة للاختبار.":"لا توجد مسألة معتمدة بعد. أضف مسألة أو راجع مثالاً.";
  approved.hidden=!count
 }
 new MutationObserver(updateAvailable).observe(by("packages"),{childList:true});
 // Core code editor and task-specific controls. No request is sent by mode selection.
 const source=by("source"),trusted=label("trusted"),status=by("status"),run=by("run"),cancel=by("cancel");
 const advanced=disclosure("خيارات البحث المتقدمة","ux-analysis-options",[
  label("generator"),label("guided"),label("spectrum"),label("count"),label("reduce-count"),label("session-seconds"),field("analysis-case")
 ]);
 const profile=disclosure("قياس البلوكات والأسطر مع مرجع","ux-profile-options",[
  desc("هذا القياس يضم كلفة التتبع؛ لا يمثل زمن المسابقة."),field("profile-case"),by("profile-run")
 ]);
 const timing=disclosure("خيارات القياس والمهلة","ux-timing-options",[label("timing-repetitions"),label("timing-seconds")]);
 const manual=by("manual-stdin").closest("details");
 const sample=disclosure("مقارنة مع خرج متوقع (اختياري)","ux-sample-options",[
  field("manual-expected"),label("sample-reviewed"),label("sample-comparison")
 ]);
 const stdin=field("manual-stdin"),observe=by("observe-run"),benchmark=by("plain-benchmark");
 const scaling=by("scaling-benchmark").closest("details");
 const scale=disclosure("قياس نمو الأداء على مدخلات قانونية","ux-scale-options",[
  desc("يتطلب مسألة معتمدة. اختر حقل الحجم وأحجاماً متعددة."),field("size-field"),field("size-values"),by("scaling-benchmark")
 ]);
 const taskHint=desc("");taskHint.id="ux-task-hint";
 const aiLabel=label("ai");for(const child of aiLabel.childNodes){if(child.nodeType===3)child.textContent=" مساعدة الذكاء الاصطناعي (اختياري)";}const diagnoseControls=append(node("div","ux-task-controls"),aiLabel);
 const independentControls=append(node("div","ux-task-controls"),stdin,sample,timing);
 const performanceControls=append(node("div","ux-task-controls"),scale,profile);
 const actionRow=append(node("div","ux-actions"),run,observe,benchmark,cancel);
 const friendly=node("p","ux-status-message","");friendly.hidden=true;friendly.id="ux-friendly-status";friendly.setAttribute("role","status");
 const ch=codePanel.querySelector("h2"),editor=append(node("div","ux-editor-title"),node("span","","solution.py"),node("span","","Python"));
 trusted.classList.add("ux-field");aiLabel.classList.add("ux-field");
 run.textContent="ابحث عن الخطأ";observe.textContent="ابدأ التتبع";benchmark.textContent="قس زمن التنفيذ";cancel.textContent="إلغاء";
 codePanel.replaceChildren(ch,taskHint,editor,source,trusted,node("p","ux-safety","شغّل فقط كوداً تثق به. العزل يقلل المخاطر ولا يضمن أمان الكود العدائي."),diagnoseControls,independentControls,actionRow,advanced,performanceControls,friendly,status);
 heading(codePanel,"2","الكود والتنفيذ");
 // Settings are available without presenting provider internals on the normal path.
 const settingItems=Array.from(settings.childNodes);
 const settingsDetails=disclosure("إعدادات الذكاء الاصطناعي والاتصال","ux-model-settings",settingItems);
 settings.classList.add("ux-settings");settings.replaceChildren(settingsDetails);
 workspace.after(settings);
 by("ai").addEventListener("change",()=>{if(by("ai").checked&&!by("model").value.startsWith("qwen2.5-coder:"))settingsDetails.open=true});
 function setMode(id){
  if(busy)return;
  mode=id;for(const b of modeButtons)b.setAttribute("aria-pressed",String(b.dataset.mode===id));
  const diagnose=id==="diagnose",performance=id==="performance";
  diagnoseControls.hidden=!diagnose;advanced.hidden=!diagnose;independentControls.hidden=diagnose;performanceControls.hidden=!performance;
  sample.hidden=performance;run.hidden=!diagnose;observe.hidden=id!=="understand";benchmark.hidden=!performance;
  taskHint.textContent=diagnose?"ألصق حلّك ثم ابحث عن حالة فشل مقابل المسألة المعتمدة.":performance?"أدخل البرنامج ومدخلاً يدوياً لقياس الزمن، أو جرّب أحجاماً مختلفة لمسألة معتمدة.":"أدخل البرنامج ومدخلاً يدوياً لتتبع خطوات التنفيذ دون الحاجة إلى حل مرجعي.";
  problemHint.textContent=diagnose?"اختر مسألة معتمدة للبحث عن أخطاء الحل.":performance?"اختيار مسألة معتمدة مطلوب فقط لقياس النمو على مدخلات قانونية.":"يمكنك تخطي هذه الخطوة، أو تحميل مثال لتجربة التتبع.";
  if(id==="understand")sample.open=false;
 }
 for(const b of modeButtons)b.addEventListener("click",()=>setMode(b.dataset.mode));
 setMode(mode);updateAvailable();
 source.addEventListener("input",()=>{by("trusted").checked=false});
 // Keep results readable by grouping, but preserve the original evidence and links.
 const results=by("results"),resultTitle=by("result-title"),scope=by("scope");
 const triplet=by("stdin").closest(".triplet"),reduction=by("reduction-panel"),localization=by("localization-panel"),diagnostics=by("execution-diagnostics");
 const compare=by("cmp-student").closest(".compare"),compareHeading=compare.previousElementSibling;
 const compareNote=compare.nextElementSibling;
 const matrix=by("matrix-view"),ranking=by("ranking"),coverage=by("branch-coverage"),branchRanking=by("branch-ranking");
 const coverageScope=by("branch-coverage-scope");
 const comparison=disclosure("مقارنة التنفيذ والتغطية","ux-compare",[
  compareHeading,compare,compareNote,matrix.previousElementSibling,matrix,ranking.previousElementSibling,ranking,
  coverageScope.previousElementSibling,coverageScope,coverage,branchRanking.previousElementSibling,branchRanking
 ]);
 const traceToolbar=by("student").closest(".toolbar"),visual=by("graph").closest(".visual");
 const deepTraceIds=["previous-locals","snapshot-changes","loops","stack","changes","relations","output-chain","static-cfg"];
 const deepTraceItems=[];for(const id of deepTraceIds){const e=by(id);deepTraceItems.push(e.previousElementSibling,e)}
 const traceDetails=disclosure("لقطات إضافية وعلاقات البيانات والتحكم","ux-trace-details",deepTraceItems);
 by("code").closest("div").append(traceDetails);
 const trace=disclosure("استكشف التنفيذ خطوة بخطوة","ux-trace",[traceToolbar,visual],true);
 const profiling=disclosure("تفاصيل زمن البلوكات والأسطر","ux-timing-results",[by("profiling")]);
 const ast=by("ast-tree").closest("details");ast.classList.add("ux-disclosure");
 const aiIds=["hypotheses","probes","facts","branch-facts"];
 const aiHeading=by("ai-state").previousElementSibling,aiState=by("ai-state"),aiItems=[aiHeading,aiState,by("hypotheses")];
 for(const id of aiIds.slice(1)){const e=by(id);aiItems.push(e.previousElementSibling,e)}
 aiItems.push(by("ai-context").closest("details"));
 const aiResults=disclosure("تفسير الذكاء الاصطناعي وأدلته","ux-ai-results",aiItems);
 const reductionEvidence=by("reduction-evidence").parentElement;
 reduction.append(disclosure("تفاصيل التصغير وإعادة التحقق","ux-reduction-evidence",[reductionEvidence]));
 const resultCaution=desc("هذه النتيجة تخص المدخلات المجربة. مواضع الاشتباه والفرضيات ليست إثباتاً للسبب الجذري.");
 const raw=disclosure("حدود النتيجة والأدلة القابلة للتصدير","ux-evidence",[scope,by("export")]);
 const repair=by("repair-panel"),repairChildren=Array.from(repair.childNodes);
 repair.replaceChildren(disclosure("جرّب إصلاح الحل والتحقق منه","ux-repair",repairChildren));
 const history=disclosure("سجل محاولات الإصلاح","ux-repair-history",[label("repair-history"),by("load-repair"),by("repair-history-view")]);
 by("ux-repair").lastElementChild.append(history);
 resultTitle.classList.add("ux-result-title");
 results.replaceChildren(resultTitle,resultCaution,triplet,diagnostics,reduction,localization,trace,comparison,profiling,ast,aiResults,repair,raw);
 const reports=by("reports"),reportItems=Array.from(reports.childNodes);reports.classList.add("ux-settings");
 reports.replaceChildren(disclosure("سجل التشغيل والتقارير البحثية","ux-run-reports",reportItems));
 const growth=by("benchmark-growth");const growthParent=growth.parentNode;growthParent.append(disclosure("تفاصيل نموذج النمو وحدوده","ux-benchmark-growth",[growth]));
 const footer=node("p","ux-footer","AlgoXRay · تجربة محلية · الملاحظات والفرضيات لا تثبت صحة جميع المدخلات أو السبب الجذري.");
 main.append(footer);
 // Preserve original behavior while exposing the appropriate evidence on demand.
 const originalBusy=setBusy;setBusy=function(value){originalBusy(value);for(const b of modeButtons)b.disabled=value};
 const originalJump=jumpToEvidence;jumpToEvidence=function(...args){trace.open=true;originalJump(...args)};
 for(const id of ["ast-tree","profile-table"])by(id).addEventListener("click",e=>{if(e.target.closest("button"))trace.open=true},true);
 const originalShow=show;show=function(){
  originalShow();
  const manualResult=result.status==="manual_observation",profileResult=result.status==="profiled_execution";
  resultTitle.textContent=manualResult?"نتيجة تتبع البرنامج":profileResult?"نتيجة قياس التنفيذ":"وجدنا حالة فشل قابلة للمراجعة";
  triplet.classList.toggle("ux-mismatch",result.status==="observed_mismatch"&&result.kind!=="exception");
  by("expected").parentElement.classList.add("ux-expected");
  by("actual").parentElement.classList.add("ux-actual");
  resultCaution.textContent=manualResult?"تتبع مدخل يدوي؛ لا يثبت صحة الحل ولا قانونية المدخل.":profileResult?"الزمن أثناء التتبع يصف تنفيذاً واحداً، وليس زمن المسابقة.":"هذه حالة فشل مرصودة؛ مواضع الاشتباه والفرضيات لا تثبت السبب الجذري.";
  trace.open=true;comparison.open=false;profiling.open=profileResult;aiResults.open=Boolean(result.hypotheses?.length);
  raw.open=false;
  if(result.evidence_localization)by("localization-scope").textContent="هذه ترشيحات مبنية على الأدلة المتاحة، وليست احتمالاً معايراً أو إثباتاً للسبب الجذري.";
  if(!manualResult&&result.evidence_localization?.ranked?.length===0)localization.querySelector("h3").textContent="موضع الاشتباه (غير محدد)";
  else localization.querySelector("h3").textContent="مواضع تستحق المراجعة";
 };
 by("prepare-replay").addEventListener("click",()=>{
  if(!importedReport||by("trusted").checked)return;
  const op=importedReport.run_report.operation;
  if(op==="observe")setMode("understand");else if(op==="profile"){setMode("performance");profile.open=true}else setMode("diagnose");
 });
 const readableStatuses={
  observed_mismatch:["وجدنا حالة فشل قابلة للمراجعة. تفاصيلها أدناه.","warning"],
  no_witness_found:["لم نجد خطأ ضمن الحالات المجربة. هذا لا يثبت صحة الحل لجميع المدخلات.","positive"],
  manual_observation:["تم تسجيل التنفيذ. راجع المخرجات والخطوات أدناه.","positive"],
  profiled_execution:["تم قياس تنفيذ واحد؛ راجع تفاصيل القياس.","positive"],
  benchmark_observation:["اكتمل طلب القياس. راجع النتائج وحدودها.","positive"],
  cancelled:["أُلغي الطلب. قد توجد ملاحظات جزئية في تقرير التشغيل.","warning"],
  oracle_unavailable:["تعذر الحكم باستخدام المرجع. راجع المسألة وتقرير التشغيل.","warning"],
  inconclusive:["النتيجة غير حاسمة. راجع سبب التوقف في سجل التشغيل.","warning"]
 };
 function syncStatus(){const raw=status.textContent.trim(),key=raw.split(/[\s·]/)[0],v=readableStatuses[key];friendly.hidden=!v;if(v){friendly.textContent=v[0];friendly.dataset.tone=v[1]}}
 new MutationObserver(syncStatus).observe(status,{childList:true,characterData:true,subtree:true});
})();
