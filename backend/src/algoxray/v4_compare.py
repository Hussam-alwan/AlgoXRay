"""Coverage association, not causal localization or cross-source line alignment."""
import math

def lines(result):
    if result.get("trace_status")!="complete":return None
    events=result.get("events",[])
    if not events:return None
    return {e["line"] for e in events if type(e.get("line")) is int and e.get("kind")=="line"}

def rank(failing,passing,*,source=None,additional_failing=()):
    failed=[(r,ls) for r in [failing,*additional_failing] if (ls:=lines(r))]
    good=[(r,ls) for r in passing if (ls:=lines(r))]
    # The selected witness itself must be complete; other traces do not make
    # its truncated prefix a complete failing spectrum.
    if not lines(failing) or not good:return {"status":"insufficient_complete_traces","ranked":[],"passing_count":len(good),"failing_count":len(failed)}
    n=len(failed)
    ranked=[]
    for line in set().union(*(ls for _,ls in failed)):
        f=sum(line in ls for _,ls in failed);p=sum(line in ls for _,ls in good)
        ranked.append({"line":line,"ochiai":round(f/math.sqrt(n*(f+p)),6),"failing_coverage":f,"passing_coverage":p})
    ranked.sort(key=lambda x:(-x["ochiai"],x["line"]))
    result={"status":"observed_spectrum","ranked":ranked,"passing_count":len(good),"failing_count":n,
            "scope":"Bounded complete traces of the same source. Coverage correlation, not root cause."}
    if source is not None:
        from .v4_branches import observed_branches
        from .v4_cfg import static_cfg
        cfg=static_cfg(source)
        def edge_map(r):
            return {e["id"]:e for e in observed_branches(source,r,cfg=cfg)["observed"]}
        failures=[edge_map(r) for r,_ in failed];passes=[edge_map(r) for r,_ in good]
        unique={k:v for rows in failures for k,v in rows.items()}
        branches=[]
        witness=failures[0]
        for k,v in unique.items():
            f=sum(k in r for r in failures);p=sum(k in r for r in passes)
            branches.append({key:v[key] for key in ("id","line","target_line","kind")}|
                            {"ochiai":round(f/math.sqrt(n*(f+p)),6),"failing_coverage":f,"passing_coverage":p,
                             "witness_event_pairs":witness.get(k,{}).get("event_pairs",[])})
        branches.sort(key=lambda r:(-r["ochiai"],r["line"],r["target_line"]))
        result["branches"]={"status":"observed_branch_spectrum","ranked":branches[:64],
                            "scope":"Restricted syntactic successor edges only. No full coverage claim."}
    return result
