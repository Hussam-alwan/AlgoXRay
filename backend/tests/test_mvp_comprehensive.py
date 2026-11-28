import copy
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from algoxray.v4_api import router_for
from algoxray.v4_contracts import PackageStore,digest
from algoxray.v4_engine import analyze_package
from algoxray import v4_api,v4_observation

P={"manifest":{"id":"comprehensive","title":"Double","statement":"Read n and print its double.",
   "fields":[{"name":"n","kind":"int","min":0,"max":9}],"lines":[["n"]],"output":"tokens"},
   "reference":"n=int(input())\nprint(2*n)\n",
   "controls":[{"case":{"n":0},"expected":"0"},{"case":{"n":1},"expected":"2"}]}
CORRECT="n=int(input())\nprint(n+n)\n"
BAD="n=int(input())\nprint(n)\n"
HEADERS={"X-AlgoXRay-Token":"test"}

def fixture_client(monkeypatch,tmp_path):
    monkeypatch.setenv("ALGOXRAY_V4_PACKAGE_STORE",str(tmp_path/"packages"))
    app=FastAPI();app.include_router(router_for(lambda req:None,"test"))
    return TestClient(app),PackageStore(tmp_path/"packages")

def test_preflight_never_runs_or_approves(monkeypatch,tmp_path):
    client,store=fixture_client(monkeypatch,tmp_path)
    def forbidden(*args,**kwargs):
        pytest.fail("Preflight must never execute a reference")
    monkeypatch.setattr(v4_api,"review",forbidden)
    assert client.post("/api/v4/packages/preflight",json={"package":P}).status_code==403
    response=client.post("/api/v4/packages/preflight",json={"package":P,"owner_reviewed":True},headers=HEADERS)
    assert response.status_code==200 and response.json()["already_approved"] is False
    assert response.json()["key"]==digest(P)
    assert store.list()==[]
    assert client.post("/api/v4/packages/approve",json={"package":P},headers=HEADERS).status_code==403
    invalid=copy.deepcopy(P);invalid["controls"]=[]
    assert client.post("/api/v4/packages/preflight",json={"package":invalid},headers=HEADERS).status_code==422
    store.save(P)
    assert client.post("/api/v4/packages/preflight",json={"package":P},headers=HEADERS).json()["already_approved"] is True
    different=copy.deepcopy(P);different["reference"]=CORRECT
    assert client.post("/api/v4/packages/preflight",json={"package":different},headers=HEADERS).json()["already_approved"] is False

def test_exact_case_benchmark_requires_approved_package_and_review(monkeypatch,tmp_path):
    client,store=fixture_client(monkeypatch,tmp_path)
    key=store.save(P);calls=[]
    def bench(source,inputs,**kw):
        calls.append((source,inputs,kw))
        return {"status":"benchmark_observation","analysis_id":kw["run_id"]}
    monkeypatch.setattr(v4_observation,"benchmark_source",bench)
    body={"package_key":key,"case":{"n":3},"source":CORRECT,"analysis_id":"a"*32}
    assert client.post("/api/v4/benchmark",json=body,headers=HEADERS).status_code==403
    body["trusted_local_source"]=True
    for change in [{"case":{"n":10}},{"stdin":"3\n"},{"size_field":"n","sizes":[1,2]},{"package_key":"0"*64},{"package_key":None}]:
        assert client.post("/api/v4/benchmark",json={**body,**change},headers=HEADERS).status_code==422
    assert not calls
    response=client.post("/api/v4/benchmark",json=body,headers=HEADERS)
    assert response.status_code==200
    assert calls[0][1]==[{"size":None,"case":{"n":3},"stdin":"3\n"}]
    assert calls[0][2]["package"]==P and calls[0][2]["size_field"] is None

def test_example_reuses_search_trace_without_extra_execution():
    calls=[]
    def worker(src,stdin,trace_limit):
        calls.append((src,stdin,trace_limit))
        return {"status":"ok","stdout":str(int(stdin)*(1 if src==BAD else 2)),"events":[],
                "trace_status":"complete","elapsed_ms":1}
    standard=analyze_package(P,CORRECT,case={"n":3},run=worker)
    assert standard["status"]=="no_witness_found" and "example_observation" not in standard
    assert [c[2] for c in calls]==[0,0]
    calls.clear()
    full=analyze_package(P,CORRECT,case={"n":3},run=worker,capture_example=True)
    assert full["status"]=="no_witness_found" and full["run_report"]["physical_executions"]==2
    assert [c[2] for c in calls]==[128,128]
    sample=full["example_observation"]
    assert sample["reused_search_trace"] is True and sample["kind"]=="match" and sample["replay_count"]==0
    assert sample["witness"]["case"]=={"n":3}
    calls.clear()
    failure=analyze_package(P,BAD,case={"n":3},reduce_calls=0,run=worker,capture_example=True)
    assert failure["status"]=="observed_mismatch" and failure["replay_count"]==3
    assert "example_observation" not in failure and len(calls)==8
