from algoxray.package_review import review_package
from algoxray.problem_registry import REGISTRY
from fastapi.testclient import TestClient
from algoxray.api import app
import pytest

@pytest.mark.parametrize("problem,case,expected",[
    ("binary_search_v1",{"array":[2,2],"target":2},1),
    ("dijkstra_v1",{"n":2,"source":0,"edges":[]},[0,None]),
    ("max_subarray_v1",{"array":[-5,-2]},-2)])
def test_valid_controls(problem,case,expected):
    r=review_package(problem,[{"case":case,"expected":expected}],sample_count=3)
    assert r["status"]=="checks_passed" and r["approval"]=="requires_human_review"
    assert r["checks"]["controls"]==1 and r["checks"]["generated"]==3

def test_invalid_control_fails():
    r=review_package("max_subarray_v1",[{"case":{"array":[-5]},"expected":0}],sample_count=1)
    assert r["status"]=="checks_failed"

def test_review_requires_local_token():
    c=TestClient(app)
    body={"problem_id":"binary_search_v1","controls":[{"case":{"array":[1],"target":1},"expected":0}],"sample_count":1}
    assert c.post("/api/packages/review",json=body).status_code==403
    token=c.get("/api/session").json()["custom_code_token"]
    result=c.post("/api/packages/review",json=body,headers={"X-AlgoXRay-Token":token})
    assert result.status_code==200 and result.json()["status"]=="checks_passed"
