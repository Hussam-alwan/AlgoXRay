"""Bounded language-specific AST projection and source/event anchors.

IDs are stable only for the same source and projection version. A line trace
does not establish which of several expressions on that line executed.
"""
import ast
import hashlib
import re

VERSION=1
MAX_NODES=512
MAX_DEPTH=64

def source_structure(source,events=()):
    identity=hashlib.sha256(source.encode("utf-8")).hexdigest()
    result={"version":VERSION,"language":"python","source_sha256":identity,
            "status":"complete","nodes":[],"event_links":[],"unsupported":[],
            "scope":"Syntactic AST projection; columns are UTF-8 byte offsets, end exclusive. Event links are source-line associations, not proof of expression execution."}
    try:tree=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError) as exc:
        result.update(status="syntax_error" if isinstance(exc,SyntaxError) else "unavailable")
        if isinstance(exc,SyntaxError):result["error"]={"line":exc.lineno,"column":exc.offset,"message":exc.msg[:180]}
        return result
    lines=re.split(r"\r\n?|\n",source)
    encoded=[line.encode("utf-8") for line in lines]
    stack=[(tree,None,"root",None,0,None)]
    while stack:
        node,parent,field,position,depth,scope=stack.pop()
        if len(result["nodes"])>=MAX_NODES:
            result["status"]="partial";break
        node_id="N"+str(len(result["nodes"])+1)
        kind=type(node).__name__
        if isinstance(node,(ast.Module,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda)):scope=node_id
        span=None
        if all(type(getattr(node,k,None)) is int for k in ("lineno","col_offset","end_lineno","end_col_offset")):
            span={"line":node.lineno,"column_utf8":node.col_offset,"end_line":node.end_lineno,"end_column_utf8":node.end_col_offset}
        label=kind
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):label+=" "+node.name
        elif isinstance(node,ast.Name):label+=" "+node.id
        elif isinstance(node,ast.arg):label+=" "+node.arg
        elif isinstance(node,ast.Attribute):label+=" ."+node.attr
        row={"id":node_id,"parent_id":parent,"field":field,"position":position,
             "depth":depth,"scope_id":scope,"kind":kind,"label":label[:120],
             "category":"statement" if isinstance(node,ast.stmt) else "expression" if isinstance(node,ast.expr) else "structure",
             "source_span":span}
        if span and span["line"]==span["end_line"] and 1<=span["line"]<=len(encoded):
            row["preview"]=encoded[span["line"]-1][span["column_utf8"]:span["end_column_utf8"]].decode("utf-8",errors="replace")[:160]
        result["nodes"].append(row)
        if isinstance(node,(ast.AsyncFunctionDef,ast.AsyncFor,ast.AsyncWith,ast.Try,ast.TryStar,ast.Match,ast.ClassDef)):
            result["unsupported"].append({"node_id":node_id,"kind":kind,"scope":"AST represented; comprehensive semantic CFG/dataflow not provided"})
        if depth>=MAX_DEPTH:
            if any(ast.iter_child_nodes(node)):result["status"]="partial"
            continue
        children=[]
        for name,value in ast.iter_fields(node):
            if isinstance(value,ast.AST):children.append((value,node_id,name,None,depth+1,scope))
            elif isinstance(value,list):
                children.extend((child,node_id,name,i,depth+1,scope) for i,child in enumerate(value) if isinstance(child,ast.AST))
        stack.extend(reversed(children))
    statements=[n for n in result["nodes"] if n["category"]=="statement" and n["source_span"]]
    for ev in events:
        if type(ev) is not dict or type(ev.get("line")) is not int or type(ev.get("event_id")) is not str:continue
        line=ev["line"]
        candidates=[n for n in statements if n["source_span"]["line"]==line]
        basis="statement_start"
        if not candidates:
            candidates=[n for n in statements if n["source_span"]["line"]<line<=n["source_span"]["end_line"]]
            if candidates:
                smallest=min(n["source_span"]["end_line"]-n["source_span"]["line"] for n in candidates)
                candidates=[n for n in candidates if n["source_span"]["end_line"]-n["source_span"]["line"]==smallest]
                basis="enclosing_span"
        result["event_links"].append({"event_id":ev["event_id"],"frame_id":ev.get("frame_id"),
            "line":line,"event_kind":ev.get("kind"),"candidate_node_ids":[n["id"] for n in candidates[:8]],
            "association":"unmapped" if not candidates else "ambiguous_line" if len(candidates)>1 else basis,
            "expression_execution_proven":False})
    return result
