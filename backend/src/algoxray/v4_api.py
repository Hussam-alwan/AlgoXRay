"""Opt-in loopback author workbench; no public or automatic AI-code execution."""
import os, secrets, threading
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from .paths import ROOT
from .v4_contracts import PackageStore,validate_package,validate_manifest
from .v4_engine import review,analyze_package
from .v4_provider import OllamaProvider,model_health,ProviderError
from .v4_repair import propose_repair,verify_repair
from .v4_gemini import provider_for,provider_status

class Draft(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    statement:str=Field(min_length=1,max_length=8000)
    model:str="qwen2.5-coder:7b"
    cloud_consent:bool=False
class Repair(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    package_key:str
    source:str=Field(min_length=1,max_length=32768)
    case:dict
    candidate:str|None=Field(default=None,min_length=1,max_length=32768)
    reviewed:bool=False
    model:str="qwen2.5-coder:7b"
    cloud_consent:bool=False
class Approve(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    package:dict
    owner_reviewed:bool=False
class Run(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    package_key:str
    source:str=Field(min_length=1,max_length=32768)
    trusted_local_source:bool=False
    use_ai:bool=False
    model:str="qwen2.5-coder:7b"
    cloud_consent:bool=False
    count:int=Field(default=6,ge=1,le=12)
    seed:int=Field(default=2026,ge=0,le=2**32-1)
    case:dict|None=None
    analysis_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')

def router_for(require_loopback,token):
    router=APIRouter(prefix="/api/v4");lock=threading.Lock();active={};active_lock=threading.Lock()
    store=PackageStore(os.getenv("ALGOXRAY_V4_PACKAGE_STORE") or ROOT/"results"/"v4-packages")
    def guard(request):
        require_loopback(request)
        if not secrets.compare_digest(request.headers.get("x-algoxray-token",""),token):raise HTTPException(403,"Local author session required")
    @router.get("/health")
    def health(request:Request):
        require_loopback(request)
        return {"status":"experimental","model":model_health(),"gemini":provider_status(),"public_execution":False,"guest_trace_authenticated":False}
    def select_provider(model,consent):
        try:return provider_for(model,consent)
        except ProviderError as exc:raise HTTPException(403 if str(exc)=="cloud_consent_required" else 422,str(exc)) from None
    @router.get("/packages")
    def packages(request:Request):
        require_loopback(request);return store.list()
    @router.post("/packages/draft")
    def draft(body:Draft,request:Request):
        guard(request)
        schema={"type":"object","properties":{"manifest":{"type":"object","properties":{"id":{"type":"string"},"title":{"type":"string"},"statement":{"type":"string"},"fields":{"type":"array","items":{"type":"object"}},"lines":{"type":"array","items":{"type":"array","items":{"type":"string"}}},"output":{"enum":["tokens","exact"]}},"required":["id","title","statement","fields","lines","output"],"additionalProperties":False}},"required":["manifest"],"additionalProperties":False}
        instructions="Draft a bounded input grammar. Fields are ordered: {name,kind:int,min,max}; {name,kind:word,min,max,alphabet} where min/max are length; {name,kind:ints,min,max,length} or length_from previous int field. lines is a list of rows of field names in original order. Do not invent constraints; return no manifest if unsupported."
        try:
            provider=select_provider(body.model,body.cloud_consent)
            r=provider.propose("contract_draft",{"statement":body.statement,"grammar":instructions},schema)
            if set(r)!={"manifest"}:raise ValueError("Invalid draft envelope")
            m=validate_manifest(r["manifest"])
            return {"status":"draft_unreviewed","manifest":m,"model":body.model,"usage":getattr(provider,"usage",{}),"warning":"Check against original problem; supply independently reviewed reference and controls."}
        except ProviderError as exc:raise HTTPException(422,str(exc)) from None
        except (ValueError,TypeError,KeyError):raise HTTPException(422,"Unsupported or invalid draft; use manual authoring")
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
            provider=select_provider(body.model,body.cloud_consent)
            return {**propose_repair(provider,store.load(body.package_key),body.source,body.case),"model":body.model,"usage":getattr(provider,"usage",{})}
        except ProviderError as exc:raise HTTPException(422,str(exc)) from None
        except (ValueError,OSError):raise HTTPException(422,"Proposal invalid")
    @router.post("/repair/verify")
    def repair_verify(body:Repair,request:Request):
        guard(request)
        if not body.reviewed or body.candidate is None:raise HTTPException(403,"Review candidate before execution")
        if not lock.acquire(blocking=False):raise HTTPException(409,"V4 busy")
        try:return verify_repair(store.load(body.package_key),body.source,body.candidate,body.case)
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
        provider=select_provider(body.model,body.cloud_consent) if body.use_ai else None
        if not lock.acquire(blocking=False):raise HTTPException(409,"V4 busy")
        c=threading.Event()
        if body.analysis_id:
            with active_lock:active[body.analysis_id]=c
        try:
            p=store.load(body.package_key)
            return analyze_package(p,body.source,count=body.count,seed=body.seed,case=body.case,provider=provider,cancel=c)
        except (ValueError,OSError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:
            if body.analysis_id:
                with active_lock:active.pop(body.analysis_id,None)
            lock.release()
    return router
