import copy
import threading
import pytest
from algoxray.v4_contracts import validate_package,serialize
from algoxray.v4_checker import judge_output
from algoxray.v4_engine import oracle,review,analyze_package
from algoxray.v4_repair import verify_repair

M={"id":"pair","title":"Pair","statement":"Print two distinct 1-based indices whose values sum to k, or NONE.",
   "fields":[{"name":"n","kind":"int","min":2,"max":6},{"name":"k","kind":"int","min":0,"max":20},
             {"name":"a","kind":"ints","min":0,"max":9,"length_from":"n"}],
   "lines":[["n","k"],["a"]],"output":"tokens"}
C={"n":4,"k":5,"a":[1,4,2,3]}
N={"n":2,"k":20,"a":[0,1]}
P={"manifest":M,"reference":"primary","reference_alt":"alternative",
   "checker":{"kind":"two_sum_indices","version":1,"array":"a","target":"k","index_base":1,"no_solution":"NONE"},
   "controls":[{"case":C,"expected":"2 1"},{"case":N,"expected":"NONE"}]}

def fake(src,stdin,trace_limit=0,**kwargs):
    n,k,*a=map(int,stdin.split())
    pairs=[(i+1,j+1) for i in range(n) for j in range(i+1,n) if a[i]+a[j]==k]
    if src=="bad":out="1 1"
    elif src=="wrong_reference":out="NONE"
    elif src=="hardcoded":out="1 2"
    elif src=="partial" and n>2:out="NONE"
    else:
        p=pairs[-1 if src=="alternative" else 0] if pairs else None
        out=" ".join(map(str,p)) if p else "NONE"
    return {"status":"ok","stdout":out,"events":[]}

def test_distinct_correct_answers_and_no_solution():
    validate_package(P)
    for text in ("1 2","2 1","3 4","4 3"):
        assert judge_output(P,C,text,"2 1")["status"]=="accepted"
    for text in ("NONE","1 1","0 1","1 3","1 2 3"):
        assert judge_output(P,C,text,"2 1")["status"]=="rejected"
    assert judge_output(P,N,"NONE","NONE")["status"]=="accepted"
    assert judge_output(P,N,"1 2","NONE")["status"]=="rejected"
    assert judge_output(P,C,"1 2","NONE")["status"]=="unavailable"
    assert review(P,run=fake)["passed"]
    assert analyze_package(P,"alternative",case=C,run=fake,reduce_calls=0)["status"]=="no_witness_found"

def test_bad_reference_never_accuses_correct_student():
    p={**P,"reference":"wrong_reference"}
    assert not review(p,run=fake)["passed"]
    r=analyze_package(p,"alternative",case=C,run=fake)
    assert r["status"]=="oracle_unavailable"
    p={**P,"reference_alt":"wrong_reference"}
    assert analyze_package(p,"primary",case=C,run=fake)["status"]=="oracle_unavailable"

def test_checker_failure_and_invalid_control(monkeypatch):
    p=copy.deepcopy(P);p["controls"][0]["expected"]="1 1"
    with pytest.raises(ValueError,match="Control violates"):validate_package(p)
    from algoxray import v4_checker
    orig=v4_checker.semantic_answer
    def fail(m,c,case,output):
        if output=="1 1":raise RuntimeError("controlled checker error")
        return orig(m,c,case,output)
    monkeypatch.setattr(v4_checker,"semantic_answer",fail)
    r=analyze_package(P,"bad",case=C,run=fake)
    assert r["status"]=="oracle_unavailable"
    assert r["detail"]["judgment"]["reason"]=="checker_failed"

def test_witnesses_and_semantic_repair():
    r=analyze_package(P,"bad",case=C,reduce_calls=4,run=fake)
    assert r["status"]=="observed_mismatch"
    assert r["witness"]["judgment"]["authority"]=="owner_reviewed_semantic_checker"
    assert r["witness"]["judgment"]["status"]=="rejected"
    r=verify_repair(P,"bad","alternative",r["witness"]["case"],original_case=C,run=fake)
    assert r["status"]=="passed_named_tests" and r["suite_sha256"]
    assert {x["kind"] for x in r["witness_reproductions"]}=={"witness","original_witness"}
    assert all(x["status"]=="reproduced" for x in r["witness_reproductions"])
    assert r["planned_cases"]==len(r["checks"])
    small={"n":2,"k":5,"a":[1,4]}
    r=verify_repair(P,"bad","partial",small,original_case=C,run=fake)
    assert r["status"]=="not_passed_or_inconclusive"
    assert r["checks"][0]["status"]=="match" and r["checks"][1]["status"]=="not_passed"
    r=verify_repair(P,"bad","hardcoded",small,original_case=C,run=fake)
    assert r["status"]=="not_passed_or_inconclusive"
    assert any("owner_control" in x["labels"] and x["status"]=="not_passed" for x in r["checks"])

def test_repair_cancel_preserves_scope():
    cancel=threading.Event();cancel.set()
    r=verify_repair(P,"bad","primary",C,run=fake,cancel=cancel)
    assert r["status"]=="cancelled" and not r["checks"] and r["executions"]==0
