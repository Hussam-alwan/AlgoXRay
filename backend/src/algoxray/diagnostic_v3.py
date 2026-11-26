"""Additional narrow, source- and witness-bound observations.

No claim of causal fault localization. Rules are deterministic and must abstain
when the required source structure, recorded return or independent math fails.
"""
import ast
from .invariants import root_return

def path_costs(case):
    costs=[set() for _ in range(case["n"])]
    stack=[(case["source"],0,frozenset([case["source"]]))]
    while stack:
        u,cost,seen=stack.pop()
        costs[u].add(cost)
        for a,b,w in case["edges"]:
            if a==u and b not in seen:
                stack.append((b,cost+w,seen|{b}))
    return costs

def graph_observation(bundle):
    e=root_return(bundle)
    if not e: return None
    c,out=bundle["case"],bundle["observed_output"]
    if type(out) is not list or len(out)!=c["n"] or any(v is not None and (type(v) is not int or v<0) for v in out):
        return None
    costs=path_costs(c)
    for i,v in enumerate(out):
        if v is not None and v not in costs[i]:
            return {"event_ids":[e["event_id"]],"source_lines":[e["line"]],
                    "adapter_id":"graph_unattainable_cost_v3",
                    "text":f"عند الإرجاع في السطر {e['line']} سجّل الحل المسافة {v} إلى العقدة {i}، لكن لا يوجد مسار بسيط من المصدر إلى هذه العقدة بهذه الكلفة. الأوزان موجبة، لذا أقصر مسار لا يحتاج إلى دورة.",
                    "direction":"افحص اتجاه الحواف ومصدر قيم المسافات وطريقة جمع أوزان المسار؛ هذه ملاحظة عن الخرج المسجل وليست تحديداً للسطر المسبب."}
    return None

def key_array(node, arg):
    return isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id==arg and isinstance(node.slice,ast.Constant) and node.slice.value=="array"

def same_ast(a,b):
    return ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)

def subarray_observation(bundle,source):
    e=root_return(bundle)
    if not e: return None
    a,out=bundle["case"]["array"],bundle["observed_output"]
    if type(out) is not int: return None
    try: tree=ast.parse(source.removeprefix("\ufeff"))
    except (SyntaxError,ValueError,RecursionError): return None
    funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="solve"]
    if len(funcs)!=1:return None
    fn=funcs[0]
    args=fn.args.posonlyargs+fn.args.args
    if len(args)!=1 or fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs:return None
    if fn.decorator_list or fn.args.defaults or fn.returns or args[0].annotation:return None
    arg=args[0].arg
    if e['locals'].get(arg)!=bundle['case']:return None
    body=fn.body
    if body and isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):body=body[1:]
    # Accept only a direct return, or one array alias followed by a return.
    if len(body)==1:
        arr=ast.Subscript(value=ast.Name(id=arg,ctx=ast.Load()),slice=ast.Constant("array"),ctx=ast.Load())
    elif len(body)==2 and isinstance(body[0],ast.Assign) and len(body[0].targets)==1 and isinstance(body[0].targets[0],ast.Name) and key_array(body[0].value,arg):
        name=body[0].targets[0].id
        if e["locals"].get(name)!=a:return None
        arr=ast.Name(id=name,ctx=ast.Load())
    else:return None
    ret=body[-1]
    if not isinstance(ret,ast.Return) or ret.lineno!=e["line"]:return None
    # Restrict to no extra executable module statements; avoid shadowed builtins.
    if any(n is not fn and not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)) for n in tree.body):
        return None
    if any(isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store) and n.id in {"max","sum","range","len"} for n in ast.walk(fn)) or arg in {"max","sum","range","len"}:return None
    expr=ret.value
    best=max((sum(a[i:j]),i,j) for i in range(len(a)) for j in range(i+1,len(a)+1))
    score,i,j=best
    if out>=score:return None
    mode=None
    if isinstance(expr,ast.Call) and isinstance(expr.func,ast.Name) and expr.func.id=="max" and len(expr.args)==1 and not expr.keywords and same_ast(expr.args[0],arr) and out==max(a):
        mode="single"
    elif isinstance(expr,ast.Call) and isinstance(expr.func,ast.Name) and expr.func.id=="max" and len(expr.args)==1 and not expr.keywords and isinstance(expr.args[0],ast.GeneratorExp):
        gen=expr.args[0]
        if len(gen.generators)==1 and isinstance(gen.generators[0].target,ast.Name):
            idx=gen.generators[0].target.id
            # Construct expected expression using parsed AST and safe identifier substitution.
            expected=ast.parse("max(sum(A[:J]) for J in range(1,len(A)+1))",mode="eval").body
            class Replace(ast.NodeTransformer):
                def visit_Name(self,node):
                    if node.id=="A":return arr
                    if node.id=="J":return ast.Name(id=idx,ctx=node.ctx)
                    return node
            if idx not in {"max","sum","range","len",arg} and (not isinstance(arr,ast.Name) or idx!=arr.id) and same_ast(expr,Replace().visit(expected)) and out==max(sum(a[:k]) for k in range(1,len(a)+1)):
                mode="prefix"
    if mode is None:return None
    text=("يحسب تعبير الإرجاع أكبر عنصر مفرد" if mode=="single" else "يحسب تعبير الإرجاع أكبر مجموع من المقاطع التي تبدأ عند الفهرس صفر")
    return {"event_ids":[e["event_id"]],"source_lines":[e["line"]],
            "adapter_id":"subarray_restricted_candidates_v3",
            "text":f"في السطر {e['line']}، {text}، وأعاد {out}. لكن المقطع المتصل من {i} إلى {j-1} مجموعه {score}، وهو أكبر من القيمة المعادة.",
            "direction":"راجع مجموعة المقاطع التي يفحصها الحل؛ يجب أن يسمح بمقطع متصل غير فارغ يبدأ وينتهي عند أي فهرس صالح."}

def new_observation(bundle,source):
    if bundle.get("evidence_revision")!="option-b.3" or bundle.get("status")!="witness_found" or bundle.get("failure_kind")!="wrong_answer":return None
    if bundle["problem_id"]=="dijkstra_v1":return graph_observation(bundle)
    if bundle["problem_id"]=="max_subarray_v1":return subarray_observation(bundle,source)
    return None
