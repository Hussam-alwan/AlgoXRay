"""Coverage-based suspiciousness, not causal localization or line alignment."""
import math

def lines(result):
    if result.get("trace_status")!="complete":return None
    events=result.get("events",[])
    if not events:return None
    return {e["line"] for e in events if type(e.get("line")) is int and e.get("kind")=="line"}

def rank(failing,passing):
    fail=lines(failing)
    good=[p for r in passing if (p:=lines(r)) is not None]
    if not fail or not good:return {"status":"insufficient_complete_traces","ranked":[],"passing_count":len(good)}
    ranked=[]
    for line in fail:
        passed=sum(line in p for p in good)
        ranked.append({"line":line,"ochiai":round(1/math.sqrt(1+passed),6),"failing_coverage":1,"passing_coverage":passed})
    ranked.sort(key=lambda x:(-x["ochiai"],x["line"]))
    return {"status":"observed_spectrum","ranked":ranked,"passing_count":len(good),"scope":"One failing trace and bounded passing traces of the same source. Coverage correlation, not root cause."}
