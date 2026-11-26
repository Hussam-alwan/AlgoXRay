import json

from fastapi.testclient import TestClient
import pytest

from algoxray import engine
from algoxray.api import app, analysis_lock


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "RESULTS", tmp_path)
    return TestClient(app)


def test_health_source_catalog_and_offline_ui(client):
    assert client.get("/api/health").json()["status"] == "ready"
    assert {p["id"] for p in client.get("/api/problems").json()} == {"dijkstra_v1", "binary_search_v1", "max_subarray_v1"}
    fixtures = client.get("/api/fixtures").json()
    assert len(fixtures) >= 7 and all("source_sha256" in f for f in fixtures)
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/vendor/cytoscape.min.js").status_code == 200
    assert client.get("/docs").status_code == 200


def test_api_to_exportable_evidence_journey(client):
    r = client.post("/api/analyze", json={"problem_id": "binary_search_v1", "fixture_id": "binary_missing_last",
                                         "case": {"array": [0], "target": 0}})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "witness_found" and data["expected_output"] == 0
    assert data["hints"][2]["event_ids"]
    assert "Infinity" not in json.dumps(data)


def test_public_code_and_unknown_fields_rejected(client):
    r = client.post("/api/analyze", json={"problem_id": "dijkstra_v1", "fixture_id": "dijkstra_correct", "source": "print('not executed')"})
    assert r.status_code == 422
    r = client.post("/api/analyze", json={"problem_id": "dijkstra_v1", "fixture_id": "../../file"})
    assert r.status_code == 422


def test_bad_case_is_not_a_student_failure(client):
    r = client.post("/api/analyze", json={"problem_id": "dijkstra_v1", "fixture_id": "dijkstra_correct", "case": {"n": 1}})
    assert r.status_code == 422


def test_cross_origin_and_rebound_host_rejected(client):
    assert client.post("/api/analyze", json={}, headers={"Origin": "https://other.example"}).status_code == 403
    assert client.get("/api/health", headers={"Host": "other.example"}).status_code == 400


def test_concurrent_run_receives_busy_response(client):
    analysis_lock.acquire()
    try:
        r = client.post("/api/analyze", json={"problem_id": "dijkstra_v1", "fixture_id": "dijkstra_correct"})
        assert r.status_code == 409
    finally:
        analysis_lock.release()

def test_max_subarray_api_witness(client):
    response = client.post("/api/analyze", json={"problem_id": "max_subarray_v1",
        "fixture_id": "max_subarray_empty_bug", "case": {"array": [-2]},
        "options": {"shrink": False}})
    assert response.status_code == 200
    bundle = response.json()
    assert bundle["failure_kind"] == "wrong_answer"
    assert bundle["witness_explanation"]["sum"] == -2
    assert bundle["evidence_revision"] == "option-b.3"

def test_option_b_summary_not_run(client, monkeypatch, tmp_path):
    from algoxray import api
    monkeypatch.setattr(api,"RESULTS",tmp_path)
    assert client.get("/api/option-b/benchmark-summary").json()["status"] == "not_run"

def test_unregistered_problem_rejected(client):
    response = client.post("/api/analyze", json={"problem_id": "unknown", "fixture_id": "binary_correct"})
    assert response.status_code == 422
