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
    if rule in {"graph_relaxation_invariant_v1","subarray_attainability_invariant_v1"} and len(linked)==1:
        from .invariants import invariant_observation
        candidate=invariant_observation(bundle)
        return bool(candidate and candidate["adapter_id"]==rule and candidate["event_ids"]==claim["event_ids"] and candidate["source_lines"]==claim["source_lines"])
    if rule == "max_subarray_zero_negative_v1" and len(linked)==1:
        e=linked[0]
        return (bundle["problem_id"]=="max_subarray_v1" and bundle["failure_kind"]=="wrong_answer"
                and max(case["array"])<0 and type(actual) is int and actual==0
                and e["kind"]=="return" and e["function"]=="solve" and type(e.get("return_value")) is int and e["return_value"]==0)
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
            verify_claim_links({**bundle, "claims": [claim]})
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

def verify_published_claims(bundle):
    """Rebuild deterministic published prose; reject free-text tampering.

    This validates recorded evidence, not authenticity of an untrusted recording.
    Actual historical execution must be checked separately by replay.
    """
    from copy import deepcopy
    from types import SimpleNamespace
    from .hints import build_hints
    from .registry import catalog
    from .problem_registry import spec_for
    identity=bundle["submission"]
    adapter=None
    if identity.get("adapter_id"):
        for row in catalog():
            if row["id"]==identity["fixture_id"] and row["sha256"]==identity["source_sha256"] and row.get("adapter")==identity["adapter_id"]:
                adapter=row["adapter"]
                break
        if adapter is None:
            raise ValueError("Unrecognized source-bound adapter")
    if bundle["status"]=="witness_found":
        spec=spec_for(bundle["problem_id"])
        legal=spec.validate(bundle["case"])
        expected=spec.reference(legal)
        if expected!=bundle["expected_output"]:
            raise ValueError("Witness oracle mismatch")
        if bundle["failure_kind"]=="wrong_answer" and spec.check(legal,bundle["observed_output"],expected)!="wrong_answer":
            raise ValueError("Witness does not violate output contract")
    regenerated={**bundle}
    regenerated["claims"],regenerated["hints"]=build_hints(bundle,SimpleNamespace(source=identity["source"],origin=identity["origin"],adapter=adapter))
    abstain_on_unsupported(regenerated)
    if regenerated["claims"]!=bundle["claims"] or regenerated["hints"]!=bundle["hints"]:
        raise ValueError("Published explanation differs from deterministic evidence templates")
    return bundle
