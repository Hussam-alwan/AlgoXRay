"""Restricted syntactic CFG and conservative observed output-compatible dependency chain."""
import ast

def static_cfg(source):
    try:t=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError):return {"status":"unavailable","nodes":[],"edges":[]}
    nodes={};edges=[];unsupported=[]
    def block(stmts,scope,follow=None):
        for i,n in enumerate(stmts):
            nxt=stmts[i+1].lineno if i+1<len(stmts) else follow
            key=scope+":"+str(n.lineno)
            nodes[key]={"id":key,"line":n.lineno,"scope":scope,"kind":type(n).__name__}
            def edge(target,label):
                if target is not None and target!=n.lineno:edges.append({"from":key,"to":scope+":"+str(target),"kind":label})
            if isinstance(n,ast.If):
                edge(n.body[0].lineno,"condition_true");edge(n.orelse[0].lineno if n.orelse else nxt,"condition_false")
                block(n.body,scope,nxt);block(n.orelse,scope,nxt)
            elif isinstance(n,(ast.While,ast.For)):
                if any(isinstance(z,(ast.Break,ast.Continue,ast.Try,ast.With,ast.AsyncFor)) for z in ast.walk(n)):
                    unsupported.append(key);continue
                edge(n.body[0].lineno,"loop_body");edge(n.orelse[0].lineno if n.orelse else nxt,"loop_exit")
                block(n.body,scope,n.lineno);block(n.orelse,scope,nxt)
            elif isinstance(n,ast.FunctionDef):
                if n.decorator_list:unsupported.append(key);continue
                edge(nxt,"next");block(n.body,scope+"/"+n.name+"@"+str(n.lineno))
            elif isinstance(n,(ast.Return,ast.Raise)):pass
            elif isinstance(n,(ast.Assign,ast.AugAssign,ast.AnnAssign,ast.Expr,ast.Pass,ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.Assert)):edge(nxt,"next")
            else:unsupported.append(key)
    block(t.body,"module")
    edges=[e for e in edges if e["to"] in nodes]
    return {"status":"restricted_syntactic_cfg","nodes":list(nodes.values())[:256],"edges":edges[:256],"unsupported":unsupported[:256],"scope":"Syntactic successors only, no runtime reachability or call/exception proof."}

def output_chain(source,result,graph):
    """Only a single simple print(name) matching one stdout value; no causal claim."""
    try:t=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError):return {"status":"unsupported","links":[]}
    prints=[n for n in ast.walk(t) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=="print"]
    if len(prints)!=1:return {"status":"unsupported","links":[]}
    p=prints[0];call=p.value
    if len(call.args)!=1 or call.keywords or not isinstance(call.args[0],ast.Name):return {"status":"unsupported","links":[]}
    name=call.args[0].id
    events=[e for e in result.get("events",[]) if e.get("kind")=="line" and e.get("line")==p.lineno]
    if len(events)!=1:return {"status":"unsupported","links":[]}
    ev=events[0];value=ev.get("locals",{}).get(name)
    if type(value) not in (int,bool,str) or result.get("stdout")!=str(value)+"\n":return {"status":"unsupported","links":[]}
    rel=graph.get("relations",{});data=rel.get("data",[]);uses=rel.get("def_use",[])
    producer=next((x for x in data if x["after_event_id"]==ev["event_id"] and x["frame_id"]==ev["frame_id"] and x["write"]["name"]==name and type(x["write"]["value"]) is type(value) and x["write"]["value"]==value),None)
    chain=[];queue=[producer] if producer else [];seen=set()
    while queue and len(chain)<32:
        x=queue.pop(0);key=x["after_event_id"]
        if key in seen:continue
        seen.add(key);chain.append(x)
        for u in uses:
            if u["consumer_event_id"]==x["before_event_id"]:
                queue.extend(y for y in data if y["after_event_id"]==u["producer_event_id"])
    return {"status":"snapshot_compatible_with_stdout","output_event_id":ev["event_id"],"variable":name,"value":value,"links":chain,"causal_verified":False,"scope":"Partial observed predecessor chain, not proof that print is built-in or that the chain caused the output."}
