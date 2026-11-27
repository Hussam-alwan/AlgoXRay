"""Generic observed graph, no algorithm-specific branches or invented events."""
def observed_graph(events):
    nodes,edges,changes,prior={}, {}, [], {}
    last=None
    for ev in events:
        if type(ev) is not dict or not all(k in ev for k in ("event_id","frame_id","line","kind","locals")): continue
        if type(ev["event_id"]) is not str or type(ev["frame_id"]) is not str or type(ev["line"]) is not int or type(ev["locals"]) is not dict: continue
        key=f"{ev['frame_id']}:{ev['line']}"
        node=nodes.setdefault(key,{"id":key,"line":ev["line"],"frame_id":ev["frame_id"],"function":ev.get("function"),"event_ids":[]})
        node["event_ids"].append(ev["event_id"])
        if last:
            pair=(last[0],key)
            edge=edges.setdefault(pair,{"from":pair[0],"to":pair[1],"count":0,"event_pairs":[]})
            edge["count"]+=1
            edge["event_pairs"].append([last[1],ev["event_id"]])
        last=(key,ev["event_id"])
        old=prior.get(ev["frame_id"])
        if old:
            before,values=old
            for k,v in ev["locals"].items():
                if k in values and values[k]!=v and not isinstance(v,dict) and not isinstance(values[k],dict):
                    changes.append({"frame_id":ev["frame_id"],"name":k,"before":values[k],"after":v,"before_event_id":before,"after_event_id":ev["event_id"]})
        prior[ev["frame_id"]]=(ev["event_id"],ev["locals"])
    return {"kind":"observed_execution_not_static_cfg","nodes":list(nodes.values()),"edges":list(edges.values()),"changes":changes,
            "causal_fault_proven":False}
