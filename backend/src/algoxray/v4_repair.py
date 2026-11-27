"""Optional user-reviewed patch. Test success is not a proof of general correctness."""
import hashlib
from .v4_contracts import validate_package,serialize,generate,equal,digest
from .v4_isolation import execute_stdio,MAX_SOURCE
from .v4_provider import ProviderError
from .v4_engine import oracle
REPAIR_SCHEMA={"type":"object","properties":{"candidate":{"type":"string"},"rationale":{"type":"string"}},"required":["candidate","rationale"],"additionalProperties":False}
def propose_repair(provider,p,source,case):
    m=p["manifest"];serialize(m,case)
    result=provider.propose("repair",{"statement":m["statement"],"source":source,"counterexample":case,
        "instruction":"Propose complete Python stdin/stdout source, not a diff. Keep scope limited. Do not claim it passed tests."},REPAIR_SCHEMA)
    if type(result) is not dict or set(result)!={"candidate","rationale"} or type(result["candidate"]) is not str or not 0<len(result["candidate"].encode())<=MAX_SOURCE or type(result["rationale"]) is not str or len(result["rationale"])>1500:
        raise ProviderError("invalid_repair")
    return {**result,"status":"unreviewed_proposal","executed":False}

def verify_repair(p,source,candidate,case,seed=2027,count=4,run=execute_stdio):
    validate_package(p);m=p["manifest"]
    if type(count) is not int or not 1<=count<=8 or type(seed) is not int or not 0<=seed<=2**32-1:raise ValueError("Invalid repair budget")
    if type(source) is not str or type(candidate) is not str or not 0<len(candidate.encode())<=MAX_SOURCE or not 0<len(source.encode())<=MAX_SOURCE:raise ValueError("Invalid source")
    stdin=serialize(m,case)
    ref=oracle(p,stdin,lambda src,stdin,limit:run(src,stdin,trace_limit=limit))
    original=run(source,stdin,trace_limit=0)
    if ref["status"]!="ok" or not (original["status"]=="exception" or original["status"]=="ok" and not equal(m,original["stdout"],ref["stdout"])):
        return {"status":"original_witness_not_reproduced","checks":[]}
    cases=[("witness",case)]+[("owner_control",c["case"]) for c in p["controls"]]+[("generated_regression",c) for c in generate(m,seed,count)]
    checks=[];seen=set()
    for label,c in cases:
        key=digest(c)
        if key in seen:continue
        seen.add(key);stdin=serialize(m,c)
        ref=oracle(p,stdin,lambda src,stdin,limit:run(src,stdin,trace_limit=limit))
        if ref["status"]!="ok":
            checks.append({"kind":label,"case":c,"status":"oracle_unavailable"});break
        actual=run(candidate,stdin,trace_limit=0)
        ok=actual["status"]=="ok" and equal(m,actual["stdout"],ref["stdout"])
        checks.append({"kind":label,"case":c,"status":"match" if ok else "not_passed","expected":ref["stdout"],"actual":actual.get("stdout"),"execution_status":actual["status"]})
    return {"status":"passed_named_tests" if all(x["status"]=="match" for x in checks) else "not_passed_or_inconclusive",
            "checks":checks,"seed":seed,"package_sha256":digest(p),"original_sha256":hashlib.sha256(source.encode()).hexdigest(),
            "candidate_sha256":hashlib.sha256(candidate.encode()).hexdigest(),
            "scope":"Finite reviewed-reference regression cases; generated cases are not an independent research holdout. Original is unchanged."}
