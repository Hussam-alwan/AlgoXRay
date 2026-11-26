"""Structural evidence validation; does not establish semantic or causal truth."""
def verify_claim_links(bundle):
    events = {event["event_id"]: event for event in bundle["events"]}
    for claim in bundle["claims"]:
        if claim["kind"] != "source_specific_observation":
            continue
        ids = claim.get("event_ids", [])
        if bundle["trace_status"] != "complete" or not ids or any(i not in events for i in ids):
            raise ValueError("Specific observation lacks complete trace evidence")
        recorded = {events[i]["line"] for i in ids}
        if not set(claim.get("source_lines", [])) <= recorded:
            raise ValueError("Observation cites an unrecorded source line")
    return bundle

def semantic_observation_valid(bundle, claim):
    """Independently check the narrow rule predicates against recorded values."""
    events = {e["event_id"]: e for e in bundle["events"]}
    linked = [events[i] for i in claim["event_ids"]]
    rule = claim.get("adapter_id")
    case = bundle["case"]
    actual = bundle["observed_output"]
    if rule == "python_exception_location_v1" and len(linked) == 1:
        e, exc = linked[0], bundle["exception"]
        return e["kind"] == "exception" and all(e.get(k) == exc.get(v) for k,v in
            (("line","line"),("function","function"),("exception_type","type")))
    if rule == "python_returned_index_v1" and len(linked) == 1:
        e = linked[0]
        a, t = case["array"], case["target"]
        return (type(actual) is int and actual != -1 and e["kind"] == "return"
                and e["function"] == "solve" and e.get("return_value") == actual
                and not (0 <= actual < len(a) and a[actual] == t))
    if rule == "python_closed_interval_ast_v1" and len(linked) == 2:
        a, b = linked
        roles = claim.get("trace_roles") or {}
        lo, hi = roles.get("lower"), roles.get("upper")
        i = b["locals"].get(lo)
        return (a.get("frame_id") == b.get("frame_id") and a["kind"] == b["kind"] == "line"
                and type(i) is int and i == b["locals"].get(hi) == a["locals"].get(lo) == a["locals"].get(hi)
                and 0 <= i < len(case["array"]) and case["array"][i] == case["target"] and actual == -1)
    if rule == "binary_last_v1" and len(linked) == 1:
        e = linked[0]
        v = e["locals"]
        i = v.get("lo")
        return (e["kind"] == "line" and type(i) is int and i == v.get("hi")
                and 0 <= i < len(case["array"]) and case["array"][i] == case["target"] and actual == -1)
    if rule == "dijkstra_seen_v1" and len(linked) == 1:
        e = linked[0]
        v = e["locals"]
        u, dest, d, w = (v.get(k) for k in ("u", "v", "d", "w"))
        dist, seen = v.get("dist"), v.get("seen")
        return (e["kind"] == "line" and all(type(x) is int for x in (u,dest,d,w))
                and [u,dest,w] in case["edges"] and type(dist) is list and type(seen) is list
                and 0 <= dest < len(dist) and dest in seen and type(dist[dest]) is int and d+w < dist[dest])
    return False


def abstain_on_unsupported(bundle):
    """Remove unverified specific claims and dependent hints, retain the witness."""
    rejected = set()
    for claim in bundle["claims"]:
        if claim["kind"] != "source_specific_observation":
            continue
        try:
            valid = semantic_observation_valid(bundle, claim)
        except (KeyError, IndexError, TypeError, ValueError):
            valid = False
        if not valid:
            rejected.add(claim["claim_id"])
    rejected_candidates = [{**c, "verification_status": "rejected"} for c in bundle["claims"] if c["claim_id"] in rejected]
    bundle["claims"] = [c for c in bundle["claims"] if c["claim_id"] not in rejected]
    bundle["hints"] = [h for h in bundle["hints"] if not rejected.intersection(h["claim_ids"])]
    bundle["claim_verification"] = {"rejected_ids": sorted(rejected), "method": "rule_predicates_v1",
                                    "rejected_candidates": rejected_candidates}
    return bundle
