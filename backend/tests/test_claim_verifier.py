import pytest
from algoxray.claim_verifier import verify_claim_links

def test_reject_unrecorded_line():
    bundle = {"trace_status": "complete", "events": [{"event_id": "E1", "line": 2}],
              "claims": [{"kind": "source_specific_observation", "event_ids": ["E1"], "source_lines": [3]}]}
    with pytest.raises(ValueError):
        verify_claim_links(bundle)

def test_accept_recorded_line():
    bundle = {"trace_status": "complete", "events": [{"event_id": "E1", "line": 2}],
              "claims": [{"kind": "source_specific_observation", "event_ids": ["E1"], "source_lines": [2]}]}
    assert verify_claim_links(bundle) is bundle
