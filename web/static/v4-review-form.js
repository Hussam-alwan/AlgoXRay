/* Human-supplied reference and independent tests. Parsing is only a projection
 * of the bounded grammar. Server preflight/owner review remain authoritative. */
window.AlgoXRayReviewForm=(()=>{
 const el=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e};
 const txt=(label,value,rows=3)=>{const wrap=el("label",label),input=el("textarea");input.dir="ltr";input.rows=rows;input.spellcheck=false;input.value=value??"";wrap.append(input);return {wrap,input}};
 function parse(m,raw){
  if(typeof raw!=="string"||new TextEncoder().encode(raw).length>16384)throw Error("حجم المدخل يتجاوز الحد المسموح.");
  if(!Array.isArray(m.fields)||!m.fields.length||m.fields.length>16)throw Error("قيود المسألة غير جاهزة.");
  const tokens=raw.trim()?raw.trim().split(/\s+/):[];let i=0;
  const take=()=>{if(i>=tokens.length)throw Error("المدخل ناقص بالنسبة إلى قيود المسألة.");return tokens[i++]};
  const integer=()=>{const token=take();if(!/^[+-]?[0-9]{1,16}$/.test(token))throw Error("توقعنا عدداً صحيحاً.");const n=Number(token);if(!Number.isSafeInteger(n))throw Error("العدد خارج النطاق المدعوم.");return n};
  const dim=(f,axis,c,cap)=>{
   const d=f[axis]??c[f[axis+"_from"]];
   if(!Number.isInteger(d)||d<0||d>cap)throw Error("طول أو بُعد غير صالح.");return d;
  };
  function body(){
   const c=Object.create(null);
   for(const f of m.fields){
    if(!f||typeof f.name!=="string"||! /^[a-z][a-z0-9_]{0,30}$/.test(f.name))throw Error("اسم حقل غير صالح.");
    if(f.kind==="int")c[f.name]=integer();
    else if(f.kind==="word")c[f.name]=take();
    else if(f.kind==="ints")c[f.name]=Array.from({length:dim(f,"length",c,m.schema_version===2?1000:100)},integer);
    else if(f.kind==="matrix")c[f.name]=Array.from({length:dim(f,"rows",c,32)},()=>Array.from({length:dim(f,"cols",c,32)},integer));
    else throw Error("نوع مدخل غير مدعوم في النموذج.");
   }
   return c;
  }
  let c;
  if(m.repeat){
   const t=integer();if(t<1||t>16)throw Error("عدد الحالات خارج النطاق المدعوم.");
   c={t,cases:Array.from({length:t},body)};
  }else c=body();
  if(i!==tokens.length)throw Error("توجد قيم إضافية لا تنتمي إلى صيغة المدخل.");
  return c;
 }
 function format(m,c){
  const body=c=>m.lines.map(row=>row.map(k=>{
   const v=c[k];return Array.isArray(v)?(Array.isArray(v[0])?v.map(r=>r.join(" ")).join("\n"):v.join(" ")):String(v);
  }).join(" ")).join("\n")+"\n";
  return m.repeat?String(c.t)+"\n"+c.cases.map(body).join(""):body(c);
 }
 function form(readPackage,writePackage,api,isBusy){
  const panel=el("div");panel.className="ux-human-review";
  const ref=txt("الحل المرجعي الذي راجعته","",5);ref.input.id="ux-reference-source";
  const note=el("p","أدخل حلّاً مرجعياً واختبارين على الأقل بنتائج تعرفها بشكل مستقل. لا تُستنتج النتائج من المرجع تلقائياً.");note.className="ux-description";
  const testList=el("div");testList.id="ux-control-form-list";
  let rows=[],manifestKey=null,baseline=null,dirty=false;
  const status=el("p");status.id="ux-control-form-status";status.setAttribute("role","status");status.className="ux-description";
  function addRow(stdin="",expected=""){
   if(rows.length>=8)return;
   const row=el("div");row.className="ux-human-test";
   const title=el("strong","اختبار مستقل");const input=txt("المدخل",stdin,2),output=txt("الخرج المتوقع",expected,2);
   const remove=el("button","حذف");remove.type="button";
   const item={row,input:input.input,output:output.input,remove};
   remove.onclick=()=>{if(isBusy()||rows.length<=2)return;rows=rows.filter(x=>x!==item);row.remove();dirty=true;syncButtons()};
   input.input.oninput=output.input.oninput=()=>{dirty=true};row.append(title,input.wrap,output.wrap,remove);testList.append(row);rows.push(item);syncButtons();
  }
  function syncButtons(){
   for(const r of rows)r.remove.disabled=isBusy()||rows.length<=2;
   extra.disabled=isBusy()||rows.length>=8;
  }
  const extra=el("button","إضافة اختبار");extra.type="button";extra.onclick=()=>{if(!isBusy()){addRow();dirty=true}};
  ref.input.oninput=()=>{dirty=true};
  const save=el("button","حفظ المرجع والاختبارات");save.type="button";save.className="ux-primary";save.id="ux-save-controls";
  save.onclick=async()=>{
   if(isBusy())return;
   let pkg;
   try{
    pkg=readPackage();
    if(JSON.stringify(pkg)!==baseline||JSON.stringify(pkg.manifest)!==manifestKey)throw Error("تغيّرت القيود. افتح نموذج المراجعة مرة أخرى.");
    if(!ref.input.value.trim())throw Error("أضف الحل المرجعي أولاً.");
    pkg.reference=ref.input.value;
    pkg.controls=rows.map(r=>{
     const c=parse(pkg.manifest,r.input.value);
     const raw=r.input.value.replace(/\r\n?/g,"\n");
     if(raw!==format(pkg.manifest,c)&&raw+"\n"!==format(pkg.manifest,c))
      throw Error("رتب المدخل بنفس أسطر المسألة وقيمها، دون فراغات إضافية. استخدم العقد التقني للحالات الخاصة.");
     return {case:c,expected:r.output.value};
    });
    // Pure validation. A successful preflight neither executes nor approves.
    const checked=await api(pkg);
    if(isBusy()||JSON.stringify(readPackage())!==baseline)throw Error("تغيّرت المسألة أثناء الفحص.");
    dirty=false;baseline=JSON.stringify(pkg);writePackage(pkg);
    status.textContent="حُفظت المدخلات والمرجع. راجع القيود والنتائج قبل التحليل؛ الفحص البنيوي ليس اعتماداً.";
   }catch(e){status.textContent=String(e.message||e)}
  };
  const reset=el("button","إلغاء التعديلات");reset.type="button";reset.onclick=()=>{if(!isBusy())refresh()};
  panel.append(note,ref.wrap,testList,extra,save,reset,status);
  function refresh(){
   let pkg;
   try{pkg=readPackage();if(!pkg?.manifest)throw Error()}catch(e){manifestKey=baseline=null;dirty=false;ref.input.value="";testList.replaceChildren();rows=[];save.disabled=true;status.textContent="جهّز قيود المسألة أولاً.";return}
   manifestKey=JSON.stringify(pkg.manifest);baseline=JSON.stringify(pkg);dirty=false;status.textContent="";
   ref.input.value=typeof pkg.reference==="string"?pkg.reference:"";
   testList.replaceChildren();rows=[];
   try{for(const c of (pkg.controls||[]).slice(0,8))addRow(format(pkg.manifest,c.case),c.expected)}
   catch(e){status.textContent="تعذر عرض بعض الحالات؛ راجع العقد التقني."}
   while(rows.length<2)addRow();
   syncButtons();save.disabled=isBusy();
  }
  function setBusy(v){ref.input.disabled=v;save.disabled=v||manifestKey===null;reset.disabled=v;for(const r of rows){r.input.disabled=v;r.output.disabled=v}syncButtons()}
  return {panel,refresh,setBusy,isDirty:()=>dirty};
 }
 return {form,parse,format};
})();
