import copy
import pytest
from algoxray.v4_intake import prepare_problem, validate_intake
from algoxray.v4_authoring import parse_problem
from algoxray.v4_draft_review import review_draft
from algoxray.v4_contracts import validate_package
from algoxray.v4_provider import MockProvider
from algoxray.v4_api import router_for

STATEMENT="Read t from 1 to 3; each case has n from 1 to 4 and n sorted distinct integers from 0 to 9."
MANIFEST={"schema_version":2,"id":"repeated","title":"Repeated list",
          "statement":STATEMENT,"fields":[{"name":"n","kind":"int","min":1,"max":4},
                    {"name":"a","kind":"ints","min":0,"max":9,"length_from":"n","sorted":True,"unique":True}],
          "lines":[["n"],["a"]],"output":"tokens","repeat":{"min":1,"max":3}}
EVIDENCE=[{"field":"n","attribute":x,"quote":"n from 1 to 4"} for x in ("min","max")]+[
          {"field":"a","attribute":x,"quote":"n sorted distinct integers from 0 to 9"} for x in ("min","max","length_from")]

def test_description_and_text_preserve_data():
    for kind in ("text","description"):
        r=prepare_problem(kind,text=STATEMENT,samples=[{"stdin":"1\n2\n1 2\n","stdout":"3\n"}])
        assert r["statement"]==STATEMENT and r["intake"]["kind"]==kind
        assert validate_intake(r["intake"],STATEMENT)==r["intake"]
        assert r["status"]=="intake_unreviewed"
        with pytest.raises(ValueError,match="hash mismatch"):validate_intake(r["intake"],STATEMENT+" edited")
    assert len(prepare_problem("description",text="Sum the numbers.")["intake"]["clarifications"])==3

def test_import_preserves_url_and_incomplete_samples():
    url="https://codeforces.com/contest/123/problem/A"
    def importer(u):
        return parse_problem('<div class="problem-statement"><p>Read n</p><div class="input"><pre>2</pre></div></div>',u)
    r=prepare_problem("codeforces",url=url,importer=importer)
    assert r["source_url"]=="https://codeforces.com/problemset/problem/123/A"
    assert r["samples"]==[] and "counts differ" in r["intake"]["clarifications"][0]
    with pytest.raises(ValueError):prepare_problem("codeforces",url="https://localhost/test",importer=importer)
    with pytest.raises(ValueError):prepare_problem("text",text="Description",url=url)

def test_unsupported_intake_and_stale_package():
    with pytest.raises(ValueError):prepare_problem("text",text=" ")
    with pytest.raises(ValueError):prepare_problem("description",text="Read n",samples=[{"stdin":"x"}])
    r=prepare_problem("text",text=STATEMENT)
    p={"manifest":MANIFEST,"reference":"ref","controls":[
        {"case":{"t":1,"cases":[{"n":1,"a":[2]}]},"expected":"2"},
        {"case":{"t":1,"cases":[{"n":2,"a":[1,3]}]},"expected":"4"}],"intake":r["intake"]}
    assert validate_package(p)==p
    p=copy.deepcopy(p);p["manifest"]["statement"]+=" updated"
    with pytest.raises(ValueError,match="hash mismatch"):validate_package(p)

def test_v2_draft_is_unreviewed_and_retains_source(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from algoxray import v4_api
    app=FastAPI();app.include_router(router_for(lambda req:None,"local-test"))
    c=TestClient(app);headers={"X-AlgoXRay-Token":"local-test"}
    assert c.post("/api/v4/packages/intake",json={"kind":"description","text":"Read n."}).status_code==403
    r=c.post("/api/v4/packages/intake",headers=headers,json={"kind":"description","text":STATEMENT})
    assert r.status_code==200
    intake=r.json()["intake"]
    proposed={"manifest":MANIFEST,"evidence":EVIDENCE,"unresolved":[]}
    monkeypatch.setattr(v4_api,"provider_for",lambda model,consent:MockProvider(proposed))
    r=c.post("/api/v4/packages/draft",headers=headers,json={"schema_version":2,"statement":STATEMENT,"intake":intake})
    assert r.status_code==200,r.text
    data=r.json()
    assert data["status"]=="draft_unreviewed" and data["manifest"]==MANIFEST
    assert data["intake"]==intake
    assert any("repeated cases" in x for x in data["provenance"]["unresolved"])
    assert any("ordering and uniqueness" in x for x in data["provenance"]["unresolved"])
    assert c.get("/api/v4/capabilities").json()["schema_versions"]==[1,2]
    assert c.post("/api/v4/packages/draft",headers=headers,json={"schema_version":2,"statement":STATEMENT+" changed","intake":intake}).status_code==422
