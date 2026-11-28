"""Conservative evidence-ranked source locations, never causal proof.

Weights are deterministic development heuristics, not probabilities or learned
accuracy. Only recorded line/event anchors are presented as observations.
"""
import ast
import re
from .v4_dataflow import evaluate
from .v4_source_structure import python_source_lines

def loop_bounds_evidence(source,execution,graph):
    try:tree=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError):return []
    events=[e for e in execution.get("events",[]) if e.get("kind")=="line" and type(e.get("locals")) is dict]
    out=[]
    for node in [n for n in ast.walk(tree) if isinstance(n,ast.For)][:64]:
        if not (isinstance(node.target,ast.Name) and isinstance(node.iter,ast.Call)
                and isinstance(node.iter.func,ast.Name) and node.iter.func.id=="range"
                and 1<=len(node.iter.args)<=3 and not node.iter.keywords
                and node.body and node.body[0].lineno>node.lineno):continue
        index=node.target.id
        arrays={x.value.id for stmt in node.body for x in ast.walk(stmt)
                if isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name)
                and isinstance(x.slice,ast.Name) and x.slice.id==index}
        if not arrays:continue
        for header in [e for e in events if e["line"]==node.lineno][:16]:
            frame=header.get("frame_id")
            try:
                args=[evaluate(arg,header["locals"],{}) for arg in node.iter.args]
                if not all(type(v) is int for v in args):continue
                values=range(*args)
                if len(values)>24:continue
                indices=list(values)
            except (ValueError,ArithmeticError,TypeError,RecursionError):continue
            for name in sorted(arrays):
                a=header["locals"].get(name)
                if type(a) is not list or not 1<=len(a)<=24 or any(not 0<=v<len(a) for v in indices):continue
                omitted=sorted(set(range(len(a)))-set(indices))
                if not omitted:continue
                # Confirm some actual supported subscript reads, never infer
                # access merely from the syntax or from an index variable.
                reads={}
                for row in graph.get("relations",{}).get("data",[]):
                    if row.get("frame_id")!=frame or not node.lineno<row.get("line",-1)<=node.end_lineno:continue
                    for key in row.get("reads",{}):
                        match=re.fullmatch(re.escape(name)+r"\[(\d+)\]",key)
                        if match:reads.setdefault(int(match[1]),row["before_event_id"])
                if not reads or set(reads)!=set(indices):continue
                finding={"kind":"range_skips_array_indices","line":node.lineno,"end_line":node.end_lineno,
                         "frame_id":frame,"header_event_id":header["event_id"],"array":name,"array_length":len(a),
                         "range_source":ast.get_source_segment(source,node.iter)[:180],
                         "computed_indices":indices,"observed_read_indices":sorted(reads),
                         "omitted_indices":omitted,"event_ids":[header["event_id"]]+list(reads.values())[:24],
                         "status":"snapshot_compatible_range_and_recorded_reads",
                         "hypothesis":"Check whether the task requires processing the omitted indices. Skipping them is not inherently erroneous.",
                         "causal_verified":False}
                out.append(finding)
                if len(out)>=8:return out
            # Only one pre-header snapshot per frame is needed for this limited probe.
            if any(x["line"]==node.lineno and x["frame_id"]==frame for x in out):break
    return out

def localize(source,witness,graph,ranking=None,diagnostics=None):
    execution=witness.get("student",{})
    kind=witness.get("kind","observation")
    known={e["event_id"]:e for e in execution.get("events",[])
           if type(e) is dict and type(e.get("event_id")) is str and type(e.get("line")) is int}
    max_line=len(python_source_lines(source))
    rows={}
    def add(line,signal,weight,events,detail):
        if type(line) is not int or not 1<=line<=max_line:return
        ids=list(dict.fromkeys(e for e in events if e in known))[:24]
        row=rows.setdefault(line,{"line":line,"score":0.0,"signals":[],"event_ids":[]})
        if any(x["kind"]==signal for x in row["signals"]):return
        row["score"]+=weight
        row["signals"].append({"kind":signal,"weight":weight,"event_ids":ids,"detail":detail})
        row["event_ids"]=list(dict.fromkeys(row["event_ids"]+ids))[:32]
    effect=None
    chain=graph.get("output_chain") or {}
    output_event=known.get(chain.get("output_event_id"))
    if output_event:
        effect={"line":output_event["line"],"event_id":output_event["event_id"],
                "kind":"output_snapshot_compatible","causal_verified":False}
    if execution.get("status")=="exception":
        loc=execution.get("failure_location") or {}
        line=loc.get("line")
        if type(line) is int and 1<=line<=max_line:
            exception_ids=[e["event_id"] for e in known.values() if e["line"]==line and e.get("kind")=="exception"
                           and (not loc.get("function") or e.get("function")==loc["function"])
                           and (not execution.get("detail") or e.get("exception_type")==execution["detail"])]
            add(line,"reported_exception_location",3,exception_ids,
                "Guest-reported exception location, not necessarily the defect origin.")
            effect={"line":line,"kind":"reported_exception_location","causal_verified":False}
            if exception_ids:effect["event_id"]=exception_ids[-1]
    for row in (ranking or {}).get("ranked",[])[:32]:
        score=row.get("ochiai")
        if type(score) in (int,float) and 0<=score<=1:
            add(row.get("line"),"coverage_ochiai",round(score,6),
                [e["event_id"] for e in known.values() if e["line"]==row["line"]],
                "Association with failing vs passing line coverage; not causation.")
    for row in (ranking or {}).get("branches",{}).get("ranked",[])[:24]:
        ids=[e for pair in row.get("witness_event_pairs",[]) for e in pair]
        if ids:
            add(row.get("line"),"observed_branch_ochiai",round(row["ochiai"],6),ids,
                "Observed restricted successor edge associated with failure, not causal proof.")
    for link in chain.get("links",[])[:16]:
        add(link.get("line"),"output_predecessor",2,
            [link.get("before_event_id"),link.get("after_event_id")],
            "Supported observed predecessor of the output-compatible snapshot.")
    for finding in (diagnostics or {}).get("findings",[]):
        add(finding.get("line"),"repeated_condition",2,finding.get("event_ids",[]),
            "Repeated recorded condition values; not an infinite-loop proof.")
        for assignment in finding.get("assignments",[]):
            add(assignment.get("line"),"unchanged_assignment",3,
                [assignment.get("before_event_id"),assignment.get("after_event_id")],
                "Recomputed assignment agrees with unchanged recorded value.")
    bounds=loop_bounds_evidence(source,execution,graph) if kind=="wrong_answer" else []
    for finding in bounds:
        add(finding["line"],"range_index_omission",2.5,finding["event_ids"],
            "Recomputed range omits some list indices; task requirement must be checked.")
    # Do not turn the effect site into a cause, and do not invent a line for
    # missing code or unsupported semantic analysis.
    ranked=sorted(rows.values(),key=lambda r:(-r["score"],r["line"]))[:20]
    for row in ranked:
        row["score"]=round(row["score"],6)
        row["status"]="suspected_location"
        row["causal_verified"]=False
    return {"status":"candidate_locations" if ranked else "insufficient_evidence",
            "source_sha256":graph.get("structure",{}).get("source_sha256"),
            "effect_site":effect,"ranked":ranked,"loop_bounds":bounds,
            "trace_status":execution.get("trace_status","unavailable"),
            "causal_fault_proven":False,
            "scope":"Heuristic evidence ranking, not calibrated probability or root-cause proof. Unrecorded code or missing conditions may be responsible; no unique line is guaranteed."}
