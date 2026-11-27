"""Optional user-reviewed patch. Test success is not a proof of general correctness."""
import hashlib,difflib,json
from pathlib import Path
from .v4_contracts import validate_package,serialize,generate,equal,digest
from .v4_isolation import execute_stdio,MAX_SOURCE
from .v4_provider import ProviderError
from .v4_engine import oracle
from .v4_checker import judge_output
from .v4_shrinking import failure_signature
from .v4_run_report import RunLedger,BudgetExhausted
REPAIR_SCHEMA={"type":"object","properties":{"candidate":{"type":"string"},"rationale":{"type":"string"}},"required":["candidate","rationale"],"additionalProperties":False}
def propose_repair(provider,p,source,case):
    m=p["manifest"];serialize(m,case)
    result=provider.propose("repair",{"statement":m["statement"],"source":source,"counterexample":case,
        "instruction":"Propose complete Python stdin/stdout source, not a diff. Keep scope limited. Do not claim it passed tests."},REPAIR_SCHEMA)
    if type(result) is not dict or set(result)!={"candidate","rationale"} or type(result["candidate"]) is not str or not 0<len(result["candidate"].encode())<=MAX_SOURCE or type(result["rationale"]) is not str or len(result["rationale"])>1500:
        raise ProviderError("invalid_repair")
    return {**result,"status":"unreviewed_proposal","executed":False,"diff":"".join(difflib.unified_diff(source.splitlines(keepends=True),result["candidate"].splitlines(keepends=True),fromfile="original",tofile="candidate"))}

def verify_repair(p,source,candidate,case,seed=2027,count=4,run=execute_stdio,*,original_case=None,cancel=None,run_id=None):
    if type(candidate) is not str or type(source) is not str:raise ValueError("Invalid repair source")
    ledger=RunLedger("repair",source,package=p,run_id=run_id,session_seconds=240,max_executions=60,
        parameters={"case":case,"original_case":original_case,"seed":seed,"count":count,"candidate_sha256":hashlib.sha256(candidate.encode()).hexdigest()})
    try:return _verify_repair(p,source,candidate,case,seed,count,run,original_case,cancel,ledger)
    except BudgetExhausted as exc:return ledger.finish({"status":"not_passed_or_inconclusive","stop_reason":str(exc),"scope":"Budget exhausted before all named checks completed."},stop_reason=str(exc))

def _verify_repair(p,source,candidate,case,seed,count,run,original_case,cancel,ledger):
    ledger.enter("validation")
    validate_package(p);m=p["manifest"]
    if type(count) is not int or not 1<=count<=8 or type(seed) is not int or not 0<=seed<=2**32-1:raise ValueError("Invalid repair budget")
    if type(source) is not str or type(candidate) is not str or not 0<len(candidate.encode())<=MAX_SOURCE or not 0<len(source.encode())<=MAX_SOURCE:raise ValueError("Invalid source")
    supplied=[("witness",case)]
    if original_case is not None and digest(original_case)!=digest(case):supplied.append(("original_witness",original_case))
    checks=[];reproductions=[];executions=0
    def invoke(src,stdin,limit,role="reference"):
        nonlocal executions
        if cancel is not None and cancel.is_set():return {"status":"cancelled"}
        result=ledger.execute(run,role,src,stdin,trace_limit=limit,**({"cancel":cancel} if cancel is not None else {}))
        executions+=1
        return result
    def check_source(src,c,ref,role):
        actual=invoke(src,serialize(m,c),0,role=role)
        judgment=judge_output(p,c,actual.get("stdout"),ref.get("stdout")) if actual["status"]=="ok" else None
        return actual,judgment
    named=supplied+[("owner_control",c["case"]) for c in p["controls"]]+[("generated_regression",c) for c in generate(m,seed,count)]
    cases={}
    for label,c in named:
        serialize(m,c)
        key=digest(c)
        if key not in cases:cases[key]={"case":c,"labels":[]}
        cases[key]["labels"].append(label)
    metadata={"version":2,"seed":seed,"package_sha256":digest(p),
              "original_sha256":hashlib.sha256(source.encode()).hexdigest(),
              "candidate_sha256":hashlib.sha256(candidate.encode()).hexdigest(),
              "suite_sha256":digest({"version":2,"package":digest(p),"seed":seed,"cases":list(cases.values())}),
              "suite_name":"witnesses_owner_controls_generated_regression","candidate_source":candidate,
              "planned_cases":len(cases),"witness_reproductions":reproductions,
              "scope":"Finite reviewed-reference regression cases; generated cases are not an independent research holdout. Original is unchanged."}
    def finish(status):
        return ledger.finish({**metadata,"status":status,"checks":checks,"executions":executions})
    # Re-establish both submitted witnesses before any candidate runs. Reuse
    # the validated reference results for these particular cases.
    refs={}
    ledger.partial={"checks":checks,"witness_reproductions":reproductions}
    ledger.enter("reproduce")
    for label,c in supplied:
        stdin=serialize(m,c)
        ref=oracle(p,stdin,invoke,case=c)
        if ref["status"]=="cancelled":return finish("cancelled")
        if ref["status"]!="ok":
            reproductions.append({"kind":label,"case":c,"status":"oracle_unavailable"})
            return finish("original_witness_not_reproduced")
        original,judgment=check_source(source,c,ref,"original")
        if original["status"]=="cancelled":return finish("cancelled")
        kind="exception" if original["status"]=="exception" else "wrong_answer" if judgment and judgment["status"]=="rejected" else "not_reproduced"
        reproduced=kind in ("exception","wrong_answer")
        reproductions.append({"kind":label,"case":c,"status":"reproduced" if reproduced else "not_reproduced",
                              "failure_signature":failure_signature({"kind":kind,"student":original}),
                              "execution_status":original["status"],"judgment":judgment,
                              "expected":ref.get("stdout"),"actual":original.get("stdout")})
        if not reproduced:return finish("original_witness_not_reproduced")
        refs[digest(c)]=ref
    ledger.enter("regression")
    for key,row in cases.items():
        label=row["labels"][0];c=row["case"]
        ref=refs.get(key) or oracle(p,serialize(m,c),invoke,case=c)
        if ref["status"]=="cancelled":return finish("cancelled")
        if ref["status"]!="ok":
            checks.append({"kind":label,**row,"status":"oracle_unavailable"});break
        actual,judgment=check_source(candidate,c,ref,"candidate")
        if actual["status"]=="cancelled":return finish("cancelled")
        status="match" if judgment and judgment["status"]=="accepted" else "oracle_unavailable" if judgment and judgment["status"]=="unavailable" else "not_passed"
        checks.append({"kind":label,**row,"status":status,"expected":ref.get("stdout"),"actual":actual.get("stdout"),
                       "execution_status":actual["status"],"judgment":judgment})
        if status=="oracle_unavailable":break
    return finish("passed_named_tests" if len(checks)==len(cases) and all(x["status"]=="match" for x in checks) else "not_passed_or_inconclusive")

class RepairStore:
    """Local immutable verified-attempt history, not proof or auto-acceptance."""
    def __init__(self,root):self.root=Path(root)
    def save(self,package_key,source,candidate,result):
        record={"package_key":package_key,"source":source,"candidate":candidate,"result":result}
        key=digest(record);self.root.mkdir(parents=True,exist_ok=True)
        target=self.root/(key+".json")
        try:
            with target.open("x",encoding="utf-8") as f:json.dump(record,f,ensure_ascii=True)
        except FileExistsError:
            if digest(self.load(key))!=key:raise ValueError("Repair history hash mismatch")
        return key
    def load(self,key):
        import re
        if type(key) is not str or not re.fullmatch("[0-9a-f]{64}",key):raise ValueError("Invalid repair history key")
        p=self.root/(key+".json")
        if not p.is_file():raise ValueError("Unknown repair history")
        r=json.loads(p.read_text(encoding="utf-8"))
        if digest(r)!=key:raise ValueError("Repair history hash mismatch")
        return r
    def list(self,package_key):
        rows=[]
        for p in sorted(self.root.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True)[:100]:
            try:
                r=self.load(p.stem)
                if r["package_key"]==package_key:rows.append({"key":p.stem,"status":r["result"]["status"],"candidate_sha256":r["result"].get("candidate_sha256")})
            except (OSError,ValueError,KeyError):continue
        return rows
