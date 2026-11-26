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
