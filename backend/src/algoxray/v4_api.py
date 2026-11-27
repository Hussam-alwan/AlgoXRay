"""Opt-in loopback author workbench; no public or automatic AI-code execution."""
import secrets, threading
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from .paths import ROOT
from .v4_contracts import PackageStore,validate_package
from .v4_engine import review,analyze_package
from .v4_provider import OllamaProvider,model_health

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
    count:int=Field(default=6,ge=1,le=12)
    seed:int=Field(default=2026,ge=0,le=2**32-1)
    case:dict|None=None

def router_for(require_loopback,token):
    router=APIRouter(prefix="/api/v4");lock=threading.Lock()
    store=PackageStore(ROOT/"results"/"v4-packages")
    def guard(request):
        require_loopback(request)
        if not secrets.compare_digest(request.headers.get("x-algoxray-token",""),token):raise HTTPException(403,"Local author session required")
    @router.get("/health")
    def health(request:Request):
        require_loopback(request)
        return {"status":"experimental","model":model_health(),"public_execution":False,"guest_trace_authenticated":False}
    @router.get("/packages")
    def packages(request:Request):
        require_loopback(request);return store.list()
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
    @router.post("/analyze")
    def analyze(body:Run,request:Request):
        guard(request)
        if not body.trusted_local_source:raise HTTPException(403,"Confirm local source review")
        if not lock.acquire(blocking=False):raise HTTPException(409,"V4 busy")
        try:
            p=store.load(body.package_key)
            return analyze_package(p,body.source,count=body.count,seed=body.seed,case=body.case,provider=OllamaProvider() if body.use_ai else None)
        except (ValueError,OSError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:lock.release()
    return router
