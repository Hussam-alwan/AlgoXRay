"""Opt-in loopback author workbench; no public or automatic AI-code execution."""
import os, secrets, threading
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from .paths import ROOT
from .v4_contracts import PackageStore,validate_package,validate_manifest
from .v4_engine import review,analyze_package
from .v4_provider import OllamaProvider,model_health,ProviderError
from .v4_repair import propose_repair,verify_repair,RepairStore
from .v4_gemini import provider_for,provider_status
from .v4_openrouter import status as openrouter_status
from .v4_groq import status as groq_status
from .v4_authoring import import_problem,draft_reference
from .v4_contracts import serialize,equal
from .v4_engine import oracle
from .v4_isolation import execute_stdio
from .v4_graph import observed_graph
from .v4_profiling import attach_profile
from .v4_cache import CACHE
from .v4_qwen_cloud import status as qwen_status
from .v4_draft_review import review_draft,field_schema
from .v4_package_audit import audit_package
from .v4_loop_observations import with_loops
from .v4_diagnostic_context import diagnose_execution
from .v4_execution_diagnostics import execution_diagnostics

class Draft(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    statement:str=Field(min_length=1,max_length=8000)
    model:str="qwen2.5-coder:7b"
    cloud_consent:bool=False
    use_cache:bool=False
class ImportProblem(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    url:str=Field(min_length=1,max_length=250)
class DraftReference(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    manifest:dict
    model:str="qwen2.5-coder:7b"
    cloud_consent:bool=False
    use_cache:bool=False
class Repair(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    package_key:str
    source:str=Field(min_length=1,max_length=32768)
    case:dict
    candidate:str|None=Field(default=None,min_length=1,max_length=32768)
    reviewed:bool=False
    model:str="qwen2.5-coder:7b"
    cloud_consent:bool=False
    use_cache:bool=False
class Approve(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    package:dict
    owner_reviewed:bool=False
class Audit(Approve):
    max_cases:int=Field(default=16,ge=2,le=32)
class Run(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    package_key:str
    source:str=Field(min_length=1,max_length=32768)
    trusted_local_source:bool=False
    use_ai:bool=False
    model:str="qwen2.5-coder:7b"
    cloud_consent:bool=False
    use_cache:bool=False
    generator:str="boundary_random"
    guided:bool=False
    spectrum:bool=False
    count:int=Field(default=6,ge=1,le=12)
    seed:int=Field(default=2026,ge=0,le=2**32-1)
    case:dict|None=None
    analysis_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')

def router_for(require_loopback,token):
    router=APIRouter(prefix="/api/v4");lock=threading.Lock();active={};active_lock=threading.Lock()
    store=PackageStore(os.getenv("ALGOXRAY_V4_PACKAGE_STORE") or ROOT/"results"/"v4-packages")
    repairs=RepairStore(os.getenv("ALGOXRAY_V4_REPAIR_STORE") or (store.root.parent/(store.root.name+"-repairs")))
    def guard(request):
        require_loopback(request)
        if not secrets.compare_digest(request.headers.get("x-algoxray-token",""),token):raise HTTPException(403,"Local author session required")
    @router.get("/health")
    def health(request:Request):
        require_loopback(request)
        return {"status":"experimental","model":model_health(),"gemini":provider_status(),"openrouter":openrouter_status(),"groq":groq_status(),"qwen_cloud":qwen_status(),"cache":CACHE.status(),"public_execution":False,"guest_trace_authenticated":False}
    def select_provider(model,consent,cache=False):
        try:return provider_for(model,consent,**({"use_cache":True} if cache else {}))
        except ProviderError as exc:raise HTTPException(403 if str(exc)=="cloud_consent_required" else 422,str(exc)) from None
    @router.post("/cache/clear")
    def clear_cache(request:Request):
        guard(request);CACHE.clear()
        return {"status":"cleared",**CACHE.status()}
    @router.get("/packages")
    def packages(request:Request):
        require_loopback(request);return store.list()
    @router.post("/packages/draft")
    def draft(body:Draft,request:Request):
        guard(request)
        schema={"type":"object","properties":{"manifest":{"type":"object","properties":{"id":{"type":"string"},"title":{"type":"string"},"statement":{"type":"string"},"fields":{"type":"array","items":{"type":"object","properties":{"name":{"type":"string"},"kind":{"type":"string","enum":["int","word","ints","matrix"]},"min":{"type":"integer"},"max":{"type":"integer"},"alphabet":{"type":"string"},"length":{"type":"integer"},"length_from":{"type":"string"},"rows":{"type":"integer"},"rows_from":{"type":"string"},"cols":{"type":"integer"},"cols_from":{"type":"string"}},"required":["name","kind","min","max"],"additionalProperties":False}},"lines":{"type":"array","items":{"type":"array","items":{"type":"string"}}},"output":{"type":"string","enum":["tokens","exact"]}},"required":["id","title","statement","fields","lines","output"],"additionalProperties":False}},"required":["manifest"],"additionalProperties":False}
        schema["properties"]["manifest"]["properties"]["fields"]["items"]=field_schema()
        schema["properties"]["evidence"]={"type":"array","maxItems":48,"items":{"type":"object","properties":{"field":{"type":"string"},"attribute":{"type":"string","enum":["min","max","alphabet","length","length_from","rows","rows_from","cols","cols_from"]},"quote":{"type":"string","minLength":1,"maxLength":600}},"required":["field","attribute","quote"],"additionalProperties":False}}
        schema["properties"]["unresolved"]={"type":"array","maxItems":16,"items":{"type":"string","minLength":1,"maxLength":400}}
        schema["required"]=["manifest","evidence","unresolved"]
        instructions='Draft a bounded input grammar. Fields are ordered: {name,kind:int,min,max}; {name,kind:word,min,max,alphabet} where min/max are length; {name,kind:ints,min,max,length} or length_from previous int field. matrix fields have min,max, rows or rows_from, cols or cols_from (1..32 per dimension); matrix must occupy its own line group. lines is a list of rows of field names in original order. Example for one integer n between 1 and 9: fields=[{"name":"n","kind":"int","min":1,"max":9}], lines=[["n"]], output="tokens". Omit irrelevant optional fields: alphabet only for word; length or length_from only for ints; rows/cols dimensions only for matrix. id must be lowercase ASCII letters/digits/underscore. Never invent constraints. A list whose size is an earlier input variable MUST use length_from, never a fixed length. For example: fields=[{"name":"size","kind":"int","min":1,"max":20},{"name":"values","kind":"ints","min":0,"max":1000,"length_from":"size"}], lines=[["size"],["values"]]. For every numeric bound, alphabet and size dependency return an evidence entry {field,attribute,quote} with an exact quotation from the supplied statement. List unrepresentable or ambiguous requirements in unresolved. Do not replace original large limits with convenient smaller ones.'
        r=None
        try:
            provider=select_provider(body.model,body.cloud_consent,body.use_cache)
            r=provider.propose("contract_draft",{"statement":body.statement,"grammar":instructions},schema)
            if not {"manifest"}<=set(r)<={"manifest","evidence","unresolved"}:raise ValueError("Invalid draft envelope")
            if type(r["manifest"]) is not dict:raise ValueError("Invalid manifest")
            m=validate_manifest({**r["manifest"],"statement":body.statement})
            constraint_review=review_draft(body.statement,m,r.get("evidence",[]),r.get("unresolved",[]))
            return {"status":"draft_unreviewed","manifest":m,"provenance":constraint_review["provenance"],"constraint_review":constraint_review,"model":body.model,"usage":getattr(provider,"usage",{}),"warning":"Check against original problem; supply independently reviewed reference and controls."}
        except ProviderError as exc:raise HTTPException(422,str(exc)) from None
        except (ValueError,TypeError,KeyError) as exc:raise HTTPException(422,{"message":"Unsupported or invalid draft; review and edit manually","reason":str(exc)[:160],"draft":r if type(r) is dict else None}) from None
    @router.post("/packages/import")
    def problem_import(body:ImportProblem,request:Request):
        guard(request)
        try:return import_problem(body.url)
        except ValueError as exc:raise HTTPException(422,str(exc)) from None
    @router.post("/packages/reference")
    def reference_draft(body:DraftReference,request:Request):
        guard(request)
        try:return draft_reference(select_provider(body.model,body.cloud_consent,body.use_cache),body.manifest)
        except ProviderError as exc:raise HTTPException(422,str(exc)) from None
        except ValueError as exc:raise HTTPException(422,str(exc)) from None
    @router.post("/packages/audit")
    def package_audit(body:Audit,request:Request):
        guard(request)
        if not body.owner_reviewed:raise HTTPException(403,"Review references before audit execution")
        if not lock.acquire(blocking=False):raise HTTPException(409,"V4 busy")
        try:return audit_package(body.package,body.max_cases)
        except (ValueError,OSError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:lock.release()
    @router.post("/packages/approve")
    def approve(body:Approve,request:Request):
        guard(request)
        if not body.owner_reviewed:raise HTTPException(403,"Independent owner review required")
        if not lock.acquire(blocking=False):raise HTTPException(409,"V4 busy")
        try:
            validate_package(body.package)
            result=review(body.package)
            if not result["passed"]:return {"status":"rejected","review":result}
            return {"status":"approved_by_owner","key":store.save(body.package),"review":result}
        except (ValueError,OSError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:lock.release()
    @router.post("/repair/propose")
    def repair_propose(body:Repair,request:Request):
        guard(request)
        try:
            provider=select_provider(body.model,body.cloud_consent,body.use_cache)
            return {**propose_repair(provider,store.load(body.package_key),body.source,body.case),"model":body.model,"usage":getattr(provider,"usage",{})}
        except ProviderError as exc:raise HTTPException(422,str(exc)) from None
        except (ValueError,OSError):raise HTTPException(422,"Proposal invalid")
    @router.get("/repairs/{package_key}")
    def repair_history(package_key:str,request:Request):
        require_loopback(request)
        try:store.load(package_key);return repairs.list(package_key)
        except (ValueError,OSError):raise HTTPException(422,"Unknown package") from None
    @router.get("/repair/version/{key}")
    def repair_version(key:str,request:Request):
        require_loopback(request)
        try:return repairs.load(key)
        except (ValueError,OSError):raise HTTPException(422,"Unknown repair version") from None
    @router.post("/repair/verify")
    def repair_verify(body:Repair,request:Request):
        guard(request)
        if not body.reviewed or body.candidate is None:raise HTTPException(403,"Review candidate before execution")
        if not lock.acquire(blocking=False):raise HTTPException(409,"V4 busy")
        try:
            result=verify_repair(store.load(body.package_key),body.source,body.candidate,body.case)
            return {**result,"history_key":repairs.save(body.package_key,body.source,body.candidate,result)}
        except (ValueError,OSError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:lock.release()
    @router.post("/analysis/{analysis_id}/cancel")
    def cancel_analysis(analysis_id:str,request:Request):
        guard(request)
        with active_lock:
            c=active.get(analysis_id)
            if c is None:raise HTTPException(404,"No active V4 analysis")
            c.set()
        return {"status":"cancellation_requested"}
    @router.post("/analyze")
    def analyze(body:Run,request:Request):
        guard(request)
        if not body.trusted_local_source:raise HTTPException(403,"Confirm local source review")
        provider=select_provider(body.model,body.cloud_consent,body.use_cache) if body.use_ai else None
        if not lock.acquire(blocking=False):raise HTTPException(409,"V4 busy")
        c=threading.Event()
        if body.analysis_id:
            with active_lock:active[body.analysis_id]=c
        try:
            p=store.load(body.package_key)
            return analyze_package(p,body.source,count=body.count,seed=body.seed,case=body.case,provider=provider,cancel=c,generator=body.generator,guided=body.guided,spectrum=body.spectrum)
        except (ValueError,OSError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:
            if body.analysis_id:
                with active_lock:active.pop(body.analysis_id,None)
            lock.release()
    @router.post("/profile")
    def profile(body:Run,request:Request):
        guard(request)
        if not body.trusted_local_source:raise HTTPException(403,"Confirm local source review")
        provider=select_provider(body.model,body.cloud_consent,body.use_cache) if body.use_ai else None
        if not lock.acquire(blocking=False):raise HTTPException(409,"V4 busy")
        c=threading.Event()
        if body.analysis_id:
            with active_lock:active[body.analysis_id]=c
        try:
            p=store.load(body.package_key)
            case=body.case if body.case is not None else p["controls"][0]["case"]
            stdin=serialize(p["manifest"],case)
            def run(src,stdin,limit):
                return execute_stdio(src,stdin,trace_limit=limit,cancel=c)
            ref=oracle(p,stdin,run,256)
            if ref["status"]=="cancelled":return {"status":"cancelled"}
            if ref["status"]!="ok":return {"status":"oracle_unavailable","reference":ref}
            student=run(body.source,stdin,256)
            if student["status"]=="cancelled":return {"status":"cancelled"}
            matches=student["status"]=="ok" and equal(p["manifest"],student["stdout"],ref["stdout"])
            witness=dict(case=case,stdin=stdin,student=student,reference=ref)
            diagnosis=diagnose_execution(p,body.source,witness,provider,cancel=c)
            if c.is_set():return {"status":"cancelled"}
            return dict(status="profiled_execution",kind="match" if matches else student["status"] if student["status"]!="ok" else "output_difference",
                package_sha256=body.package_key,student_source=body.source,reference_source=p["reference"],
                witness=witness,replay_count=0,attempts=1,
                student_graph=with_loops(attach_profile(observed_graph(student.get("events",[]),body.source),student),body.source,student),
                reference_graph=with_loops(attach_profile(observed_graph(ref.get("events",[]),p["reference"]),ref),p["reference"],ref),
                **diagnosis,execution_diagnostics=execution_diagnostics(body.source,student),
                scope="One instrumented input, no search or replay claim. Timing is not judge runtime or complexity proof.")
        except (ValueError,OSError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:
            if body.analysis_id:
                with active_lock:active.pop(body.analysis_id,None)
            lock.release()
    return router
