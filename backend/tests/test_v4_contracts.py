import json
import pytest
from algoxray.v4_contracts import *
from algoxray.v4_engine import analyze_package,review

M={"id":"sum","title":"Sum","statement":"Sum list","fields":[{"name":"n","kind":"int","min":1,"max":4},{"name":"a","kind":"ints","min":-5,"max":5,"length_from":"n"}],"lines":[["n"],["a"]],"output":"tokens"}
P={"manifest":M,"reference":"reference","controls":[{"case":{"n":1,"a":[3]},"expected":"3"},{"case":{"n":2,"a":[1,2]},"expected":"3"}]}
def test_schema_generator_reducer():
    validate_package(P)
    for c in generate(M,42,30):
        assert serialize(M,c).endswith("\n")
        assert all(complexity(M,d)<complexity(M,c) for d in smaller(M,c))
    with pytest.raises(ValueError):serialize(M,{"n":2,"a":[3]})
    with pytest.raises(ValueError):validate_manifest({**M,"output":"eval"})
def test_store(tmp_path):
    s=PackageStore(tmp_path);k=s.save(P);assert s.load(k)==P
    (tmp_path/(k+".json")).write_text("{}")
    with pytest.raises(ValueError):s.load(k)
def fake(source,stdin,trace_limit):
    nums=list(map(int,stdin.split()))[1:]
    value=sum(nums) if source=="reference" else 0
    return {"status":"ok","stdout":str(value)+"\n","events":[]}
def test_engine_replay_and_control():
    assert review(P,run=fake)["passed"]
    assert analyze_package(P,"reference",run=fake)["status"]=="no_witness_found"
    r=analyze_package(P,"wrong",run=fake)
    assert r["status"]=="observed_mismatch" and r["replay_count"]==3
    assert r["ai_status"]=="disabled"
def test_oracle_failure():
    r=analyze_package(P,"wrong",run=lambda *a,**kw:{"status":"timeout"})
    assert r["status"]=="oracle_unavailable"
