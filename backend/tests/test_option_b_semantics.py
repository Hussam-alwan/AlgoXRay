from algoxray.claim_verifier import abstain_on_unsupported
from algoxray.engine import analyze, Options
from algoxray.registry import get_submission

def test_correct_dijkstra_unreachable_is_not_failure():
    result = analyze(get_submission("dijkstra_correct"), Options(shrink=False),
                     case={"n": 2, "edges": [], "source": 0}, persist=False)
    assert result["status"] == "inconclusive"
    assert result["manual_check"]["observed"] == [0, None]

def test_unsupported_claim_is_removed():
    bundle = {"case": {"array": [1], "target": 1}, "observed_output": -1,
              "events": [{"event_id": "E1", "kind": "line", "locals": {"lo": 1, "hi": 1}}],
              "claims": [{"claim_id": "C2", "kind": "source_specific_observation",
                          "adapter_id": "binary_last_v1", "event_ids": ["E1"]}],
              "hints": [{"claim_ids": ["C2"]}]}
    abstain_on_unsupported(bundle)
    assert bundle["claims"] == bundle["hints"] == []
    assert bundle["claim_verification"]["rejected_ids"] == ["C2"]
