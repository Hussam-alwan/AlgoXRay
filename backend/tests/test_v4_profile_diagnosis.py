import copy
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from algoxray.v4_contracts import PackageStore
from algoxray.v4_provider import ProviderError
from test_v4_execution_diagnostics import SOURCE,stalled

@pytest.fixture
def setup_profile(monkeypatch,tmp_path):
    from algoxray import v4_api
    monkeypatch.setenv("ALGOXRAY_V4_PACKAGE_STORE",str(tmp_path))
    package={"manifest":{"id":"profile","title":"profile","statement":"Print n","fields":[{"name":"n","kind":"int","min":1,"max":4}],"lines":[["n"]],"output":"tokens"},"reference":"print(int(input()))",
        "controls":[{"case":{"n":1},"expected":"1"},{"case":{"n":4},"expected":"4"}]}
    key=PackageStore(tmp_path).save(package);calls=[]
    def run(source,stdin,**kwargs):
        calls.append(source)
        if source==package["reference"]:return {"status":"ok","stdout":stdin,"events":[],"trace_status":"complete"}
        return {**stalled(),"stdout":"","detail":"Deadline"}
    monkeypatch.setattr(v4_api,"execute_stdio",run)
    app=FastAPI();app.include_router(v4_api.router_for(lambda r:None,"test"))
    client=TestClient(app)
    return v4_api,client,{"X-AlgoXRay-Token":"test"},{"package_key":key,"source":SOURCE,"case":{"n":1},"trusted_local_source":True},calls

def test_profile_honors_opt_in_cache_and_returns_checked_facts_on_timeout(setup_profile,monkeypatch):
    module,client,headers,body,calls=setup_profile;selected=[]
    class Proposal:
        model="fixture";usage={"request_id":"test"}
        def propose(self,task,data,schema):
            assert task=="diagnosis" and data["execution_status"]=="timeout"
            e=next(e for e in data["events"] if e["line"]==3)
            return {"hypotheses":[{"text":"Inspect repeated loop bounds","event_ids":[e["event_id"]],"line":3}],
                "facts":[{"event_id":e["event_id"],"variable":"l","value":1}],
                "branches":[{"event_id":e["event_id"],"line":3,"condition":True}]}
    def factory(model,consent,**kwargs):selected.append((model,consent,kwargs));return Proposal()
    monkeypatch.setattr(module,"provider_for",factory)
    response=client.post("/api/v4/profile",headers=headers,json={**body,"use_ai":True,"use_cache":True})
    data=response.json()
    assert response.status_code==200 and data["kind"]=="timeout" and data["replay_count"]==0
    assert selected==[("qwen2.5-coder:7b",False,{"use_cache":True})] and len(calls)==2
    assert data["ai_status"]=="ok" and data["hypotheses"][0]["status"]=="hypothesis"
    assert data["ai_facts"][0]["status"]=="matches_recorded_snapshot"
    assert data["ai_branches"][0]["status"]=="matches_recorded_condition"
    assert data["ai_context"]["execution_status"]=="timeout" and data["execution_diagnostics"]["findings"]

@pytest.mark.parametrize("malformed",[False,True])
def test_unavailable_or_invalid_ai_keeps_timeout_trace_and_findings(setup_profile,monkeypatch,malformed):
    module,client,headers,body,calls=setup_profile
    class Broken:
        model="fixture";usage={}
        def propose(self,*args):
            if malformed:return {"invented_verified_cause":True}
            raise ProviderError("controlled_test_provider_unavailable")
    monkeypatch.setattr(module,"provider_for",lambda *a,**kw:Broken())
    response=client.post("/api/v4/profile",headers=headers,json={**body,"use_ai":True})
    data=response.json()
    assert response.status_code==200 and data["kind"]=="timeout" and data["ai_status"]=="unavailable_or_invalid"
    assert data["witness"]["student"]["events"] and data["execution_diagnostics"]["findings"]
    assert data["hypotheses"]==data["ai_facts"]==data["ai_branches"]==[]

def test_profile_cloud_consent_is_checked_before_execution(setup_profile,monkeypatch):
    module,client,headers,body,calls=setup_profile
    def factory(model,consent,**kwargs):
        if not consent:raise ProviderError("cloud_consent_required")
        raise AssertionError("No live cloud calls")
    monkeypatch.setattr(module,"provider_for",factory)
    response=client.post("/api/v4/profile",headers=headers,json={**body,"use_ai":True,"model":"qwen-cloud"})
    assert response.status_code==403 and calls==[]

def test_profile_does_not_select_provider_without_opt_in(setup_profile,monkeypatch):
    module,client,headers,body,calls=setup_profile
    monkeypatch.setattr(module,"provider_for",lambda *a,**kw:(_ for _ in ()).throw(AssertionError("AI must be opt-in")))
    data=client.post("/api/v4/profile",headers=headers,json=body).json()
    assert data["ai_status"]=="disabled" and data["ai_context"]=={} and data["execution_diagnostics"]["findings"]
