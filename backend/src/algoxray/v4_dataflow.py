"""Conservative source/trace relations for a documented integer/boolean subset."""
import ast
import operator

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod}
CMP={ast.Lt:operator.lt,ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge,ast.Eq:operator.eq,ast.NotEq:operator.ne}
def scalar(v):return type(v) is bool or type(v) is int and v.bit_length()<=256
def evaluate(node,env,reads):
    if isinstance(node,ast.Constant) and scalar(node.value):return node.value
    if isinstance(node,ast.Name) and scalar(env.get(node.id)):
        reads[node.id]=env[node.id];return env[node.id]
    if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name):
        a=env.get(node.value.id);i=evaluate(node.slice,env,reads)
        if type(a) is not list or type(i) is not int or not -len(a)<=i<len(a) or not scalar(a[i]):raise ValueError("Unsupported indexed value")
        reads[f"{node.value.id}[{i}]"]=a[i];return a[i]
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub,ast.Not)):
        a=evaluate(node.operand,env,reads)
        v=+a if isinstance(node.op,ast.UAdd) else -a if isinstance(node.op,ast.USub) else not a
    elif isinstance(node,ast.BinOp) and type(node.op) in OPS:
        v=OPS[type(node.op)](evaluate(node.left,env,reads),evaluate(node.right,env,reads))
    elif isinstance(node,ast.Compare) and len(node.ops)==1 and type(node.ops[0]) in CMP:
        v=CMP[type(node.ops[0])](evaluate(node.left,env,reads),evaluate(node.comparators[0],env,reads))
    else:raise ValueError("Unsupported expression")
    if not scalar(v):raise ValueError("Unsupported result")
    return v

def relations(source,events):
    try:tree=ast.parse(source)
    except (SyntaxError,RecursionError,ValueError):return {"data":[],"control":[],"def_use":[]}
    stmts={}
    for n in ast.walk(tree):
        if isinstance(n,ast.stmt):stmts.setdefault(n.lineno,[]).append(n)
    data,control,links=[],[],[]
    producers={}
    previous={}
    for after in events:
        if after.get("kind")!="line":continue
        frame=after.get("frame_id")
        before=previous.get(frame);previous[frame]=after
        if not before:continue
        prod=producers.setdefault(frame,{})
        ns=stmts.get(before.get("line"),[])
        if len(ns)!=1:prod.clear();continue
        n=ns[0];old,new=before.get("locals",{}),after.get("locals",{})
        if type(old) is not dict or type(new) is not dict:prod.clear();continue
        for name in list(prod):
            if name not in old or type(old[name]) is not type(prod[name]["value"]) or old[name]!=prod[name]["value"]:prod.pop(name)
        reads={}
        try:
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.end_lineno==n.lineno:
                name=n.targets[0].id;v=evaluate(n.value,old,reads)
            elif isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name) and type(n.op) in OPS and n.end_lineno==n.lineno:
                name=n.target.id;v=OPS[type(n.op)](evaluate(n.target,old,reads),evaluate(n.value,old,reads))
            elif isinstance(n,(ast.If,ast.While)):
                value=evaluate(n.test,old,reads)
                target=n.body[0].lineno if bool(value) else n.orelse[0].lineno if n.orelse else None
                if target!=after.get("line") or target==n.lineno:prod.clear();continue
                control.append({"line":n.lineno,"condition":bool(value),"reads":reads,"target_line":target,
                                "before_event_id":before["event_id"],"after_event_id":after["event_id"],"frame_id":frame})
                continue
            else:prod.clear();continue
            if reads and scalar(v) and scalar(new.get(name)) and type(v) is type(new[name]) and v==new[name]:
                relation={"line":n.lineno,"reads":reads,"write":{"name":name,"value":v},"frame_id":frame,"before_event_id":before["event_id"],"after_event_id":after["event_id"]}
                data.append(relation)
                for read,value in reads.items():
                    previous_write=prod.get(read)
                    if previous_write and type(previous_write["value"]) is type(value) and previous_write["value"]==value:
                        links.append({"name":read,"value":value,"frame_id":frame,"producer_event_id":previous_write["event_id"],"consumer_event_id":before["event_id"],"consumer_line":n.lineno,"status":"supported_observed_dependency"})
                prod[name]={"value":v,"event_id":after["event_id"]}
            else:prod.pop(name,None)
        except (ValueError,ArithmeticError,RecursionError):prod.clear();continue
    return {"data":data[:128],"control":control[:128],"def_use":links[:128]}
