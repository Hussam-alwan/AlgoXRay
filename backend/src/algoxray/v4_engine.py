"""Bounded observational debugging for approved stdio packages. No universal correctness claim."""
import time
from .v4_contracts import validate_package,serialize,generate,smaller,equal,digest
from .v4_isolation import execute_stdio
from .v4_graph import observed_graph
from .v4_profiling import attach_profile
from .v4_loop_observations import with_loops
from .v4_compare import rank
from .v4_cfg import output_chain
from .v4_guidance import hypothesis_cases,suggestions,classify_probe
from .v4_provider import OllamaProvider,DIAGNOSIS_SCHEMA,check_hypotheses,check_facts,ProviderError,bounded_propose

def oracle(p,stdin,run,trace_limit=0):
    first=run(p["reference"],stdin,trace_limit)
    if first["status"]!="ok":return first
    for c in p["controls"]:
        if serialize(p["manifest"],c["case"])==stdin and not equal(p["manifest"],first["stdout"],c["expected"]):
            return {"status":"oracle_disagreement","primary":first,"known_expected":c["expected"]}
    if "reference_alt" not in p:return first
    second=run(p["reference_alt"],stdin,0)
    if second["status"]=="cancelled":return second
    if second["status"]!="ok" or not equal(p["manifest"],first["stdout"],second["stdout"]):
        return {"status":"oracle_disagreement","primary":first,"alternative":second}
    return {**first,"alternative_agreed":True}

def review(p,run=execute_stdio):
    validate_package(p);m=p["manifest"];checks=[]
    for c in p["controls"]:
        r=oracle(p,serialize(m,c["case"]),lambda src,stdin,limit:run(src,stdin,trace_limit=limit))
        checks.append({"case":c["case"],"status":r["status"],"matches":r["status"]=="ok" and equal(m,r["stdout"],c["expected"])})
    return {"passed":all(x["matches"] for x in checks),"checks":checks,"limitation":"Finite owner-supplied controls, not proof of reference correctness."}

def analyze_package(p,source,seed=2026,count=6,reduce_calls=3,case=None,provider=None,run=execute_stdio,cancel=None,generator="boundary_random",guided=False,spectrum=False):
    validate_package(p);m=p["manifest"]
    if type(count) is not int or not 1<=count<=12 or type(reduce_calls) is not int or not 0<=reduce_calls<=6: raise ValueError("Invalid analysis budget")
    if type(seed) is not int or not 0<=seed<=2**32-1: raise ValueError("Invalid seed")
    if generator not in ("boundary_random","hypothesis"):raise ValueError("Unsupported generator")
    start=time.monotonic(); attempts=0
    guidance={"status":"disabled","rejected":0,"probes":[]};suggested=False
    def invoke(src,stdin,trace_limit):
        return run(src,stdin,trace_limit=trace_limit,**({"cancel":cancel} if cancel is not None else {}))
    def pair(c,trace_limit=0):
        nonlocal attempts
        attempts+=1
        stdin=serialize(m,c)
        if cancel is not None and cancel.is_set():return {"kind":"cancelled","case":c,"stdin":stdin}
        ref=oracle(p,stdin,invoke,trace_limit)
        if ref["status"]=="cancelled":return {"kind":"cancelled","case":c,"stdin":stdin}
        if ref["status"]!="ok": return {"kind":"oracle_unavailable","case":c,"stdin":stdin,"reference":ref}
        actual=invoke(source,stdin,trace_limit)
        status=actual["status"]
        if status=="cancelled":kind="cancelled"
        elif status=="ok": kind="match" if equal(m,actual["stdout"],ref["stdout"]) else "wrong_answer"
        elif status=="exception": kind="exception"
        else: kind="inconclusive"
        return {"kind":kind,"case":c,"stdin":stdin,"student":actual,"reference":ref}
    cases=[case] if case is not None else [c["case"] for c in p["controls"]]+list(hypothesis_cases(m,seed,count) if generator=="hypothesis" else generate(m,seed,count))
    seen=set();found=None;inconclusive=0
    for c in cases:
        key=digest(c)
        if key in seen: continue
        seen.add(key)
        result=pair(c)
        if result["kind"]=="cancelled":return {"status":"cancelled","attempts":attempts}
        if result["kind"]=="oracle_unavailable":
            return {"status":"oracle_unavailable","detail":result,"attempts":attempts}
        if result["kind"] in ("wrong_answer","exception"): found=result;break
        if result["kind"]=="inconclusive": inconclusive+=1
    def run_suggestions(witness=None,hypotheses=()):
        nonlocal suggested
        suggested=True
        if cancel is not None and cancel.is_set():return None
        try:
            proposals,rejected=suggestions(provider,m,source,witness,hypotheses,cancel=cancel)
            guidance.update(status="completed",rejected=rejected,usage=getattr(provider,"usage",{}))
        except (ProviderError,ValueError) as exc:
            guidance.update(status="unavailable_or_invalid",error=str(exc)[:120]);return None
        first=None
        for proposal in proposals:
            key=digest(proposal["case"])
            if key in seen:
                guidance["rejected"]+=1;continue
            seen.add(key)
            result=pair(proposal["case"])
            guidance["probes"].append(classify_probe(proposal,result))
            if result["kind"]=="cancelled":return None
            if result["kind"]=="oracle_unavailable":return result
            if first is None and result["kind"] in ("wrong_answer","exception"):first=result
        return first
    if not found and provider is not None and guided and case is None:
        found=run_suggestions()
        if found and found["kind"]=="oracle_unavailable":return {"status":"oracle_unavailable","attempts":attempts,"detail":found,"guidance":guidance}
        if cancel is not None and cancel.is_set():return {"status":"cancelled","attempts":attempts}
    if not found: return {"status":"inconclusive" if inconclusive or any(x["status"]=="inconclusive" for x in guidance["probes"]) else "no_witness_found","attempts":attempts,"generator":generator,"guidance":guidance,"scope":"Bounded tests only; correctness not proven."}
    original=found
    for c in smaller(m,found["case"]):
        if reduce_calls<=0:break
        reduce_calls-=1
        candidate=pair(c)
        if candidate["kind"]=="cancelled":return {"status":"cancelled","attempts":attempts}
        if candidate["kind"]==found["kind"]: found=candidate;break
    replay=[pair(found["case"],128) for _ in range(3)]
    if any(x["kind"]=="cancelled" for x in replay):return {"status":"cancelled","attempts":attempts}
    def identity(x):
        return (x["kind"],x.get("reference",{}).get("stdout"),x.get("student",{}).get("stdout"),x.get("student",{}).get("detail"))
    if any(identity(x)!=identity(found) for x in replay):
        return {"status":"unstable","attempts":attempts,"scope":"Replay disagreed; no accusation."}
    witness=replay[0];seen.add(digest(witness["case"]))
    student_events=witness["student"].get("events",[])
    reference_events=witness["reference"].get("events",[])
    hypotheses=[];facts=[]; ai_status="disabled";ai_error=None
    if provider is not None:
        try:
            supplied=student_events[-24:]
            proposal=bounded_propose(provider,"diagnosis",{"statement":m["statement"],"source":source,"stdin":witness["stdin"],"expected":witness["reference"]["stdout"],"actual":witness["student"].get("stdout"),"events":supplied,"instruction":"Use only supplied event IDs. Facts must use scalar local variables only: integer, boolean, string or null; omit arrays and unavailable values. Hypotheses are not verified causes."},DIAGNOSIS_SCHEMA,cancel=cancel)
            hypotheses=check_hypotheses(proposal,supplied);facts=check_facts(proposal,supplied);ai_status="ok"
        except ProviderError as exc: ai_status="unavailable_or_invalid";ai_error=str(exc);hypotheses=[];facts=[]
        except ValueError: ai_status="unavailable_or_invalid";ai_error="invalid_model_output";hypotheses=[];facts=[]
    ai_usage=dict(getattr(provider,"usage",{}))
    if provider is not None and guided and not suggested and hypotheses and ai_status=="ok":
        extra=run_suggestions({"case":witness["case"],"expected":witness["reference"]["stdout"],"actual":witness["student"].get("stdout")},hypotheses)
        if extra and extra["kind"]=="oracle_unavailable":return {"status":"oracle_unavailable","attempts":attempts,"detail":extra,"guidance":guidance}
    ranking={"status":"disabled","ranked":[]}
    if spectrum:
        passing=[]
        if witness["student"].get("trace_status")=="complete":
            candidates=[c["case"] for c in p["controls"]]+list(generate(m,seed^12345,3))
            checked=set()
            for c in candidates:
                key=digest(c)
                if key==digest(witness["case"]) or key in checked:continue
                checked.add(key)
                extra=pair(c,128)
                if extra["kind"]=="cancelled":break
                if extra["kind"]=="oracle_unavailable":return {"status":"oracle_unavailable","attempts":attempts,"detail":extra}
                if extra["kind"]=="match" and extra["student"].get("trace_status")=="complete":passing.append(extra["student"])
                if len(checked)>=3 or len(passing)>=2:break
        ranking=rank(witness["student"],passing)
    if cancel is not None and cancel.is_set():return {"status":"cancelled","attempts":attempts}
    student_graph=with_loops(attach_profile(observed_graph(student_events,source),witness["student"]),source,witness["student"]);reference_graph=with_loops(attach_profile(observed_graph(reference_events,p["reference"]),witness["reference"]),p["reference"],witness["reference"])
    student_graph["output_chain"]=output_chain(source,witness["student"],student_graph)
    reference_graph["output_chain"]=output_chain(p["reference"],witness["reference"],reference_graph)
    return {"status":"observed_mismatch","kind":witness["kind"],"package_sha256":digest(p),"original_case":original["case"],"witness":witness,
            "reference_source":p["reference"],"student_source":source,"replay_count":3,"attempts":attempts,"student_graph":student_graph,"reference_graph":reference_graph,
            "hypotheses":hypotheses,"ai_facts":facts,"ai_status":ai_status,"ai_model":getattr(provider,"model",None),"ai_usage":ai_usage,"generator":generator,"guidance":guidance,"suspiciousness":ranking,"ai_error":ai_error,"elapsed_ms":round((time.monotonic()-start)*1000,2),
            "scope":"Replay-stable observation relative to owner-reviewed reference; guest evidence not authenticated; no root-cause proof."}
