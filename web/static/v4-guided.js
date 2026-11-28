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
 const intro=append(node("div","ux-intro"),node("p","ux-eyebrow","مساحة عمل AlgoXRay"),node("h2","","افهم حلّك خطوة بخطوة"),desc("أضف المسألة والكود. سنبحث عن الأخطاء ونشرح التنفيذ ونقيس الزمن."));
 const modes=node("div","ux-modes");modes.setAttribute("role","group");modes.setAttribute("aria-label","هدف التحليل");
 let mode="full",tabs=null;
 const modeButtons=[];
 for(const [id,n,title,detail] of [
  ["full","01","التحليل الشامل","افهم التنفيذ، اكتشف الأخطاء، وقس الأداء في رحلة واحدة."],
  ["diagnose","02","تشخيص الخطأ","اعثر على حالة فشل صغيرة وافحص سببها المحتمل."],
  ["understand","03","فهم التنفيذ","شاهد خطوات الكود والقيم المتغيرة على مدخل تختاره."],
  ["performance","04","قياس الأداء","قس الزمن دون تتبع أو افحص نمو الزمن مع حجم المدخلات."]
 ]){
  const b=node("button","ux-mode");b.type="button";b.dataset.mode=id;b.setAttribute("aria-pressed",String(mode===id));
  append(b,node("span","ux-mode-index",n),node("strong","",title),node("small","",detail));modes.append(b);modeButtons.push(b);
 }
 const separateModes=node("div","ux-single-modes");append(separateModes,...modeButtons.slice(1));
 const separate=disclosure("أدوات منفصلة (اختياري)","ux-separate-modes",[separateModes]);
 modes.append(separate);modes.classList.add("ux-full-modes");
 main.prepend(intro,modes);
 const workspace=node("div","ux-workspace");modes.after(workspace);append(workspace,problem,codePanel);
 // Prepare the problem in a distinct section. Reviewing a reference remains explicit.
 const approved=label("packages");approved.classList.add("ux-field");
 const approval=by("approval"),reviewLabel=label("reviewed"),approve=by("approve"),audit=by("audit-reference");
 const fullTarget=node("select");fullTarget.id="ux-full-target";
 for(const [v,t] of [["draft","المسودة الحالية / المثال"],["approved","مسألة معتمدة"]]){
  const option=node("option","",t);option.value=v;fullTarget.append(option)
 }
 const targetLabel=node("label","ux-field","المسألة المستخدمة ");targetLabel.append(fullTarget);
 const preflightNote=node("p","ux-description");preflightNote.id="ux-preflight-note";
 const demoToolbar=by("demo").closest(".toolbar"),importToolbar=by("problem-url").closest(".toolbar");
 const statementField=field("statement"),manualSamples=field("manual-samples");
 const statementKind=by("statement-kind").closest(".toolbar");
 const pkgField=field("package"),packagePreview=node("div","ux-package-preview");
 const packageJson=disclosure("تعديل العقد التقني JSON","ux-package-json",[pkgField]);
 const packageReview=disclosure("مراجعة المسألة والحل المرجعي","ux-package-review",[
  desc("قبل البحث عن الخطأ، راجع قيود المدخلات والحل المرجعي واختبارات مستقلة. مسودة الذكاء الاصطناعي لا تعد اعتماداً."),
  packagePreview,packageJson,reviewLabel,append(node("div","ux-actions"),approve,audit),by("reference-audit")
 ]);
 const newProblem=disclosure("إعدادات المسألة والتدقيق","ux-new-problem",[
  desc("يمكنك تعديل طريقة تجهيز المسألة وإضافة أمثلة مستقلة للمراجعة."),
  by("import-samples"),statementKind,manualSamples,by("intake-review"),by("draft-review")
 ]);
 const urlInput=disclosure("أو استورد رابط Codeforces","ux-url-input",[importToolbar]);
 statementField.querySelector("textarea").dir="auto";
 const statementLabel=statementField.querySelector("label");
 if(statementLabel)statementLabel.textContent="نص المسألة";
 statementField.querySelector("textarea").rows=5;statementField.querySelector("textarea").placeholder="ألصق نص المسألة هنا…";
 const prepareDraft=by("draft"),draftReference=by("draft-reference");
 const prepareRow=append(node("div","ux-actions"),prepareDraft);
 const draftEntry=append(node("div","ux-draft-entry"),statementField,urlInput,prepareRow);

 const currentProblem=append(node("div",""),node("strong","","المسألة الحالية"),desc(""));currentProblem.id="ux-current-problem";
 packageReview.lastElementChild.insertBefore(draftReference,packageJson);
 const authorForm=window.AlgoXRayReviewForm.form(
  ()=>JSON.parse(by("package").value),
  pkg=>{by("package").value=JSON.stringify(pkg,null,2);by("package").dispatchEvent(new Event("input",{bubbles:true}));},
  async pkg=>{setBusy(true);try{return await api("/api/v4/packages/preflight",{package:pkg})}finally{setBusy(false)}},
  ()=>busy);
 const author=disclosure("إدخال المرجع والاختبارات دون JSON","ux-human-review",[authorForm.panel]);
 packageReview.lastElementChild.insertBefore(author,packageJson);
 author.addEventListener("toggle",()=>{if(author.open&&!authorForm.isDirty())authorForm.refresh()});
 const preparationHelp=desc("جهّز المسألة الجديدة أولاً. المرجع الناتج مسودة، ويحتاج إلى اختبارات مستقلة ومراجعة قبل التشغيل.");
 preparationHelp.id="ux-preparation-help";
 // Keep all review controls reachable after loading or authoring a draft.
 const problemHint=desc("اختر مسألة معتمدة للبحث عن أخطاء الحل. يمكنك فهم التنفيذ أو قياسه دون مرجع.");
 const available=node("p","ux-description");available.id="ux-package-availability";
 const example=append(node("div","ux-example"),desc("مثال تدريبي جاهز للمراجعة."),demoToolbar);
 const savedProblem=disclosure("أمثلة ومسائل محفوظة","ux-problem-library",[targetLabel,approved,available,example]);
 const approvalMessage=node("p","ux-status-message");approvalMessage.hidden=true;
 const approvalDetails=disclosure("تفاصيل فحص المسألة","ux-approval-details",[approval]);approvalDetails.hidden=true;
 const ph=problem.querySelector("h2");packageReview.lastElementChild.append(newProblem,preflightNote);
 problem.replaceChildren(ph,problemHint,currentProblem,draftEntry,preparationHelp,savedProblem,packageReview,approvalMessage,approvalDetails);
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
 by("draft").textContent="جهّز المسألة (AI)";by("draft-reference").textContent="اقترح حلاً مرجعياً (AI)";
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
   const extra=Object.entries(f).filter(([k])=>!["name","kind","min","max"].includes(k)).map(([k,v])=>k+": "+String(v)).join(" · ");
   append(fields,append(node("div","ux-constraint"),node("strong","",String(f.name??"")),node("span","",String(f.kind??"")+" "+limits+(extra?" · "+extra:""))));
  }
  packagePreview.append(fields);
  const format=node("div","ux-package-rules");
  const rules=[["ترتيب المدخلات",Array.isArray(m.lines)?m.lines.map(r=>Array.isArray(r)?r.join(" "):String(r)).join(" / "):"—"],
   ["مقارنة المخرجات",String(m.output??"—")]];
  if(m.tolerance)rules.push(["السماحية العددية",Object.entries(m.tolerance).map(([k,v])=>k+"="+v).join(" · ")]);
  if(m.repeat)rules.push(["عدد الحالات",String(m.repeat.min)+" .. "+String(m.repeat.max)]);
  if(Array.isArray(m.relations)&&m.relations.length)rules.push(["علاقات الحقول",m.relations.filter(r=>r&&typeof r==="object").map(r=>String(r.left)+" "+({le:"≤",lt:"<",ge:"≥",gt:">",eq:"="}[r.op]||r.op)+" "+String(r.right)).join(" · ")]);
  if(p.checker)rules.push(["الحكم الدلالي",Object.entries(p.checker).map(([k,v])=>k+": "+String(v)).join(" · ")]);
  for(const [title,value] of rules){const row=node("div","ux-rule");append(row,node("span","",title),node("strong","",value));format.append(row)}
  packagePreview.append(format);
  const ref=node("pre","",typeof p.reference==="string"&&p.reference?p.reference:"لم يتم إعداد حل مرجعي بعد.");
  const referenceItems=[ref];
  if(typeof p.reference_alt==="string"&&p.reference_alt)referenceItems.push(node("h4","","المرجع الثاني"),node("pre","",p.reference_alt));
  packagePreview.append(disclosure("معاينة الحل المرجعي","ux-preview-reference",referenceItems));
  const controls=node("div","ux-control-preview");
  for(const c of (Array.isArray(p.controls)?p.controls:[])){
   if(!c||typeof c!=="object")continue;
   append(controls,append(node("div","ux-control-row"),node("pre","",JSON.stringify(c.case??null)),node("pre","",String(c.expected??""))));
  }
  if(!controls.children.length)controls.append(desc("أضف اختبارات مستقلة ونتائجها المتوقعة في محرر العقد قبل الاعتماد."));
  packagePreview.append(disclosure("الاختبارات المستقلة ("+controls.querySelectorAll(".ux-control-row").length+")","ux-preview-controls",[controls]));
  if(p.checker)packagePreview.append(desc("تستخدم المسألة حكماً دلالياً؛ راجع قاعدته في العقد التقني."));
  if(p.provenance||p.intake)packagePreview.append(disclosure("مصدر المسألة وقيود المسودة غير المحسومة","ux-preview-provenance",[
    desc("راجع مصدر القيود والنقاط غير المحسومة قبل الاعتماد."),node("pre","",JSON.stringify({provenance:p.provenance,intake:p.intake},null,2))
  ]));
  packagePreview.append(desc("راجع القيود والمرجع والاختبارات أعلاه مقابل النص الأصلي. محرر JSON متاح للتعديل والتدقيق الكامل عند الحاجة."));
 }
 by("package").addEventListener("input",()=>{by("reviewed").checked=false;renderPackagePreview();if(author.open)authorForm.refresh()});
 new MutationObserver(()=>{renderPackagePreview();if(author.open&&!authorForm.isDirty())authorForm.refresh()}).observe(approval,{childList:true,subtree:true});
 renderPackagePreview();
 function updateAvailable(){
  const count=by("packages").options.length;
  available.textContent=count?"المسائل المعتمدة متاحة للاختبار.":"لا توجد مسألة معتمدة بعد. أضف مسألة أو راجع مثالاً.";
  fullTarget.options[1].disabled=!count;
  if(!count&&fullTarget.value==="approved")fullTarget.value="draft";
  approved.hidden=!count||(mode==="full"&&fullTarget.value!=="approved");
  const useApproved=mode==="full"&&fullTarget.value==="approved";
  let title="",ready=false;
  try{const pkg=JSON.parse(by("package").value);title=pkg?.manifest?.title||"";ready=Boolean(title&&pkg.manifest.statement===by("statement").value&&pkg.reference&&pkg.controls?.length>=2)}catch(e){}
  prepareRow.hidden=ready;preparationHelp.hidden=ready||useApproved;
  currentProblem.querySelector("strong").textContent=useApproved?(by("packages").selectedOptions[0]?.textContent.split(" · ")[0]||"مسألة محفوظة"):title||"مسألة جديدة";
  currentProblem.querySelector("p").textContent=useApproved?"مسألة راجعتها سابقاً":title?"المسودة الحالية · تحتاج المراجعة إذا لم تعتمدها":"ألصق النص أو استورد الرابط";
  draftEntry.hidden=useApproved;
  if(mode!=="full")savedProblem.open=true;
 }
 new MutationObserver(updateAvailable).observe(by("packages"),{childList:true});
 // Core code editor and task-specific controls. No request is sent by mode selection.
 const source=by("source"),trusted=label("trusted"),status=by("status"),run=by("run"),cancel=by("cancel");
 const sourceFile=node("input");sourceFile.type="file";sourceFile.accept=".py,text/plain";sourceFile.hidden=true;sourceFile.id="ux-source-file";
 const fileButton=node("button","","تحميل ملف .py");fileButton.type="button";fileButton.id="ux-load-source";
 fileButton.onclick=()=>{if(!busy)sourceFile.click()};
 sourceFile.onchange=async()=>{
  const f=sourceFile.files?.[0];sourceFile.value="";
  if(!f||busy)return;
  if(f.size>32768){msg("status","الملف أكبر من الحد المسموح (32 KiB).");return}
  try{const code=await f.text();if(busy)return;source.value=code;source.dispatchEvent(new Event("input",{bubbles:true}))}catch(e){msg("status","تعذر قراءة الملف.")}
 };
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
 const independentControls=append(node("div","ux-task-controls"),stdin,sample);
 const performanceControls=append(node("div","ux-task-controls"),scale,profile);
 const fullButton=node("button","ux-primary");fullButton.id="ux-run-full";fullButton.type="button";
 const fullConsent=desc("");fullConsent.id="ux-full-consent";
 const actionRow=append(node("div","ux-actions"),fullButton,run,observe,benchmark,cancel);
 const friendly=node("p","ux-status-message","");friendly.hidden=true;friendly.id="ux-friendly-status";friendly.setAttribute("role","status");
 const ch=codePanel.querySelector("h2"),editor=append(node("div","ux-editor-title"),node("span","","solution.py"),fileButton,sourceFile);
 trusted.classList.add("ux-field");aiLabel.classList.add("ux-field");
 run.textContent="ابحث عن الخطأ";observe.textContent="ابدأ التتبع";benchmark.textContent="قس زمن التنفيذ";cancel.textContent="إلغاء";
 codePanel.replaceChildren(ch,taskHint,editor,source,trusted,node("p","ux-safety","شغّل فقط كوداً تثق به. العزل يقلل المخاطر ولا يضمن أمان الكود العدائي."),diagnoseControls,independentControls,fullConsent,actionRow,advanced,timing,performanceControls,friendly,status);
 heading(codePanel,"2","الكود والتنفيذ");
 // Settings are available without presenting provider internals on the normal path.
 const settingItems=Array.from(settings.childNodes);
 const settingsWarning=node("p","ux-status-message");settingsWarning.hidden=true;settingsWarning.setAttribute("role","status");settingsWarning.dataset.tone="warning";
 const settingsDetails=disclosure("إعدادات الذكاء الاصطناعي والاتصال","ux-model-settings",[settingsWarning,...settingItems]);
 settings.classList.add("ux-settings");settings.replaceChildren(settingsDetails);
 for(const id of ["model","cloud-consent","ai"])by(id).addEventListener("change",()=>{settingsWarning.hidden=true});
 const tools=disclosure("إعدادات وأدوات إضافية","ux-tools",[diagnoseControls,advanced,timing,settings,modes]);
 const toolsPanel=append(node("section","panel ux-compact-tools"),tools);
 workspace.after(toolsPanel);
 // In the default view there is no separate task picker above the editor.
 intro.classList.add("ux-compact-intro");
 by("ai").addEventListener("change",()=>{if(by("ai").checked&&!by("model").value.startsWith("qwen2.5-coder:"))settingsDetails.open=true});
 function setMode(id){
  if(busy)return;
  mode=id;for(const b of modeButtons)b.setAttribute("aria-pressed",String(b.dataset.mode===id));
  const full=id==="full",diagnose=id==="diagnose",performance=id==="performance";
  diagnoseControls.hidden=!(full||diagnose);advanced.hidden=!(full||diagnose);independentControls.hidden=full||diagnose;performanceControls.hidden=!performance;
  modes.classList.toggle("ux-show-full",!full);
  if(!full)tools.open=true;
  timing.hidden=diagnose;sample.hidden=performance;run.hidden=!diagnose;observe.hidden=id!=="understand";benchmark.hidden=!performance;
  fullButton.hidden=!full;fullConsent.hidden=!full;targetLabel.hidden=!full;
  trusted.hidden=full;reviewLabel.hidden=full;approve.hidden=full;
  preflightNote.hidden=!full;updateAvailable();updateFullConsent();
  if(!full)separate.open=true;
  taskHint.textContent=full?"ألصق كود Python أو حمّل ملفاً من جهازك.":diagnose?"ألصق حلّك ثم ابحث عن حالة فشل مقابل المسألة المعتمدة.":performance?"أدخل البرنامج ومدخلاً يدوياً لقياس الزمن، أو جرّب أحجاماً مختلفة لمسألة معتمدة.":"أدخل البرنامج ومدخلاً يدوياً لتتبع خطوات التنفيذ دون الحاجة إلى حل مرجعي.";
  problemHint.textContent=full?"ألصق نص المسألة أو اختر مثالاً محفوظاً.":diagnose?"اختر مسألة معتمدة للبحث عن أخطاء الحل.":performance?"اختيار مسألة معتمدة مطلوب فقط لقياس النمو على مدخلات قانونية.":"يمكنك تخطي هذه الخطوة، أو تحميل مثال لتجربة التتبع.";
  if(id==="understand")sample.open=false;
 }
 function updateFullConsent(){
  const draft=fullTarget.value==="draft";
  fullButton.textContent=busy?"جارٍ التحليل…":"حلّل لي الحل";
  fullConsent.textContent=draft?
   "بالضغط تؤكد مراجعة الكود والمرجع والاختبارات؛ المسألة الجديدة ستُعرض للمراجعة أولاً.":
   "بالضغط تؤكد أنك تثق بالكود للتشغيل المحلي على المسألة المختارة.";
  if(!draft){preflightNote.textContent="سيُستخدم عقد المسألة المعتمدة دون إعادة اعتمادها.";return}
  try{
   const p=JSON.parse(by("package").value);
   preflightNote.textContent=p&&p.manifest&&typeof p.reference==="string"&&p.reference&&Array.isArray(p.controls)&&p.controls.length>=2?
    "صيغة JSON قابلة للقراءة. يُفحص العقد تلقائياً قبل التشغيل؛ المراجعة الدلالية مسؤوليتك.":
    "المسودة غير مكتملة: أضف المرجع واختبارين مستقلين على الأقل.";
  }catch(e){preflightNote.textContent="صيغة JSON غير صالحة أو لا توجد مسودة بعد."}
 }
 fullTarget.addEventListener("change",()=>{updateAvailable();updateFullConsent()});
 by("packages").addEventListener("change",()=>{if(by("packages").value){fullTarget.value="approved";updateAvailable();updateFullConsent()}});
 for(const id of ["load","draft","draft-reference","import-problem","prepare-statement"]){
  by(id).addEventListener("click",()=>{fullTarget.value="draft";updateAvailable();updateFullConsent()})
 }
 by("package").addEventListener("input",()=>{fullTarget.value="draft";updateAvailable();updateFullConsent()});
 by("statement").addEventListener("input",()=>{fullTarget.value="draft";updateAvailable();updateFullConsent()});
 let importedUrlText="";
 by("problem-url").addEventListener("input",()=>{fullTarget.value="draft";updateAvailable();updateFullConsent()});
 const originalImport=by("import-problem").onclick;
 by("import-problem").onclick=async()=>{if(busy)return;const raw=by("problem-url").value.trim(),before=activeIntake;await originalImport();if(activeIntake&&activeIntake!==before&&activeIntake.kind==="codeforces")importedUrlText=raw};
 by("load").addEventListener("click",()=>{by("problem-url").value="";importedUrlText=""});

 new MutationObserver(()=>{updateAvailable();updateFullConsent()}).observe(approval,{childList:true,subtree:true,characterData:true});

 new MutationObserver(updateFullConsent).observe(approval,{childList:true,characterData:true,subtree:true});
 for(const b of modeButtons)b.addEventListener("click",()=>{setMode(b.dataset.mode);tabs?.select("input",true)});
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
 const storySlot=node("div");storySlot.id="ux-story-slot";
 const advancedResult=disclosure("التفاصيل المتقدمة والرسوم التقنية","ux-story-details",[diagnostics,reduction,localization,trace,comparison,profiling,ast,aiResults,repair,raw]);
 results.classList.add("ux-story-output");
 results.replaceChildren(resultTitle,resultCaution,triplet,storySlot,advancedResult);
 const reports=by("reports"),reportItems=Array.from(reports.childNodes);reports.classList.add("ux-settings");
 reports.replaceChildren(disclosure("سجل التشغيل والتقارير البحثية","ux-run-reports",reportItems));
 const growth=by("benchmark-growth"),benchPanel=by("benchmark-results"),benchHeading=benchPanel.querySelector("h2");
 const growthParent=growth.parentNode;growthParent.append(disclosure("تفاصيل نموذج النمو وحدوده","ux-benchmark-growth",[growth]));
 const benchSlot=node("div");benchSlot.id="ux-bench-story-slot";
 const benchDetails=disclosure("الأرقام والتقرير التفصيلي","ux-bench-details",Array.from(benchPanel.childNodes).filter(n=>n!==benchHeading));
 benchPanel.replaceChildren(benchHeading,benchSlot,benchDetails);
 const originalBenchmark=showBenchmark;showBenchmark=function(){
  originalBenchmark();
  if(!benchmarkResult)return;
  benchSlot.replaceChildren(window.AlgoXRayStory.performance(benchmarkResult));
  benchDetails.open=mode!=="full";tabs?.refresh();
 };
 const footer=node("p","ux-footer","AlgoXRay · تجربة محلية · الملاحظات والفرضيات لا تثبت صحة جميع المدخلات أو السبب الجذري.");
 main.append(footer);
 // Preserve original behavior while exposing the appropriate evidence on demand.
 const fullPanel=node("section","panel ux-full-result");fullPanel.id="ux-full-result";fullPanel.hidden=true;
 const fullTitle=node("h2","","نتيجة التحليل الشامل");
 const fullProgress=node("p","ux-status-message");fullProgress.id="ux-full-progress";fullProgress.setAttribute("role","status");
 const fullCards=node("div","ux-full-cards"),fullValues={};
 for(const [key,title] of [["diagnosis","التشخيص"],["trace","فهم التنفيذ"],["timing","زمن التنفيذ"]]){
  const card=node("div","ux-full-card"),v=node("strong","","لم يبدأ");v.id="ux-full-"+key;fullValues[key]=v;
  append(card,node("span","",title),v);fullCards.append(card);
 }
 const fullExport=node("button","","حفظ التقرير الشامل");
 fullExport.type="button";fullExport.hidden=true;
 fullExport.id="ux-full-export";
 append(fullPanel,fullTitle,fullProgress,fullCards,desc("زمن التشغيل العادي يُقاس دون التتبع على المدخل المختار. عدد مرات التشغيل الفعلية يظل مسجلاً في الأدلة."),fullExport);
 workspace.after(fullPanel);
 fullPanel.after(results,by("benchmark-results"),toolsPanel);
 let fullActive=false,fullCancelled=false,fullReport=null;
 function clearFull(){if(fullActive)return;fullReport=null;fullPanel.hidden=true;fullExport.hidden=true}
 function invalidateFull(){if(fullActive||busy)return;if(fullReport)invalidateResult();clearFull()}
 const originalBusy=setBusy;setBusy=function(value){
  originalBusy(value);for(const b of modeButtons)b.disabled=value;
  fullTarget.disabled=fullButton.disabled=fileButton.disabled=value;authorForm.setBusy(value);
  updateFullConsent();
  tabs?.refresh();
 };
 for(const id of ["source","package","analysis-case","session-seconds","timing-repetitions","timing-seconds","count","reduce-count","statement","problem-url","manual-stdin","manual-expected","profile-case","size-field","size-values"]){
  by(id).addEventListener("input",invalidateFull)
 }
 for(const id of ["packages","model","ai","generator","guided","spectrum","cloud-consent","use-cache","sample-reviewed","sample-comparison"]){by(id).addEventListener("change",invalidateFull)}
 for(const id of ["load","correct","mutant","prepare-replay","draft","draft-reference","prepare-statement","import-problem","approve"]){by(id).addEventListener("click",invalidateFull)}
 fullTarget.addEventListener("change",invalidateFull);
 for(const id of ["run","observe-run","plain-benchmark","scaling-benchmark","profile-run"]){
  by(id).addEventListener("click",()=>{if(!busy){invalidateResult();clearFull();tabs?.refresh()}},true);
 }
 const originalRunReport=showRunReport;showRunReport=function(data){originalRunReport(data);tabs?.noteReport(data)};

 cancel.addEventListener("click",()=>{if(fullActive){fullCancelled=true;fullProgress.textContent="طُلب الإلغاء؛ لن تبدأ مرحلة أخرى."}},true);
 fullExport.onclick=()=>{
  if(!fullReport)return;
  const blob=new Blob([JSON.stringify(fullReport,null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="algoxray-comprehensive-"+fullReport.id+".json";a.click();URL.revokeObjectURL(url)
 };
 fullButton.onclick=async()=>{
  if(busy)return;
  const code=source.value,fromDraft=fullTarget.value==="draft",reviewWasVisible=packageReview.open&&Boolean(by("ux-preview-reference")?.open)&&Boolean(by("ux-preview-controls")?.open)&&(!by("ux-preview-provenance")||by("ux-preview-provenance").open);
  let draft=null,key=by("packages").value,caseValue=null;
  if(!code.trim()){msg("status","أضف كود Python أولاً.");return}
  try{
   caseValue=by("analysis-case").value.trim()?JSON.parse(by("analysis-case").value):null;
   if(fromDraft)draft=JSON.parse(by("package").value);
  }catch(e){packageReview.open=true;packageJson.open=true;msg("status","صيغة JSON غير صالحة. راجع المسألة أو حالة الاختبار.");return}
  if(!fromDraft&&!key){msg("status","اختر مسألة معتمدة.");return}
  if(fromDraft&&authorForm.isDirty()){
   packageReview.open=true;author.open=true;msg("status","احفظ المرجع والاختبارات في نموذج المراجعة أولاً.");return
  }
  if(fromDraft&&by("problem-url").value.trim()&&by("problem-url").value.trim()!==importedUrlText){
   urlInput.open=true;msg("status","استورد الرابط أولاً قبل تحليل المسألة.");return
  }
  if(fromDraft&&by("statement").value.trim()&&draft?.manifest?.statement!==by("statement").value){
   draftEntry.hidden=false;prepareDraft.focus();
   msg("status","تغيّر نص المسألة. اضغط «جهّز المسألة» لإنشاء مسودة مطابقة، ثم راجعها.");return
  }
  const modelOptions=aiOptions(),useAI=by("ai").checked;
  if(useAI&&!modelOptions.model.startsWith("qwen2.5-coder:")&&!modelOptions.cloud_consent){settingsDetails.open=true;tools.open=true;settingsWarning.textContent="راجع موافقة إرسال البيانات إلى المزود السحابي أو اختر نموذجاً محلياً، ثم ارجع إلى الإدخال للتحليل.";settingsWarning.hidden=false;tabs?.select("advanced",true);msg("status",settingsWarning.textContent);return}
  clearFull();fullActive=true;fullCancelled=false;
  fullReport={format:"algoxray_comprehensive_report",version:1,id:crypto.randomUUID().replaceAll("-",""),status:"running",phases:[],scope:"Local composite report; individual phase reports retain their own IDs and budgets. Not a signature or general correctness proof."};
  fullPanel.hidden=false;for(const v of Object.values(fullValues)){v.textContent="بانتظار التنفيذ";delete v.parentElement.dataset.tone}
  fullProgress.textContent="جارٍ فحص المسألة…";fullProgress.dataset.tone="neutral";
  results.hidden=true;by("benchmark-results").hidden=true;result=null;benchmarkResult=null;
  setBusy(true);cancel.hidden=false;msg("status","");
  async function phase(name,path,body){
   if(fullCancelled)return null;
   const id=crypto.randomUUID().replaceAll("-","");analysisId=id;
   const data=await api(path,{...body,analysis_id:id});
   if(data.analysis_id!==id||source.value!==code)throw Error("Run identity changed; no new stage started.");
   fullReport.phases.push({name,data});analysisId=null;return data
  }
  try{
   if(fromDraft){
    const preflight=await api("/api/v4/packages/preflight",{package:draft});
    fullReport.preflight=preflight;
    if(fullCancelled)return;
    if(!preflight.already_approved&&!reviewWasVisible){
     packageReview.open=true;
     for(const id of ["ux-preview-reference","ux-preview-controls","ux-preview-provenance"]){const d=by(id);if(d)d.open=true}
     fullProgress.textContent="عرضنا المسألة للمراجعة بشكل مقروء. راجع المرجع والقيود والاختبارات المستقلة، ثم اضغط زر التحليل مرة أخرى.";
     fullReport.status="review_required";fullProgress.dataset.tone="warning";tabs?.select("input",true);packageReview.scrollIntoView({block:"center"});return
    }
    key=preflight.key;
    if(!preflight.already_approved){
     fullProgress.textContent="جارٍ اختبار المرجع الذي راجعته…";
     const approvalResult=await api("/api/v4/packages/approve",{package:draft,owner_reviewed:true});
     fullReport.approval=approvalResult;msg("approval",JSON.stringify(approvalResult.review,null,2));
     if(approvalResult.status!=="approved_by_owner"||approvalResult.key!==key){fullReport.status="approval_rejected";fullProgress.textContent="لم ينجح فحص المرجع؛ لن نشغّل الحل قبل تصحيح المسألة.";fullProgress.dataset.tone="warning";packageReview.open=true;tabs?.select("input",true);return}
    }
    await packages(key);fullTarget.value="approved";packageReview.open=false;newProblem.open=false;updateAvailable();updateFullConsent();
   }
   if(fullCancelled)return;
   fullReport.package_sha256=key;
   fullProgress.textContent="جارٍ البحث عن الأخطاء وجمع خطوات التنفيذ…";
   const analysis=await phase("analysis","/api/v4/analyze",{package_key:key,source:code,case:caseValue,trusted_local_source:true,
    capture_example:true,use_ai:useAI,...modelOptions,generator:by("generator").value,guided:by("guided").checked,spectrum:by("spectrum").checked,
    count:Number(by("count").value),reduce_calls:Number(by("reduce-count").value),session_seconds:Number(by("session-seconds").value)});
   if(!analysis)return;
   showRunReport(analysis);
   const observed=analysis.status==="observed_mismatch"?analysis:analysis.example_observation;
   const verdicts={observed_mismatch:"وُجدت حالة فشل",no_witness_found:"لم نجد خطأ في الحالات المجربة",inconclusive:"نتيجة غير حاسمة",oracle_unavailable:"تعذر الحكم بالمرجع",unstable:"تعذر تثبيت الشاهد",cancelled:"أُلغي الطلب"};
   fullValues.diagnosis.textContent=verdicts[analysis.status]||analysis.status;
   fullValues.diagnosis.parentElement.dataset.tone=analysis.status==="no_witness_found"?"positive":"warning";
   if(observed?.witness&&observed.student_graph){
    result=observed;sources={student:code,reference:observed.reference_source||""};side="student";index=0;show();
    fullValues.trace.textContent="تمت إعادة استخدام تتبع التحليل";
   }else fullValues.trace.textContent="لا تتوفر خطوات موثقة";
   if(fullCancelled||analysis.status==="cancelled")return;
   if(!observed?.witness?.case||!["ok","timeout"].includes(observed.witness.student?.status)){
    fullValues.timing.textContent="لا يتوفر مدخل أو تنفيذ صالح للقياس";
    fullReport.status="partial";fullProgress.textContent="اكتمل الجزء المتاح من التحليل؛ تعذر قياس الزمن دون تتبع.";fullProgress.dataset.tone="warning";return
   }
   fullProgress.textContent="جارٍ قياس زمن التشغيل الحقيقي على المدخل نفسه دون تتبع…";
   const measured=await phase("benchmark","/api/v4/benchmark",{package_key:key,case:observed.witness.case,source:code,trusted_local_source:true,repetitions:Number(by("timing-repetitions").value),seconds:Number(by("timing-seconds").value)});
   if(!measured)return;
   benchmarkResult=measured;showBenchmark();
   const stats=measured.points?.[0]?.summary;
   const wall=stats?.wall_ns?.median;
   if(Number.isFinite(wall)){
    fullValues.timing.replaceChildren(node("bdi","",(wall/1e6).toFixed(4)+" ms"),document.createTextNode(" · "),node("bdi","",stats.completed+"/"+stats.requested),document.createTextNode(" تشغيلات"));
   }else fullValues.timing.textContent="لم يكتمل قياس صالح للزمن";
   showRunReport(analysis); // Keep analysis report accessible; composite export contains both reports.
   fullReport.status=measured.stop_reason==="completed"&&stats?.completed===stats?.requested&&Number.isFinite(wall)?"completed":"partial";
   fullProgress.textContent=fullReport.status==="completed"?"اكتمل التحليل الشامل. اختر التبويب الذي تريد استكشافه.":"انتهى التحليل مع قياس جزئي أو غير متاح.";
   fullProgress.dataset.tone=fullReport.status==="completed"?"positive":"warning";
  }catch(e){
   fullReport.status="partial";fullReport.error=String(e.message||e);
   fullProgress.textContent="تعذر إكمال إحدى المراحل: "+fullReport.error;fullProgress.dataset.tone="warning";
   if(!fullReport.phases.length&&fromDraft){packageReview.open=true;author.open=true;authorForm.refresh();tabs?.select("input",true)}
  }finally{
   if(fullCancelled||fullReport.phases.some(x=>x.data.status==="cancelled"||x.data.stop_reason==="cancelled")){
    fullReport.status="cancelled";fullProgress.textContent="أُلغي التحليل؛ النتائج المكتملة قبل الإلغاء محفوظة.";fullProgress.dataset.tone="warning"
   }
   for(const v of Object.values(fullValues))if(v.textContent==="بانتظار التنفيذ")v.textContent="لم تُنفّذ";
   fullExport.hidden=!(fullReport.phases.length||fullReport.approval);analysisId=null;cancel.hidden=true;fullActive=false;setBusy(false);refreshModels().catch(()=>{})
  }
 };
 const originalJump=jumpToEvidence;jumpToEvidence=function(...args){tabs?.select("advanced",true);advancedResult.open=true;trace.open=true;originalJump(...args)};
 for(const id of ["ast-tree","profile-table"])by(id).addEventListener("click",e=>{if(e.target.closest("button"))trace.open=true},true);
 const originalShow=show;show=function(){
  originalShow();
  const manualResult=result.status==="manual_observation",profileResult=result.status==="profiled_execution";
  resultTitle.textContent=manualResult?"نتيجة تتبع البرنامج":result.reused_search_trace?"مثال من التنفيذ الذي تم اختباره":profileResult?"نتيجة قياس التنفيذ":"وجدنا حالة فشل قابلة للمراجعة";
  triplet.classList.toggle("ux-mismatch",result.status==="observed_mismatch"&&result.kind!=="exception");
  by("expected").parentElement.classList.add("ux-expected");
  by("actual").parentElement.classList.add("ux-actual");
  resultCaution.textContent=manualResult?"تتبع مدخل يدوي؛ لا يثبت صحة الحل ولا قانونية المدخل.":profileResult?"الزمن أثناء التتبع يصف تنفيذاً واحداً، وليس زمن المسابقة.":"هذه حالة فشل مرصودة؛ مواضع الاشتباه والفرضيات لا تثبت السبب الجذري.";
  advancedResult.open=mode!=="full";trace.open=true;comparison.open=false;profiling.open=profileResult;aiResults.open=Boolean(result.hypotheses?.length);
  const story=window.AlgoXRayStory.execution(result,(line,id)=>jumpToEvidence(line,id),()=>tabs?.select("execution",true));
  if(tabs)tabs.installStory(story);else storySlot.replaceChildren(story);
  if(!manualResult){
   by("actual").previousElementSibling.textContent="خرج برنامجك";
   by("expected").previousElementSibling.textContent=result.witness.judgment?.reference_output_is_example?"مثال لخرج مقبول":"الخرج المرجعي";
  }
  if(result.reused_search_trace)msg("ai-state","تم استخدام تتبع من البحث نفسه؛ لم يُطلب تشخيص AI إضافي لهذه الحالة.");
  raw.open=false;
  if(result.evidence_localization)by("localization-scope").textContent="هذه ترشيحات مبنية على الأدلة المتاحة، وليست احتمالاً معايراً أو إثباتاً للسبب الجذري.";
  if(!manualResult&&result.evidence_localization?.ranked?.length===0)localization.querySelector("h3").textContent="موضع الاشتباه (غير محدد)";
  else localization.querySelector("h3").textContent="مواضع تستحق المراجعة";
 };
 by("prepare-replay").addEventListener("click",()=>{
  if(!importedReport||by("trusted").checked)return;
  const op=importedReport.run_report.operation;
  if(op==="observe")setMode("understand");else if(op==="profile"){setMode("performance");profile.open=true}else setMode("diagnose");tabs?.select("input",true);
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
 tabs=window.AlgoXRayTabs.mount({
  main,intro,workspace,toolsPanel,results,fullPanel,fullProgress,cancel,benchPanel,benchDetails,advancedResult,reports,fullExport,footer,
  state:()=>({busy,fullActive,fullReport,result,reportHidden:by("run-report-panel").hidden}),
  stopTechnicalPlayback:()=>stopTracePlayback()
 });

})();
