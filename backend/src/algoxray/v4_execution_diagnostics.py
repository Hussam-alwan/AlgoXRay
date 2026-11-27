"""Explain recorded timeout symptoms; never certify a loop or line as the cause."""
import ast,hashlib
from .v4_dataflow import evaluate,scalar

def execution_diagnostics(source,execution):
    events=[e for e in execution.get("events",[]) if type(e) is dict and e.get("kind")=="line" and type(e.get("line")) is int and type(e.get("event_id")) is str and type(e.get("frame_id")) is str and type(e.get("locals")) is dict]
    result={"status":execution.get("status","unavailable"),"trace_status":execution.get("trace_status","unavailable"),
            "source_sha256":hashlib.sha256(source.encode()).hexdigest(),"findings":[],"timed_loops":[],
            "scope":"Recorded symptoms only. Repeated guard values and an unchanged assignment do not prove an infinite loop or root cause. A truncated trace covers only its recorded prefix."}
    if result["status"]!="timeout":return result
    result["timed_loops"]=[{k:b[k] for k in ("line","end_line","kind","hits") if k in b} for b in sorted(
        (b for b in execution.get("profile",{}).get("blocks",[]) if b.get("kind") in ("while","for") and type(b.get("hits")) is int and b["hits"]>0),
        key=lambda b:b["hits"],reverse=True)][:3]
    if events:result["last_recorded_event"]={k:events[-1][k] for k in ("line","event_id","frame_id")}
    try:tree=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError):return result
    statements={}
    for node in ast.walk(tree):
        if isinstance(node,ast.stmt):statements.setdefault(node.lineno,[]).append(node)
    by_frame={}
    for event in events:by_frame.setdefault(event["frame_id"],[]).append(event)
    for node in [n for n in ast.walk(tree) if isinstance(n,ast.While)][:64]:
        if node.test.lineno!=node.lineno or node.test.end_lineno!=node.lineno or node.body[0].lineno<=node.lineno:continue
        names=sorted({n.id for n in ast.walk(node.test) if isinstance(n,ast.Name)})
        if not 1<=len(names)<=8:continue
        for frame,rows in by_frame.items():
            headers=[(i,e) for i,e in enumerate(rows) if e["line"]==node.lineno]
            if len(headers)<3:continue
            snapshots=[]
            for _,event in headers:
                loc=event["locals"]
                try:
                    if not all(name in loc and scalar(loc[name]) for name in names):raise ValueError("Unavailable condition value")
                    condition=bool(evaluate(node.test,loc,{}))
                    values={name:loc[name] for name in names}
                    snapshots.append((values,condition))
                except (ValueError,ArithmeticError,RecursionError,TypeError):snapshots.append(None)
            latest=snapshots[-1]
            if latest is None or not latest[1]:continue
            repeated=1
            for earlier in reversed(snapshots[:-1]):
                if earlier is None or earlier[1] is not latest[1] or any(type(earlier[0][name]) is not type(latest[0][name]) or earlier[0][name]!=latest[0][name] for name in names):break
                repeated+=1
            if repeated<3:continue
            first=headers[-repeated][1];last=headers[-1][1]
            finding={"kind":"repeated_while_condition","line":node.lineno,"end_line":node.end_lineno,
                     "frame_id":frame,"condition_source":ast.get_source_segment(source,node.test)[:180],
                     "condition_values":latest[0],"condition_value":True,"observed_repeated_headers":repeated,
                     "first_event_id":first["event_id"],"last_event_id":last["event_id"],
                     "event_ids":[e["event_id"] for _,e in headers[-3:]],"assignments":[],
                     "causal_verified":False}
            start=headers[-min(repeated,4)][0];end=headers[-1][0];seen=set()
            for before,after in zip(rows[start:end],rows[start+1:end+1]):
                ns=statements.get(before["line"],[])
                if len(ns)!=1:continue
                assignment=ns[0]
                if assignment.end_lineno!=assignment.lineno:continue
                old=before["locals"];new=after["locals"];reads={}
                try:
                    if isinstance(assignment,ast.Assign) and len(assignment.targets)==1 and isinstance(assignment.targets[0],ast.Name):
                        name=assignment.targets[0].id;value=evaluate(assignment.value,old,reads)
                    elif isinstance(assignment,ast.AugAssign) and isinstance(assignment.target,ast.Name):
                        from .v4_dataflow import OPS
                        if type(assignment.op) not in OPS:continue
                        name=assignment.target.id
                        value=OPS[type(assignment.op)](evaluate(assignment.target,old,reads),evaluate(assignment.value,old,reads))
                    else:continue
                    if name not in names or not scalar(value) or name not in old or name not in new:continue
                    if type(value) is not type(old[name]) or type(value) is not type(new[name]) or value!=old[name] or value!=new[name]:continue
                    identity=(assignment.lineno,name)
                    if identity in seen:continue
                    seen.add(identity)
                    finding["assignments"].append({"line":assignment.lineno,"variable":name,"before":value,"after":value,
                        "source":ast.get_source_segment(source,assignment)[:180],"reads":reads,
                        "before_event_id":before["event_id"],"after_event_id":after["event_id"],"status":"matches_recorded_unchanged_assignment"})
                except (ValueError,ArithmeticError,RecursionError,TypeError):continue
                if len(finding["assignments"])>=4:break
            result["findings"].append(finding)
            if len(result["findings"])>=3:return result
    return result
