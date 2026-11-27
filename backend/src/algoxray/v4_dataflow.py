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
    except (SyntaxError,RecursionError,ValueError):return {"data":[],"control":[]}
    stmts={}
    for n in ast.walk(tree):
        if isinstance(n,ast.stmt):stmts.setdefault(n.lineno,[]).append(n)
    data,control=[],[]
    previous={}
    for after in events:
        if after.get("kind")!="line":continue
        frame=after.get("frame_id")
        before=previous.get(frame);previous[frame]=after
        if not before:continue
        ns=stmts.get(before.get("line"),[])
        if len(ns)!=1:continue
        n=ns[0];old,new=before.get("locals",{}),after.get("locals",{})
        if type(old) is not dict or type(new) is not dict:continue
        reads={}
        try:
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.end_lineno==n.lineno:
                name=n.targets[0].id;v=evaluate(n.value,old,reads)
            elif isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name) and type(n.op) in OPS and n.end_lineno==n.lineno:
                name=n.target.id;v=OPS[type(n.op)](evaluate(n.target,old,reads),evaluate(n.value,old,reads))
            elif isinstance(n,(ast.If,ast.While)):
                value=evaluate(n.test,old,reads)
                target=n.body[0].lineno if bool(value) else n.orelse[0].lineno if n.orelse else None
                if target!=after.get("line") or target==n.lineno:continue
                control.append({"line":n.lineno,"condition":bool(value),"reads":reads,"target_line":target,
                                "before_event_id":before["event_id"],"after_event_id":after["event_id"],"frame_id":frame})
                continue
            else:continue
            if reads and scalar(v) and scalar(new.get(name)) and type(v) is type(new[name]) and v==new[name]:
                data.append({"line":n.lineno,"reads":reads,"write":{"name":name,"value":v},"frame_id":frame,
                             "before_event_id":before["event_id"],"after_event_id":after["event_id"]})
        except (ValueError,ArithmeticError,RecursionError):continue
    return {"data":data[:128],"control":control[:128]}
