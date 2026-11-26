"""Rank recorded observations without claiming causal fault localization."""
from collections import defaultdict


def rank_observations(bundle):
    if bundle.get("status") != "witness_found" or bundle.get("trace_status") != "complete":
        return []
    events = {event["event_id"]: event for event in bundle.get("events", [])}
    grouped = defaultdict(set)
    for claim in bundle.get("claims", []):
        if claim.get("kind") != "source_specific_observation" or claim.get("verification_status") != "verified":
            continue
        for event_id in claim.get("event_ids", []):
            event = events.get(event_id)
            if event and type(event.get("line")) is int and event["line"] > 0:
                grouped[event["line"]].add(event_id)
    return [{"line": line, "event_ids": sorted(ids), "basis": "verified_observation",
             "causal_fault_proven": False}
            for line, ids in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))]
