"""Bounded observational debugging for approved stdio packages. No universal correctness claim."""
import time
from .v4_contracts import validate_package,serialize,generate,smaller,equal,digest
from .v4_isolation import execute_stdio
from .v4_graph import observed_graph
from .v4_provider import OllamaProvider,DIAGNOSIS_SCHEMA,check_hypotheses,ProviderError

def review(p,run=execute_stdio):
    validate_package(p);m=p["manifest"];checks=[]
    for c in p["controls"]:
        r=run(p["reference"],serialize(m,c["case"]),trace_limit=0)
        checks.append({"case":c["case"],"status":r["status"],"matches":r["status"]=="ok" and equal(m,r["stdout"],c["expected"])})
    return {"passed":all(x["matches"] for x in checks),"checks":checks,"limitation":"Finite owner-supplied controls, not proof of reference correctness."}

def analyze_package(p,source,seed=2026,count=6,reduce_calls=3,case=None,provider=None,run=execute_stdio):
    validate_package(p);m=p["manifest"]
    if type(count) is not int or not 1<=count<=12 or type(reduce_calls) is not int or not 0<=reduce_calls<=6: raise ValueError("Invalid analysis budget")
    if type(seed) is not int or not 0<=seed<=2**32-1: raise ValueError("Invalid seed")
    start=time.monotonic(); attempts=0
    def pair(c,trace_limit=0):
        nonlocal attempts
        attempts+=1
        stdin=serialize(m,c)
        ref=run(p["reference"],stdin,trace_limit=trace_limit)
        if ref["status"]!="ok": return {"kind":"oracle_unavailable","case":c,"stdin":stdin,"reference":ref}
        actual=run(source,stdin,trace_limit=trace_limit)
        status=actual["status"]
        if status=="ok": kind="match" if equal(m,actual["stdout"],ref["stdout"]) else "wrong_answer"
        elif status=="exception": kind="exception"
        else: kind="inconclusive"
        return {"kind":kind,"case":c,"stdin":stdin,"student":actual,"reference":ref}
    cases=[case] if case is not None else [c["case"] for c in p["controls"]]+list(generate(m,seed,count))
    seen=set();found=None;inconclusive=0
    for c in cases:
        key=digest(c)
        if key in seen: continue
        seen.add(key)
        result=pair(c)
        if result["kind"]=="oracle_unavailable":
            return {"status":"oracle_unavailable","detail":result,"attempts":attempts}
        if result["kind"] in ("wrong_answer","exception"): found=result;break
        if result["kind"]=="inconclusive": inconclusive+=1
    if not found: return {"status":"inconclusive" if inconclusive else "no_witness_found","attempts":attempts,"scope":"Bounded tests only; correctness not proven."}
    original=found
    for c in smaller(m,found["case"]):
        if reduce_calls<=0:break
        reduce_calls-=1
        candidate=pair(c)
        if candidate["kind"]==found["kind"]: found=candidate;break
    replay=[pair(found["case"],128) for _ in range(3)]
    def identity(x):
        return (x["kind"],x.get("reference",{}).get("stdout"),x.get("student",{}).get("stdout"),x.get("student",{}).get("detail"))
    if any(identity(x)!=identity(found) for x in replay):
        return {"status":"unstable","attempts":attempts,"scope":"Replay disagreed; no accusation."}
    witness=replay[0]
    student_events=witness["student"].get("events",[])
    reference_events=witness["reference"].get("events",[])
    hypotheses=[]; ai_status="disabled"
    if provider is not None:
        try:
            proposal=provider.propose("diagnosis",{"statement":m["statement"],"source":source,"stdin":witness["stdin"],"expected":witness["reference"]["stdout"],"actual":witness["student"].get("stdout"),"events":student_events[-24:]},DIAGNOSIS_SCHEMA)
            hypotheses=check_hypotheses(proposal,student_events);ai_status="ok"
        except (ProviderError,ValueError): ai_status="unavailable_or_invalid"
    return {"status":"observed_mismatch","kind":witness["kind"],"package_sha256":digest(p),"original_case":original["case"],"witness":witness,
            "reference_source":p["reference"],"student_source":source,"replay_count":3,"attempts":attempts,"student_graph":observed_graph(student_events),"reference_graph":observed_graph(reference_events),
            "hypotheses":hypotheses,"ai_status":ai_status,"elapsed_ms":round((time.monotonic()-start)*1000,2),
            "scope":"Replay-stable observation relative to owner-reviewed reference; guest evidence not authenticated; no root-cause proof."}
