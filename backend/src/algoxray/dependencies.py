"""Read/write evidence for single-line integer assignments only."""
import ast
import operator

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul}
LIMIT = 256

def integer(value):
    return type(value) is int and value.bit_length() <= 1024

def expression(node, values, reads):
    if isinstance(node, ast.Constant) and integer(node.value):
        return node.value
    if isinstance(node, ast.Name) and integer(values.get(node.id)):
        reads[node.id] = values[node.id]
        return values[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        result = OPS[type(node.op)](expression(node.left, values, reads), expression(node.right, values, reads))
        if integer(result): return result
    raise ValueError("Unsupported or missing arithmetic operand")

def assignment_map(source):
    try: tree=ast.parse(source.removeprefix("\ufeff"))
    except (SyntaxError,ValueError,RecursionError): return {}
    statements={}
    for n in ast.walk(tree):
        if isinstance(n,ast.stmt):
            statements.setdefault(n.lineno,[]).append(n)
    return {line: nodes[0] for line,nodes in statements.items()
            if len(nodes)==1 and isinstance(nodes[0],ast.Assign)
            and len(nodes[0].targets)==1 and isinstance(nodes[0].targets[0],ast.Name)
            and nodes[0].end_lineno==line}

def dynamic_dependencies(source, events):
    assignments=assignment_map(source)
    links=[]
    for before,after in zip(events,events[1:]):
        if len(links)>=LIMIT: break
        if before.get("kind")!="line" or after.get("kind")!="line": continue
        if not before.get("frame_id") or before["frame_id"]!=after.get("frame_id"): continue
        statement=assignments.get(before.get("line"))
        if statement is None: continue
        name=statement.targets[0].id
        old,new=before["locals"],after["locals"]
        reads={}
        try: expected=expression(statement.value,old,reads)
        except (ValueError,RecursionError): continue
        if not reads or not integer(new.get(name)) or new[name]!=expected: continue
        links.append({"line":before["line"],"frame_id":before["frame_id"],
                      "before_event_id":before["event_id"],"after_event_id":after["event_id"],
                      "reads":reads,"write":{"name":name,"value":expected},
                      "basis":"consecutive_integer_assignment","causal_fault_proven":False})
    return links
