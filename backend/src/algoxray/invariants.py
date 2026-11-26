"""Witness-derived output invariants with an actual recorded solve return.

These are verified symptoms at a program point, never causal fault locations.
They do not assume a particular implementation or variable naming convention.
"""
def root_return(bundle):
    events=bundle.get("events",[])
    if bundle.get("trace_status")!="complete" or not events: return None
    event=events[-1]
    if event.get("kind")!="return" or event.get("function")!="solve" or event.get("parent_frame_id") is not None:
        return None
    if event.get("return_value")!=bundle.get("observed_output"): return None
    return event

def graph_violation(case,dist):
    if type(dist) is not list or len(dist)!=case["n"] or any(v is not None and (type(v) is not int or v<0) for v in dist): return None
    for u,v,w in case["edges"]:
        if dist[u] is not None and (dist[v] is None or dist[v]>dist[u]+w):
            return u,v,w
    return None

def attainable_sum(case,actual):
    a=case["array"]
    return any(sum(a[i:j])==actual for i in range(len(a)) for j in range(i+1,len(a)+1))

def invariant_observation(bundle):
    if bundle.get("failure_kind")!="wrong_answer" or bundle.get("status")!="witness_found": return None
    event=root_return(bundle)
    if not event: return None
    case,actual=bundle["case"],bundle["observed_output"]
    line=event["line"]
    if bundle["problem_id"]=="dijkstra_v1":
        edge=graph_violation(case,actual)
        if edge:
            u,v,w=edge
            value="غير قابلة للوصول" if actual[v] is None else str(actual[v])
            return {"event_ids":[event["event_id"]],"source_lines":[line],
                    "text":f"في النتيجة المسجلة عند السطر {line}، المسافة إلى {u} تساوي {actual[u]}، والحافة {u} → {v} وزنها {w}، لكن المسافة إلى {v} هي {value}. شرط التحديث يقتضي ألا تتجاوز {actual[u]+w}.",
                    "direction":"تتبّع هذه الحافة وافحص هل تُحدَّث المسافة من عقدة سبق الوصول إليها. هذا خرق للشرط عند الإرجاع، وليس تحديداً للسبب الجذري.",
                    "adapter_id":"graph_relaxation_invariant_v1"}
    if bundle["problem_id"]=="max_subarray_v1" and type(actual) is int and not attainable_sum(case,actual):
        return {"event_ids":[event["event_id"]],"source_lines":[line],
                "text":f"في السطر {line} أعاد الحل {actual}، مع أن تعداد جميع المقاطع المتصلة غير الفارغة يثبت أن أياً منها لا يملك هذا المجموع.",
                "direction":"افحص ما إذا كان المجموع الذي تجمعه يمثل مقطعاً واحداً متصلاً وغير فارغ. لا يُحدد حدث الإرجاع وحده موضع السبب.",
                "adapter_id":"subarray_attainability_invariant_v1"}
    return None
