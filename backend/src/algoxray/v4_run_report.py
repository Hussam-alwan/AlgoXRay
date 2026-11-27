"""Versioned local run metadata; observations, not authenticated proof."""
import hashlib,time,uuid,sys,platform
from pathlib import Path
from .v4_contracts import digest

VERSION=1
STAGES={
    "analysis":("validation","search","guided_search","shrink","replay","spectrum","structure","diagnosis","guided_confirmation"),
    "profile":("validation","reference","student","structure","diagnosis"),
    "observe":("validation","student","structure"),
    "benchmark":("validation","measurement"),
    "repair":("validation","reproduce","regression"),
}
class BudgetExhausted(RuntimeError):pass
def sha(text):return hashlib.sha256(text.encode("utf-8")).hexdigest()

class RunLedger:
    def __init__(self,operation,source,*,package=None,parameters=None,run_id=None,session_seconds=240,max_executions=200,clock=time.monotonic):
        self.operation=operation;self.source=source;self.package=package
        self.parameters=parameters or {};self.id=run_id or uuid.uuid4().hex
        self.session_seconds=session_seconds;self.max_executions=max_executions
        self.clock=clock;self.started=clock();self.current=None;self.stage_start=None
        self.stages={name:{"name":name,"status":"not_run","elapsed_ms":0.0,"executions":0,"visits":0} for name in STAGES[operation]}
        self.workers=[];self.inputs=set();self.partial=None;self.pair_attempts=0
        self.engine_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('v4_*.py'))}
    def elapsed(self):return round((self.clock()-self.started)*1000,3)
    def check(self,*,worker=False):
        if self.elapsed()>=self.session_seconds*1000:raise BudgetExhausted("session_wall_budget_exhausted")
        if worker and len(self.workers)>=self.max_executions:raise BudgetExhausted("physical_execution_budget_exhausted")
    def close_stage(self,status="completed"):
        if self.current is None:return
        row=self.stages[self.current]
        row["elapsed_ms"]=round(row["elapsed_ms"]+(self.clock()-self.stage_start)*1000,3)
        row["status"]=status;self.current=None
    def enter(self,name):
        self.close_stage()
        row=self.stages[name];row["status"]="running";row["visits"]+=1
        self.current=name;self.stage_start=self.clock()
    def skip(self,name,reason):
        if self.stages[name]["status"]=="not_run":self.stages[name].update(status="skipped",reason=reason)
    def execute(self,run,role,source,stdin,**kwargs):
        self.check(worker=True)
        started=self.clock()
        row={"number":len(self.workers)+1,"stage":self.current,"role":role,
             "source_sha256":sha(source),"input_sha256":sha(stdin),
             "requested_mode":kwargs.get("mode","trace_profile"),
             "seconds":kwargs.get("seconds",1.0),"trace_limit":kwargs.get("trace_limit",128)}
        self.workers.append(row);self.inputs.add(row["input_sha256"])
        if self.current:self.stages[self.current]["executions"]+=1
        try:
            r=run(source,stdin,**kwargs)
            row.update(status=r.get("status","unknown"),cleanup_confirmed=r.get("cleanup_confirmed"),
                       image_id=r.get("image_id"),host_elapsed_ms=r.get("elapsed_ms"))
            return r
        except Exception:
            row["status"]="worker_call_failed";raise
        finally:row["call_ms"]=round((self.clock()-started)*1000,3)
    def finish(self,result,*,stop_reason=None):
        stopped=stop_reason or result.get("stop_reason") or result.get("status","unknown")
        interrupted=stopped in ("cancelled","oracle_unavailable","inconclusive","unstable","session_wall_budget_exhausted",
                                "physical_execution_budget_exhausted","session_budget_exhausted","worker_call_failed","original_witness_not_reproduced")
        self.close_stage("partial" if interrupted else "completed")
        package_hash=digest(self.package) if self.package else None
        report={"version":VERSION,"run_id":self.id,"operation":self.operation,
                "source_sha256":sha(self.source),"package_sha256":package_hash,
                "spec_version":self.package["manifest"].get("schema_version",1) if self.package else None,
                "parameters":self.parameters,"status":result.get("status"),"stop_reason":stopped,
                "elapsed_ms":self.elapsed(),"physical_executions":len(self.workers),
                "distinct_worker_inputs":len(self.inputs),"pair_attempts":result.get("attempts",self.pair_attempts),
                "engine_source_files_sha256":digest(self.engine_files),
                "host_python":platform.python_version(),"host_system":platform.system(),
                "limits":{"session_wall_seconds":self.session_seconds,"max_worker_calls":self.max_executions,
                          "enforcement":"Checked between calls; in-flight calls and cleanup may finish after the boundary."},
                "stages":list(self.stages.values()),"workers":self.workers,
                "image_ids":sorted({r["image_id"] for r in self.workers if type(r.get("image_id")) is str}),
                "scope":"Local observational report. Hashes identify content, not authenticity. Imported reports never grant execution approval."}
        if self.package:report["manifest_sha256"]=digest(self.package["manifest"])
        if interrupted and self.partial is not None and "witness" not in result and "checks" not in result:
            result={**result,"partial_observation":self.partial}
        return {**result,"analysis_id":self.id,"student_source":result.get("student_source",self.source),
                "package_sha256":result.get("package_sha256",package_hash),"run_report":report}
