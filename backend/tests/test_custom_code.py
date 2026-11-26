"""End-to-end local pasted-code journeys and evidence boundaries."""
import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from algoxray import api, engine
from algoxray.engine import validate_bundle

SOURCE = """def solve(payload):
    array = payload["array"]
    target = payload["target"]
    left = 0
    right = len(array) - 1
    while left < right:
        mid = (left + right) // 2
        if array[mid] == target:
            return mid
        if array[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "RESULTS", tmp_path)
    return TestClient(api.app)


def analyze(client, source=SOURCE, case=None, options=None):
    token = client.get("/api/session").json()["custom_code_token"]
    return client.post("/api/analyze", headers={"X-AlgoXRay-Token": token},
                       json={"problem_id": "binary_search_v1", "source": source, "trusted_local_code": True,
                             "case": {"array": [7], "target": 7} if case is None else case,
                             "options": options or {"shrink": False}})


def test_paste_to_verified_observation_and_export(client, tmp_path, monkeypatch):
    catalog = api.ROOT / "fixtures/catalog.json"
    before = catalog.read_bytes()
    paths = []
    original = api.local_submission

    def capture(problem_id, path):
        paths.append(path)
        return original(problem_id, path)

    monkeypatch.setattr(api, "local_submission", capture)
    response = analyze(client)
    assert response.status_code == 200, response.text
    bundle = response.json()
    validate_bundle(bundle)
    assert bundle["observed_output"] == -1 and bundle["expected_output"] == 0
    assert bundle["diagnosis"]["status"] == "supported" and bundle["evidence_level"] == "E3"
    assert bundle["diagnosis"]["source_lines"] == [6, 14]
    assert bundle["submission"]["adapter_id"] is None
    assert bundle["submission"]["source"] == SOURCE
    assert bundle["submission"]["source_sha256"] == hashlib.sha256(SOURCE.encode()).hexdigest()
    assert bundle["diagnosis"]["trace_roles"] == {"lower": "left", "upper": "right", "array": "array"}
    assert bundle["verification"]["replay_matches"] == bundle["verification"]["replay_attempts"] == 3
    events = {e["event_id"]: e for e in bundle["events"]}
    observation = bundle["claims"][-1]
    assert observation["adapter_id"] == "python_closed_interval_ast_v1"
    assert all(i in events for i in observation["event_ids"])
    assert events[observation["event_ids"][0]]["locals"]["left"] == 0
    assert catalog.read_bytes() == before
    assert paths and all(not path.exists() for path in paths)
    saved = json.loads((tmp_path / "runs" / bundle["run_id"] / "evidence.json").read_text(encoding="utf-8"))
    assert saved["submission"]["source"] == SOURCE
    assert (tmp_path / "runs" / bundle["run_id"] / "submission.py").read_bytes() == SOURCE.encode("utf-8")


def test_custom_code_is_never_accepted_from_non_loopback_client():
    with TestClient(api.app, client=("203.0.113.8", 4321)) as remote:
        assert remote.get("/api/session").status_code == 403
        response = remote.post("/api/analyze", headers={"X-AlgoXRay-Token": api.custom_code_token},
                               json={"problem_id": "binary_search_v1", "source": SOURCE, "trusted_local_code": True})
        assert response.status_code == 403


def test_different_variable_names_are_traced_and_supported(client):
    source = (SOURCE.replace("payload", "data").replace("array", "items").replace('"items"', '"array"')
              .replace("target", "needle").replace('"needle"', '"target"')
              .replace("left", "begin").replace("right", "finish"))
    bundle = analyze(client, source).json()
    assert bundle["diagnosis"]["status"] == "supported"
    assert bundle["diagnosis"]["trace_roles"]["lower"] == "begin"
    assert any("begin" in e["locals"] and "items" in e["locals"] for e in bundle["events"])


def test_custom_correct_solution_has_no_accusation(client):
    response = analyze(client, SOURCE.replace("while left < right:", "while left <= right:"))
    assert response.status_code == 200
    bundle = response.json()
    assert bundle["status"] == "inconclusive"
    assert not bundle["claims"] and bundle["diagnosis"]["status"] == "unavailable"


def test_custom_unrecognized_wrong_answer_abstains(client):
    bundle = analyze(client, "def solve(payload):\n    return -1\n").json()
    assert bundle["status"] == "witness_found"
    assert bundle["diagnosis"]["status"] == "witness_only"
    assert bundle["evidence_level"] == "E2"
    assert not any(c["kind"] == "source_specific_observation" for c in bundle["claims"])


def test_incomplete_trace_never_gets_ast_diagnosis(client):
    bundle = analyze(client, options={"trace_limit": 1, "shrink": False}).json()
    assert bundle["status"] == "witness_found" and bundle["trace_status"] == "truncated"
    assert bundle["diagnosis"]["status"] == "witness_only"


def test_half_open_interval_is_not_falsely_called_closed_interval_bug(client):
    source = SOURCE.replace("right = len(array) - 1", "right = len(array)").replace("return mid", "return -1")
    bundle = analyze(client, source, case={"array": [1, 7], "target": 7}).json()
    assert bundle["status"] == "witness_found"
    assert bundle["diagnosis"]["status"] == "witness_only"


def test_runtime_exception_points_to_recorded_line(client):
    source = "def solve(payload):\n    items = payload['array']\n    return items[len(items)]\n"
    bundle = analyze(client, source).json()
    assert bundle["failure_kind"] == "exception" and bundle["exception"]["type"] == "IndexError"
    assert bundle["exception"]["line"] == 3
    assert bundle["diagnosis"]["status"] == "supported"
    assert bundle["diagnosis"]["source_lines"] == [3]
    ids = bundle["diagnosis"]["event_ids"]
    assert any(e["event_id"] in ids and e["kind"] == "exception" and e["line"] == 3 for e in bundle["events"])


def test_syntax_and_contract_errors_never_execute_source(client, monkeypatch):
    monkeypatch.setattr(api, "analyze", lambda *a, **kw: pytest.fail("Invalid source reached execution"))
    response = analyze(client, "def solve(payload)\n    return -1\n")
    assert response.status_code == 422
    assert response.json()["detail"]["kind"] == "syntax_error"
    assert response.json()["detail"]["line"] == 1
    assert analyze(client, "print('no solve')").status_code == 422
    assert analyze(client, "async def solve(payload):\n    return -1").status_code == 422


def test_local_trust_and_token_are_both_required(client, monkeypatch):
    monkeypatch.setattr(api, "analyze", lambda *a, **kw: pytest.fail("Untrusted source reached execution"))
    payload = {"problem_id": "binary_search_v1", "source": SOURCE, "trusted_local_code": True}
    assert client.post("/api/analyze", json=payload).status_code == 403
    assert client.post("/api/analyze", headers={"X-AlgoXRay-Token": "wrong"}, json=payload).status_code == 403
    token = client.get("/api/session").json()["custom_code_token"]
    payload["trusted_local_code"] = False
    assert client.post("/api/analyze", headers={"X-AlgoXRay-Token": token}, json=payload).status_code == 403


def test_cross_origin_custom_requests_are_rejected(client):
    payload = {"problem_id": "binary_search_v1", "source": SOURCE, "trusted_local_code": True}
    headers = {"X-AlgoXRay-Token": client.get("/api/session").json()["custom_code_token"], "Origin": "https://other.example"}
    assert client.post("/api/analyze", headers=headers, json=payload).status_code == 403
    headers.pop("Origin")
    headers["Sec-Fetch-Site"] = "cross-site"
    assert client.post("/api/analyze", headers=headers, json=payload).status_code == 403


def test_request_must_choose_one_source_and_limit_size(client):
    payload = {"problem_id": "binary_search_v1", "source": SOURCE, "fixture_id": "binary_correct", "trusted_local_code": True}
    assert client.post("/api/analyze", json=payload).status_code == 422
    assert client.post("/api/analyze", json={"problem_id": "binary_search_v1"}).status_code == 422
    assert analyze(client, SOURCE + "#" * 32769).status_code == 422
    assert client.post("/api/analyze", content=b"x" * 65537).status_code == 413


def test_timeout_does_not_break_next_analysis(client):
    source = "def solve(payload):\n    while True:\n        pass\n"
    bundle = analyze(client, source, options={"shrink": False, "per_case_seconds": 0.03,
                                             "max_seconds": 0.05, "replay_count": 2}).json()
    assert bundle["failure_kind"] == "timeout"
    assert bundle["diagnosis"]["status"] == "witness_only"
    assert client.get("/api/health").status_code == 200
    assert analyze(client).json()["diagnosis"]["status"] == "supported"
