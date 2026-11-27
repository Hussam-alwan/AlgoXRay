"""Independent local execution and timing. No reference is invented.

A manually supplied stdin is not claimed legal under a problem statement.
A user-reviewed sample only supports a comparison on that particular input.
"""
import hashlib
import math
import time
from copy import deepcopy
from statistics import median
from .v4_isolation import execute_stdio,MAX_SOURCE,MAX_INPUT
from .v4_graph import observed_graph
from .v4_profiling import attach_profile
from .v4_loop_observations import with_loops
from .v4_cfg import output_chain
from .v4_execution_diagnostics import execution_diagnostics
from .v4_contracts import validate_manifest,generate,serialize,equal,digest

def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def validate_text(source,stdin):
    if type(source) is not str or not 0<len(source.encode("utf-8"))<=MAX_SOURCE:
        raise ValueError("Source size outside supported bounds")
    if type(stdin) is not str or len(stdin.encode("utf-8"))>MAX_INPUT:
        raise ValueError("Input size outside supported bounds")

def observe_source(source,stdin,*,expected=None,expected_reviewed=False,
                   comparison="tokens",seconds=1.0,mode="trace_profile",run=execute_stdio,cancel=None):
    validate_text(source,stdin)
    if comparison not in ("tokens","exact"):raise ValueError("Unsupported sample comparison")
    if expected is not None and (type(expected) is not str or len(expected.encode("utf-8"))>8192):
        raise ValueError("Expected sample exceeds bounds")
    if mode not in ("trace_profile","benchmark_uninstrumented"):raise ValueError("Unsupported execution mode")
    result=run(source,stdin,trace_limit=256 if mode=="trace_profile" else 0,
               mode=mode,seconds=seconds,cancel=cancel)
    status=result["status"]
    outcome="syntax_error" if status=="exception" and result.get("detail") in ("SyntaxError","IndentationError","TabError") else "runtime_error" if status=="exception" else status
    if expected is None or not expected_reviewed:
        judgment={"status":"oracle_unavailable","authority":"none"}
    elif status!="ok":
        judgment={"status":"sample_not_compared","authority":"user_reviewed_sample"}
    else:
        judgment={"status":"sample_match" if equal({"output":comparison},result["stdout"],expected) else "sample_mismatch",
                  "authority":"user_reviewed_sample"}
    judgment.update(policy=comparison,expected=expected if expected_reviewed else None,
                    input_validity="not_verified_against_problem",general_correctness_claim=False)
    graph=with_loops(attach_profile(observed_graph(result.get("events",[]),source),result),source,result)
    graph["output_chain"]=output_chain(source,result,graph)
    from .v4_localization import localize
    progress=execution_diagnostics(source,result)
    localization=localize(source,{"student":result},graph,diagnostics=progress)

    return {"status":"cancelled" if status=="cancelled" else "manual_observation",
            "kind":outcome,"judgment":judgment,"source_sha256":sha(source),"student_source":source,
            "mode":mode,"witness":{"stdin":stdin,"case":None,"student":result,
                     "reference":{"status":"not_run","stdout":"","events":[],"trace_status":"not_run"}},
            "reference_source":"","student_graph":graph,
            "reference_graph":observed_graph([],""),
            "execution_diagnostics":progress,"evidence_localization":localization,
            "replay_count":0,"attempts":1,"ai_status":"disabled",
            "scope":"One manually supplied input; legality and general correctness not verified. No reference program ran. Sample comparison, if requested and reviewed, is an observation only."}

def generated_size_inputs(m,size_field,sizes,seed):
    """Constrain an explicitly selected scalar or T, never replace original constraints."""
    validate_manifest(m)
    if type(sizes) is not list or not 1<=len(sizes)<=5 or any(type(x) is not int or not 1<=x<=10**15 for x in sizes) or sizes!=sorted(set(sizes)):
        raise ValueError("Choose 1..5 strictly increasing positive integer sizes")
    rows=[]
    for size in sizes:
        narrow=deepcopy(m)
        if "repeat" in m:
            if size_field!="t":raise ValueError("Repeated grammar supports varying T only in this sweep")
            lo,hi=m["repeat"]["min"],m["repeat"]["max"]
            if not lo<=size<=hi:raise ValueError("Size outside original contract")
            narrow["repeat"]={"min":size,"max":size}
        else:
            field=next((f for f in narrow["fields"] if f["name"]==size_field and f["kind"]=="int"),None)
            if field is None or not field["min"]<=size<=field["max"]:
                raise ValueError("Choose an integer field and sizes within the original contract")
            field.update(min=size,max=size)
        validate_manifest(narrow)
        case=list(generate(narrow,seed,3))[-1]
        rows.append({"size":size,"case":case,"stdin":serialize(m,case)})
    return rows

def summaries(runs):
    stats={"completed":0,"timeouts":0,"requested":len(runs)}
    stats["timeouts"]=sum(r["status"]=="timeout" for r in runs)
    valid=[r for r in runs if r["status"]=="ok" and type(r.get("wall_ns")) is int and type(r.get("cpu_ns")) is int]
    stats["completed"]=len(valid)
    for key in ("wall_ns","cpu_ns","host_ms"):
        xs=[r[key] for r in valid if type(r.get(key)) in (float,int)]
        stats[key]={"median":median(xs),"min":min(xs),"max":max(xs)} if xs else None
    return stats

def empirical_exponent(points,repeats):
    """A descriptive fitted slope; deliberately abstain on sparse/censored/noisy observations."""
    if len(points)<3 or repeats<3:return {"status":"insufficient_points_or_repetitions"}
    if any(p["summary"]["completed"]!=repeats or p["summary"]["wall_ns"] is None or
           p["summary"]["wall_ns"]["min"]<=0 or p["summary"]["wall_ns"]["max"]>2*p["summary"]["wall_ns"]["min"] or
           p["correctness"]=="recorded_mismatch" or len({r.get("stdout_sha256") for r in p["runs"]})!=1 for p in points):
        return {"status":"incomplete_noisy_or_incorrect"}
    sizes=[p["size"] for p in points]
    if any(type(s) is not int or s<=0 for s in sizes) or max(sizes)<4*min(sizes):
        return {"status":"insufficient_size_range"}
    xs=[math.log(s) for s in sizes];ys=[math.log(p["summary"]["wall_ns"]["median"]) for p in points]
    mx,my=sum(xs)/len(xs),sum(ys)/len(ys)
    denominator=sum((x-mx)**2 for x in xs)
    if not denominator:return {"status":"insufficient_size_range"}
    slope=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/denominator
    return {"status":"descriptive_fit","wall_log_log_exponent":round(slope,3),
            "scope":"Empirical finite-range wall-time fit, not a Big-O proof or judge prediction."}

def benchmark_source(source,inputs,*,repeats=3,seconds=1.0,seed=2026,package=None,
                     size_field=None,run=execute_stdio,cancel=None,total_seconds=90):
    from .v4_engine import oracle
    if type(repeats) is not int or not 1<=repeats<=5:raise ValueError("Choose 1..5 repetitions")
    if type(inputs) is not list or not 1<=len(inputs)<=5:raise ValueError("Choose 1..5 inputs")
    for row in inputs:validate_text(source,row["stdin"])
    start=time.monotonic();points=[];executions=0;stop="completed"
    def invoke(src,stdin,limit):
        nonlocal executions
        executions+=1
        return run(src,stdin,trace_limit=0,mode="benchmark_uninstrumented",seconds=seconds,cancel=cancel)
    def stopped():
        if cancel is not None and cancel.is_set():return "cancelled"
        if time.monotonic()-start>=total_seconds:return "session_budget_exhausted"
        return None
    for row in inputs:
        stop=stopped() or "completed"
        if stop!="completed":break
        ref=oracle(package,row["stdin"],invoke) if package else None
        expected=ref.get("stdout") if ref and ref["status"]=="ok" else None
        runs=[]
        for _ in range(repeats):
            stop=stopped() or "completed"
            if stop!="completed":break
            result=invoke(source,row["stdin"],0);profile=result.get("profile",{})
            if result["status"]=="cancelled":
                stop="cancelled";break
            valid=profile.get("method")=="uninstrumented_execution" and result["status"]=="ok"
            match=equal(package["manifest"],result["stdout"],expected) if valid and expected is not None else None
            runs.append({"status":result["status"] if valid or result["status"]!="ok" else "measurement_unavailable",
                         "wall_ns":profile.get("execution_wall_ns") if valid else None,
                         "cpu_ns":profile.get("execution_cpu_ns") if valid else None,
                         "host_ms":result.get("elapsed_ms"),"matches_reviewed_reference":match,
                         "stdout_sha256":sha(result["stdout"]) if type(result.get("stdout")) is str else None,
                         "cleanup_confirmed":result.get("cleanup_confirmed"),"image_id":result.get("image_id")})
        summary=summaries(runs);summary["requested"]=repeats
        correctness=("recorded_mismatch" if any(r["matches_reviewed_reference"] is False for r in runs) else
                     "recorded_match" if len(runs)==repeats and all(r["matches_reviewed_reference"] is True for r in runs) else
                     "not_evaluated_or_inconclusive")
        points.append({**row,"runs":runs,"summary":summary,"correctness":correctness,
                       "reference_status":ref.get("status") if ref else "not_run"})
        if stop!="completed":break
    if cancel is not None and cancel.is_set():stop="cancelled"
    return {"status":"benchmark_observation","stop_reason":stop,"source_sha256":sha(source),
            "student_source":source,"package_sha256":digest(package) if package else None,
            "size_field":size_field,"seed":seed,"repetitions":repeats,"seconds_per_run":seconds,
            "session_budget_seconds":total_seconds,"physical_executions":executions,
            "elapsed_ms":round((time.monotonic()-start)*1000,2),"points":points,
            "growth":empirical_exponent(points,repeats) if stop=="completed" and size_field else {"status":"not_applicable_or_incomplete"},
            "scope":"Uninstrumented compile and execution wall/CPU; host time separate. Same input within each point; other fields generated by recorded boundary/random strategy. No guaranteed complexity class, platform time, or correctness."}
