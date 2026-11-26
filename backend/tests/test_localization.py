from algoxray.localization import rank_observations

def test_only_verified_observations_rank():
    bundle = {"status": "witness_found", "trace_status": "complete",
              "events": [{"event_id": "E1", "line": 4}],
              "claims": [{"kind": "source_specific_observation", "verification_status": "verified",
                          "event_ids": ["E1", "missing"]}]}
    assert rank_observations(bundle) == [{"line": 4, "event_ids": ["E1"],
                                         "basis": "verified_observation", "causal_fault_proven": False}]
    bundle["trace_status"] = "truncated"
    assert rank_observations(bundle) == []
