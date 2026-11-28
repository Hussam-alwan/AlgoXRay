import pytest

from algoxray.v4_repair import RepairStore,verify_repair,propose_repair
from algoxray.v4_provider import MockProvider
P={"manifest":{"id":"twice","title":"Twice","statement":"Print double","fields":[{"name":"x","kind":"int","min":1,"max":9}],"lines":[["x"]],"output":"tokens"},
   "reference":"correct","controls":[{"case":{"x":2},"expected":"4"},{"case":{"x":3},"expected":"6"}]}
def fake(src,stdin,trace_limit=0):
    x=int(stdin)
    return {"status":"ok","stdout":str(2*x if src=="correct" else 2 if src=="hardcoded" else x)}
def test_patch_finite_checks():
    r=verify_repair(P,"bad","correct",{"x":1},run=fake)
    assert r["status"]=="passed_named_tests" and r["original_sha256"]!=r["candidate_sha256"]
    assert verify_repair(P,"bad","hardcoded",{"x":1},run=fake)["status"]=="not_passed_or_inconclusive"
    assert verify_repair(P,"correct","bad",{"x":1},run=fake)["status"]=="original_witness_not_reproduced"
def test_proposal_not_executed():
    p=MockProvider({"candidate":"print(1)","rationale":"example"})
    assert propose_repair(p,P,"bad",{"x":1})["executed"] is False


def test_interrupted_history_write_can_be_retried(tmp_path,monkeypatch):
    from algoxray import v4_repair

    store=RepairStore(tmp_path)
    result={"status":"passed_named_tests","candidate_sha256":"example"}

    def interrupted(value,stream,**kwargs):
        stream.write('{"package_key":')
        raise OSError("controlled history write failure")

    with monkeypatch.context() as patch:
        patch.setattr(v4_repair.json,"dump",interrupted)
        with pytest.raises(OSError,match="controlled history write failure"):
            store.save("test","before","after",result)
    assert not list(tmp_path.iterdir())

    key=store.save("test","before","after",result)
    assert store.load(key)["result"]==result
    assert store.save("test","before","after",result)==key
    assert [row["key"] for row in store.list("test")] == [key]
