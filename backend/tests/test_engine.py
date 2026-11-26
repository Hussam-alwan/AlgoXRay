from copy import deepcopy
from dataclasses import replace
from algoxray.problem_registry import REGISTRY
import json

import jsonschema
import pytest

from algoxray import engine
from algoxray.engine import Options, analyze, validate_bundle
from algoxray.paths import ROOT
from algoxray.problems import OracleDisagreement, PROBLEMS, complexity
from algoxray.registry import get_submission, local_submission
from algoxray.tracing import safe_value


@pytest.fixture
def graph_bundle():
    return analyze(get_submission("dijkstra_premature_visited"), Options(),
                   case=PROBLEMS["dijkstra_v1"]["example"], persist=False)


def test_verified_dijkstra_trace_and_source_specific_hint(graph_bundle):
    r = graph_bundle
    assert r["status"] == "witness_found"
    assert r["observed_output"] == [0, 1, 3] and r["expected_output"] == [0, 1, 2]
    assert r["evidence_level"] == "E3"
    assert r["verification"]["replay_matches"] == 3
    assert r["submission"]["source_sha256"] == get_submission("dijkstra_premature_visited").sha256
    diagnostic = r["claims"][1]
    event = next(e for e in r["events"] if e["event_id"] in diagnostic["event_ids"])
    assert event["locals"]["v"] in event["locals"]["seen"]
    assert event["locals"]["d"] + event["locals"]["w"] < event["locals"]["dist"][event["locals"]["v"]]
    jsonschema.validate(r, json.loads((ROOT / "contracts/evidence.schema.json").read_text()))


def test_generated_witness_and_minimization():
    r = analyze(get_submission("dijkstra_premature_visited"), Options(max_examples=150), persist=False)
    assert r["status"] == "witness_found"
    assert complexity(r["problem_id"], r["case"]) <= complexity(r["problem_id"], r["original_case"])
    assert r["reduction"]["method"] == "hypothesis"
    assert r["verification"]["replay_matches"] == r["verification"]["replay_attempts"]


def test_correct_control_is_inconclusive_not_proven():
    r = analyze(get_submission("dijkstra_correct"), Options(max_examples=12, include_trace=False, shrink=False), persist=False)
    assert r["status"] == "inconclusive" and not r["hints"] and r["case"] is None
    assert r["statistics"]["discovery_candidates"] <= 12


def test_binary_singleton_trace():
    r = analyze(get_submission("binary_missing_last"), Options(), case={"array": [0], "target": 0}, persist=False)
    assert r["evidence_level"] == "E3" and r["observed_output"] == -1
    assert r["expected_output"] == 0
    assert any(e["locals"].get("lo") == e["locals"].get("hi") == 0 for e in r["events"])


def test_source_without_adapter_abstains():
    r = analyze(get_submission("dijkstra_reversed_edges"), Options(),
                case={"n": 2, "edges": [[0, 1, 1]], "source": 0}, persist=False)
    assert r["status"] == "witness_found" and r["evidence_level"] == "E2"
    assert r["diagnostic_status"] == "abstained" and len(r["hints"]) == 2


def test_changed_source_disables_adapter(tmp_path):
    original = get_submission("dijkstra_premature_visited")
    p = tmp_path / "same_algorithm.py"
    p.write_text(original.source, encoding="utf-8")
    sub = local_submission("dijkstra_v1", p)
    r = analyze(sub, Options(), case=PROBLEMS["dijkstra_v1"]["example"], persist=False)
    assert r["status"] == "witness_found" and r["evidence_level"] == "E2"
    assert not any(c["kind"] == "source_specific_observation" for c in r["claims"])


def test_trace_truncation_keeps_witness_and_abstains():
    r = analyze(get_submission("dijkstra_premature_visited"), Options(trace_limit=2),
                case=PROBLEMS["dijkstra_v1"]["example"], persist=False)
    assert r["status"] == "witness_found" and r["trace_status"] == "truncated"
    assert len(r["events"]) == 2 and r["evidence_level"] == "E2"


def test_claim_cannot_refer_to_missing_event(graph_bundle):
    tampered = deepcopy(graph_bundle)
    tampered["claims"][1]["event_ids"] = ["invented"]
    with pytest.raises(ValueError, match="missing event"):
        validate_bundle(tampered)


def test_snapshot_is_independent_and_strict_json():
    live = {"dist": [0, float("inf"), 4]}
    snapshot = safe_value(live)
    live["dist"][1] = 2
    assert snapshot["dist"] == [0, None, 4]
    json.dumps(snapshot, allow_nan=False)


def test_oracle_disagreement_never_accuses(monkeypatch):
    def disagree(*_):
        raise OracleDisagreement("test disagreement")
    monkeypatch.setitem(REGISTRY, "dijkstra_v1", replace(REGISTRY["dijkstra_v1"], reference=disagree))
    r = analyze(get_submission("dijkstra_correct"), Options(), case=PROBLEMS["dijkstra_v1"]["example"], persist=False)
    assert r["status"] == "oracle_disagreement" and not r["claims"]


@pytest.mark.parametrize("kwargs", [{"seed": True}, {"max_examples": 0}, {"trace_limit": 9999},
                                   {"strategy": "unknown"}, {"per_case_seconds": float("nan")}])
def test_invalid_options_rejected(kwargs):
    with pytest.raises(ValueError):
        Options(**kwargs)


def test_external_quixbugs_recursion_is_exception_not_wrong_answer():
    sub = get_submission("quixbugs_find_in_sorted")
    r = analyze(sub, Options(shrink=False), case={"array": [0], "target": 1}, persist=False)
    assert sub.origin == "quixbugs_curated_benchmark"
    assert r["failure_kind"] == "exception" and r["exception"]["type"] == "RecursionError"
    assert r["expected_output"] == -1 and len(r["hints"]) == 1


def test_unstable_submission_does_not_produce_confirmed_witness(tmp_path):
    p = tmp_path / "unstable.py"
    p.write_text("from pathlib import Path\ndef solve(payload):\n    counter_file = Path(__file__).with_suffix('.counter')\n    count = int(counter_file.read_text()) + 1 if counter_file.exists() else 1\n    counter_file.write_text(str(count))\n    return [100 + count, 0, 0]\n", encoding="utf-8")
    r = analyze(local_submission("dijkstra_v1", p), Options(shrink=False),
                case=PROBLEMS["dijkstra_v1"]["example"], persist=False)
    assert r["status"] == "inconclusive" and not r["claims"]
    assert r["statistics"]["flaky_candidates"] == 1
