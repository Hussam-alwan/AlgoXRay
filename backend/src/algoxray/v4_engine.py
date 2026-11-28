"""Bounded observational debugging for approved stdio packages. No universal correctness claim."""
import time
from collections import Counter
from .v4_contracts import validate_package,serialize,generate,smaller,equal,digest,complexity
from .v4_isolation import execute_stdio
from .v4_shrinking import failure_signature
from .v4_checker import judge_output
from .v4_run_report import RunLedger,BudgetExhausted
from .v4_graph import observed_graph
from .v4_profiling import attach_profile
from .v4_loop_observations import with_loops
from .v4_diagnostic_context import diagnose_execution
from .v4_compare import rank
from .v4_cfg import output_chain
from .v4_guidance import hypothesis_cases,suggestions,classify_probe
from .v4_provider import OllamaProvider,DIAGNOSIS_SCHEMA,check_hypotheses,check_facts,ProviderError,bounded_propose

def oracle(p,stdin,run,trace_limit=0,*,case=None):
    first=run(p["reference"],stdin,trace_limit)
    if first["status"]!="ok":return first
    if "checker" in p:
        judgment=judge_output(p,case,first.get("stdout"),first.get("stdout"))
        if judgment["status"]!="accepted":
            return {"status":"oracle_disagreement","primary":first,"judgment":judgment}
        first={**first,"judgment":judgment}
    for c in p["controls"]:
        if serialize(p["manifest"],c["case"])==stdin and judge_output(p,c["case"],first.get("stdout"),c["expected"])["status"]!="accepted":
            return {"status":"oracle_disagreement","primary":first,"known_expected":c["expected"]}
    if "reference_alt" not in p:return first
    second=run(p["reference_alt"],stdin,0)
    if second["status"]=="cancelled":return second
    if second["status"]!="ok" or judge_output(p,case,second.get("stdout"),first.get("stdout"))["status"]!="accepted":
        return {"status":"oracle_disagreement","primary":first,"alternative":second}
    return {**first,"alternative_agreed":True}

def review(p,run=execute_stdio):
    validate_package(p);m=p["manifest"];checks=[]
    for c in p["controls"]:
        r=oracle(p,serialize(m,c["case"]),lambda src,stdin,limit:run(src,stdin,trace_limit=limit),case=c["case"])
        checks.append({"case":c["case"],"status":r["status"],"matches":r["status"]=="ok" and judge_output(p,c["case"],r["stdout"],c["expected"])["status"]=="accepted"})
    return {"passed":all(x["matches"] for x in checks),"checks":checks,"limitation":"Finite owner-supplied controls, not proof of reference correctness."}

def observed_example(p,source,witness):
    """Reuse an instrumented search pair, without another guest or AI call."""
    from .v4_branches import observed_branches
    from .v4_execution_diagnostics import execution_diagnostics
    from .v4_localization import localize
    def graph(code,execution):
        g=with_loops(attach_profile(observed_graph(execution.get("events",[]),code),execution),code,execution)
        g["output_chain"]=output_chain(code,execution,g)
        g["branches"]=observed_branches(code,execution,cfg=g["static_cfg"])
        return g
    student=witness["student"];sg=graph(source,student);rg=graph(p["reference"],witness["reference"])
    progress=execution_diagnostics(source,student)
    return {"status":"profiled_execution","kind":"match" if witness["kind"]=="match" else student["status"],
            "witness":witness,"package_sha256":digest(p),"student_source":source,"reference_source":p["reference"],
            "student_graph":sg,"reference_graph":rg,"replay_count":0,"attempts":1,"reused_search_trace":True,
            "execution_diagnostics":progress,"evidence_localization":localize(source,witness,sg,diagnostics=progress),
            **diagnose_execution(p,source,witness),
            "scope":"One example already observed during bounded search, not a failure witness or proof of general correctness. Instrumented timing is not normal runtime."}

def analyze_package(p,source,seed=2026,count=6,reduce_calls=12,case=None,provider=None,run=execute_stdio,cancel=None,generator="boundary_random",guided=False,spectrum=False,*,session_seconds=240,run_id=None,capture_example=False):
    if type(count) is not int or not 1<=count<=12 or type(reduce_calls) is not int or not 0<=reduce_calls<=32:
        raise ValueError("Invalid analysis budget")
    if type(session_seconds) not in (int,float) or not 1<=session_seconds<=300:raise ValueError("Invalid session budget")
    ledger=RunLedger("analysis",source,package=p,run_id=run_id,session_seconds=session_seconds,
        max_executions=3*(8+count+reduce_calls+3+6+4),
        parameters={"seed":seed,"count":count,"reduce_calls":reduce_calls,"case":case,"generator":generator,
                    "spectrum":spectrum,"guided":guided,"ai_requested":provider is not None,
                    "model":getattr(provider,"model",None),"trace_limit":128,"replays":3,"capture_example":capture_example})
    for stage,enabled in (("guided_search",guided and provider is not None),("guided_confirmation",guided and provider is not None),
                          ("diagnosis",provider is not None),("spectrum",spectrum)):
        if not enabled:ledger.skip(stage,"not_requested")
    try:
        result=_analyze_package(p,source,seed,count,reduce_calls,case,provider,run,cancel,generator,guided,spectrum,ledger,capture_example)
        return ledger.finish(result)
    except BudgetExhausted as exc:
        return ledger.finish({"status":"inconclusive","stop_reason":str(exc),
                              "scope":"Analysis stopped at a declared session budget checkpoint. Partial observations are not a new verified verdict."},stop_reason=str(exc))

def _analyze_package(p,source,seed,count,reduce_calls,case,provider,run,cancel,generator,guided,spectrum,ledger,capture_example):
    ledger.enter("validation")
    validate_package(p);m=p["manifest"]
    if type(count) is not int or not 1<=count<=12 or type(reduce_calls) is not int or not 0<=reduce_calls<=32: raise ValueError("Invalid analysis budget")
    if type(seed) is not int or not 0<=seed<=2**32-1: raise ValueError("Invalid seed")
    if generator not in ("boundary_random","hypothesis"):raise ValueError("Unsupported generator")
    start=time.monotonic(); attempts=0; executions=0
    guidance={"status":"disabled","rejected":0,"probes":[]};suggested=False
    def invoke(src,stdin,trace_limit,role="reference"):
        nonlocal executions
        executions+=1
        return ledger.execute(run,role,src,stdin,trace_limit=trace_limit,**({"cancel":cancel} if cancel is not None else {}))
    def pair(c,trace_limit=0):
        nonlocal attempts
        attempts+=1;ledger.pair_attempts+=1
        stdin=serialize(m,c)
        if cancel is not None and cancel.is_set():return {"kind":"cancelled","case":c,"stdin":stdin}
        ref=oracle(p,stdin,invoke,trace_limit,case=c)
        if ref["status"]=="cancelled":return {"kind":"cancelled","case":c,"stdin":stdin}
        if ref["status"]!="ok": return {"kind":"oracle_unavailable","case":c,"stdin":stdin,"reference":ref}
        actual=invoke(source,stdin,trace_limit,role="student")
        status=actual["status"]
        judgment=None
        if status=="cancelled":kind="cancelled"
        elif status=="ok":
            judgment=judge_output(p,c,actual.get("stdout"),ref.get("stdout"))
            kind={"accepted":"match","rejected":"wrong_answer","unavailable":"oracle_unavailable"}[judgment["status"]]
        elif status=="exception": kind="exception"
        else: kind="inconclusive"
        return {"kind":kind,"case":c,"stdin":stdin,"student":actual,"reference":ref,"judgment":judgment}
    cases=[case] if case is not None else [c["case"] for c in p["controls"]]+list(hypothesis_cases(m,seed,count) if generator=="hypothesis" else generate(m,seed,count))
    ledger.enter("search")
    seen=set();found=None;example=None;inconclusive=Counter()
    for c in cases:
        key=digest(c)
        if key in seen: continue
        seen.add(key)
        result=pair(c,128 if capture_example and example is None else 0)
        if result["kind"]=="cancelled":return {"status":"cancelled","attempts":attempts}
        if result["kind"]=="oracle_unavailable":
            return {"status":"oracle_unavailable","detail":result,"attempts":attempts}
        if result["kind"] in ("wrong_answer","exception"): found=result;break
        if capture_example and example is None:example=result
        if result["kind"]=="inconclusive": inconclusive[result["student"]["status"]]+=1
    def run_suggestions(witness=None,hypotheses=()):
        nonlocal suggested
        suggested=True
        ledger.enter("guided_confirmation" if witness else "guided_search")
        ledger.check()
        if cancel is not None and cancel.is_set():return None
        try:
            proposals,rejected=suggestions(provider,m,source,witness,hypotheses,cancel=cancel)
            guidance.update(status="completed",rejected=rejected,usage=getattr(provider,"usage",{}))
        except (ProviderError,ValueError) as exc:
            guidance.update(status="unavailable_or_invalid",error=str(exc)[:120]);ledger.close_stage("partial");return None
        first=None
        for proposal in proposals:
            key=digest(proposal["case"])
            if key in seen:
                guidance["rejected"]+=1;continue
            seen.add(key)
            result=pair(proposal["case"])
            guidance["probes"].append(classify_probe(proposal,result))
            if result["kind"]=="inconclusive":inconclusive[result["student"]["status"]]+=1
            if result["kind"]=="cancelled":return None
            if result["kind"]=="oracle_unavailable":return result
            if first is None and result["kind"] in ("wrong_answer","exception"):first=result
        return first
    if not found and provider is not None and guided and case is None:
        found=run_suggestions()
        if found and found["kind"]=="oracle_unavailable":return {"status":"oracle_unavailable","attempts":attempts,"detail":found,"guidance":guidance}
        if cancel is not None and cancel.is_set():return {"status":"cancelled","attempts":attempts}
    if not found:
        response={"status":"inconclusive" if inconclusive or any(x["status"]=="inconclusive" for x in guidance["probes"]) else "no_witness_found",
                "attempts":attempts,"generator":generator,"guidance":guidance,"scope":"Bounded tests only; correctness not proven.",
                "inconclusive_student_outcomes":dict(inconclusive)}
        if example is not None:
            ledger.enter("structure")
            ledger.check()
            response["example_observation"]=observed_example(p,source,example)
        return response
    original=found
    ledger.partial={"witness":original,"replay_verified":False}
    ledger.enter("shrink")
    signature=failure_signature(original)
    budget=reduce_calls
    accepted=[]
    checked={digest(original["case"])}
    stop_reason="budget_exhausted" if not budget else "signature_unavailable" if signature is None else "no_smaller_candidate"
    while reduce_calls>0 and signature is not None:
        improved=False
        for c in smaller(m,found["case"]):
            key=digest(c)
            if key in checked:continue
            if reduce_calls<=0:break
            checked.add(key);reduce_calls-=1
            candidate=pair(c)
            if candidate["kind"]=="cancelled":return {"status":"cancelled","attempts":attempts}
            if candidate["kind"]=="oracle_unavailable":
                return {"status":"oracle_unavailable","detail":candidate,"attempts":attempts}
            if failure_signature(candidate)==signature:
                accepted.append({"case":c,"complexity":complexity(m,c),"stdin":candidate["stdin"]})
                found=candidate;improved=True;break
        if not improved:
            stop_reason="budget_exhausted" if reduce_calls<=0 else "no_smaller_candidate"
            break
    if signature is not None and reduce_calls<=0:stop_reason="budget_exhausted"
    reduction={"original_complexity":complexity(m,original["case"]),
               "reduced_complexity":complexity(m,found["case"]),
               "signature":signature,"budget":budget,"probes":budget-reduce_calls,
               "accepted":accepted,"stop_reason":stop_reason,
               "scope":"Best legal compatible witness found within budget; neither global minimality nor identical root cause proven."}
    def identity(x):
        student=x.get("student",{})
        return (x["kind"],x.get("reference",{}).get("stdout"),student.get("stdout"),student.get("detail"),student.get("failure_location"))

    def replay_case(expected,trace_limit,label):
        first=None
        for _ in range(3):
            replayed=pair(expected["case"],trace_limit)
            kind=replayed["kind"]
            if kind=="cancelled":
                return None,{"status":kind,"attempts":attempts}
            if kind=="oracle_unavailable":
                return None,{"status":kind,"detail":replayed,"attempts":attempts}
            if identity(replayed)!=identity(expected):
                return None,{"status":"unstable","attempts":attempts,"reduction":reduction,
                             "scope":label+" replay disagreed; no accusation."}
            if first is None:first=replayed
        return first,None

    ledger.enter("replay")
    if accepted:
        _,failure=replay_case(original,0,"Original")
        if failure:return failure
        reduction["original_replay_count"]=3
    witness,failure=replay_case(found,128,"Best witness")
    if failure:return failure
    reduction["reduced_replay_count"]=3
    seen.add(digest(witness["case"]))
    ledger.partial={"witness":witness,"original_case":original["case"],"reduction":reduction,"replay_verified":True}
    student_events=witness["student"].get("events",[])
    reference_events=witness["reference"].get("events",[])
    ranking={"status":"disabled","ranked":[]}
    if spectrum:
        ledger.enter("spectrum")
        passing=[];additional_failing=[]
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
                if extra["student"].get("trace_status")=="complete":
                    if extra["kind"]=="match":passing.append(extra["student"])
                    elif extra["kind"] in ("wrong_answer","exception"):additional_failing.append(extra["student"])
                if len(checked)>=4:break
        ranking=rank(witness["student"],passing,source=source,additional_failing=additional_failing)
    if cancel is not None and cancel.is_set():return {"status":"cancelled","attempts":attempts}
    ledger.enter("structure")
    student_graph=with_loops(attach_profile(observed_graph(student_events,source),witness["student"]),source,witness["student"]);reference_graph=with_loops(attach_profile(observed_graph(reference_events,p["reference"]),witness["reference"]),p["reference"],witness["reference"])
    student_graph["output_chain"]=output_chain(source,witness["student"],student_graph)
    reference_graph["output_chain"]=output_chain(p["reference"],witness["reference"],reference_graph)
    from .v4_branches import observed_branches
    student_graph["branches"]=observed_branches(source,witness["student"],cfg=student_graph["static_cfg"])
    reference_graph["branches"]=observed_branches(p["reference"],witness["reference"],cfg=reference_graph["static_cfg"])
    from .v4_localization import localize
    localization=localize(source,witness,student_graph,ranking)

    ledger.partial.update(student_graph=student_graph,reference_graph=reference_graph,evidence_localization=localization)
    if provider is not None:
        ledger.enter("diagnosis")
        ledger.check()
    diagnosis=diagnose_execution(p,source,witness,provider,ranking,cancel,localization=localization,reduction=reduction,branches=student_graph["branches"])
    if provider is not None and diagnosis["ai_status"]!="ok":ledger.close_stage("partial")
    hypotheses=[h for h in diagnosis["hypotheses"] if h["status"]=="hypothesis" and not h.get("conflicting_claims")];ai_status=diagnosis["ai_status"]
    if provider is not None and guided and not suggested and hypotheses and ai_status=="ok":
        extra=run_suggestions({"case":witness["case"],"expected":witness["reference"]["stdout"],"actual":witness["student"].get("stdout")},hypotheses)
        if extra and extra["kind"]=="oracle_unavailable":return {"status":"oracle_unavailable","attempts":attempts,"detail":extra,"guidance":guidance}
    if cancel is not None and cancel.is_set():return {"status":"cancelled","attempts":attempts}
    for stage in ("guided_search","guided_confirmation"):
        ledger.skip(stage,"not_needed")
    return {"status":"observed_mismatch","kind":witness["kind"],"package_sha256":digest(p),"original_case":original["case"],"original_witness":original,"reduction":reduction,"executions":executions,"witness":witness,
            "reference_source":p["reference"],"student_source":source,"replay_count":3,"attempts":attempts,"student_graph":student_graph,"reference_graph":reference_graph,
            **diagnosis,"evidence_localization":localization,"generator":generator,"guidance":guidance,"suspiciousness":ranking,"elapsed_ms":round((time.monotonic()-start)*1000,2),
            "scope":"Replay-stable observation relative to owner-reviewed reference; guest evidence not authenticated; no root-cause proof."}
