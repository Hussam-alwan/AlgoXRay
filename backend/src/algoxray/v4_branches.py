"""Source-linked observations of syntactic branch edges.

This is not full branch coverage. Only uniquely matched observed line
transitions in a restricted CFG count. Truncated traces supply positive
observations but must not be used as complete spectra.
"""
import ast
from collections import defaultdict
from .v4_cfg import static_cfg

LABELS={"condition_true","condition_false","loop_body","loop_exit"}

def observed_branches(source,execution,*,cfg=None):
    cfg=static_cfg(source) if cfg is None else cfg
    nodes={n["id"]:n for n in cfg.get("nodes",[])}
    candidates=defaultdict(list)
    all_edges=defaultdict(list)
    try:
        t=ast.parse(source)
        counts=defaultdict(int)
        for n in ast.walk(t):
            if isinstance(n,ast.stmt):counts[n.lineno]+=1
    except (SyntaxError,ValueError,RecursionError):
        counts={}
    for e in cfg.get("edges",[]):
        a,b=nodes.get(e["from"]),nodes.get(e["to"])
        if a and b and counts.get(a["line"])==counts.get(b["line"])==1:
            key=(a["line"],b["line"])
            all_edges[key].append(e)
            if e["kind"] in LABELS:candidates[key].append(e)
    unique={k:v[0] for k,v in candidates.items() if len(v)==len(all_edges[k])==1}
    previous={};observations={}
    for ev in execution.get("events",[]):
        if type(ev) is not dict or type(ev.get("event_id")) is not str or type(ev.get("frame_id")) is not str:continue
        frame=ev["frame_id"];kind=ev.get("kind")
        if kind in ("call","return","exception"):
            previous.pop(frame,None)
            continue
        if kind!="line" or type(ev.get("line")) is not int:continue
        before=previous.get(frame);previous[frame]=ev
        if before is None:continue
        pair=(before["line"],ev["line"]);e=unique.get(pair)
        if e is None:continue
        identity=e["from"]+"|"+e["kind"]+"|"+e["to"]
        row=observations.setdefault(identity,{"id":identity,"line":pair[0],"target_line":pair[1],
            "kind":e["kind"],"count":0,"event_pairs":[]})
        row["count"]+=1
        if len(row["event_pairs"])<8:row["event_pairs"].append([before["event_id"],ev["event_id"]])
    return {"status":"observed_syntactic_edges","trace_status":execution.get("trace_status","unavailable"),
            "observed":list(observations.values())[:256],
            "candidate_edges":len(unique),"scope":"Only uniquely matched same-frame line transitions in the restricted CFG. Unknown branches and omitted control flow are not claimed covered. Partial traces are not complete coverage.",
            "complete_spectrum_eligible":execution.get("trace_status")=="complete" and bool(execution.get("events"))}
