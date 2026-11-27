"""Observed loop header visits/body entries, never guessed iteration counts."""
import ast

def loop_observations(source,execution):
    try:tree=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError):return {"status":"unavailable","loops":[]}
    candidates=[n for n in ast.walk(tree) if isinstance(n,(ast.For,ast.While,ast.AsyncFor))][:128]
    events=execution.get("events",[]);out=[]
    for node in candidates:
        expression=node.test if isinstance(node,ast.While) else node.iter
        supported=not isinstance(node,ast.AsyncFor) and expression.lineno==node.lineno and expression.end_lineno==node.lineno and node.body[0].lineno>node.lineno
        if not supported:
            out.append({"line":node.lineno,"kind":type(node).__name__,"status":"unsupported_header_mapping"});continue
        frames={}
        previous={}
        for ev in events:
            if type(ev) is not dict or type(ev.get("line")) is not int or any(type(ev.get(k)) is not str for k in ("event_id","frame_id","kind")):continue
            frame=ev.get("frame_id")
            if ev.get("kind") in ("call","return"):previous.pop(frame,None)
            if ev.get("kind")!="line":continue
            before=previous.get(frame);previous[frame]=ev
            if ev.get("line")==node.lineno:
                entry=frames.setdefault(frame,{"frame_id":frame,"header_visits":0,"observed_body_entries":0,"header_event_ids":[],"body_event_ids":[]})
                entry["header_visits"]+=1;entry["header_event_ids"].append(ev["event_id"])
            if before and before.get("line")==node.lineno and ev.get("line")==node.body[0].lineno and frame in frames:
                frames[frame]["observed_body_entries"]+=1;frames[frame]["body_event_ids"].append(ev["event_id"])
        for frame,data in frames.items():
            out.append({"line":node.lineno,"end_line":node.end_lineno,"kind":type(node).__name__,
                        "status":"observed_complete_trace" if execution.get("trace_status")=="complete" else "observed_partial_trace",
                        **data})
    return {"status":"observed","loops":out,
            "scope":"Counts come from recorded same-frame line transitions. Partial traces give observed lower bounds; header visits are not body iterations."}

def with_loops(graph,source,execution):
    graph["loop_summary"]=loop_observations(source,execution)
    return graph
