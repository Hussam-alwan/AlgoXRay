import threading
import pytest
from algoxray.v4_engine import analyze_package
from algoxray.v4_run_report import RunLedger,BudgetExhausted,sha

P={"manifest":{"id":"report_test","title":"Double","statement":"Read n and print double.",
    "fields":[{"name":"n","kind":"int","min":0,"max":9}],"lines":[["n"]],"output":"tokens"},
    "reference":"print(2*int(input()))","controls":[{"case":{"n":0},"expected":"0"},{"case":{"n":1},"expected":"2"}]}
CORRECT=P["reference"];MUTANT="print(int(input()))"

def fake(src,stdin,**kwargs):
    n=int(stdin)
    return {"status":"ok","stdout":str(n*2 if src==CORRECT else n),"events":[],
            "trace_status":"complete","image_id":"fixture","cleanup_confirmed":True,"elapsed_ms":0.3}

def test_all_terminal_stages_and_identity():
    for source,status in [(CORRECT,"no_witness_found"),(MUTANT,"observed_mismatch")]:
        r=analyze_package(P,source,case={"n":2},reduce_calls=0,run=fake,run_id="a"*32)
        assert r["status"]==status
        ledger=r["run_report"]
        assert r["analysis_id"]==ledger["run_id"]=="a"*32
        assert ledger["source_sha256"]==sha(source)
        assert ledger["package_sha256"]==r["package_sha256"]
        assert ledger["physical_executions"]==len(ledger["workers"])
        assert ledger["distinct_worker_inputs"]==1
        assert sum(s["executions"] for s in ledger["stages"])==ledger["physical_executions"]
        assert all(s["status"]!="running" for s in ledger["stages"])
        stages={s["name"]:s["status"] for s in ledger["stages"]}
        assert stages["diagnosis"]=="skipped"
        assert stages["replay"]==("completed" if source==MUTANT else "not_run")
        assert {w["role"] for w in ledger["workers"]}=={"reference","student"}

def test_cancel_before_worker():
    event=threading.Event();event.set()
    r=analyze_package(P,MUTANT,case={"n":2},run=fake,cancel=event)
    assert r["status"]=="cancelled"
    assert r["run_report"]["physical_executions"]==0
    assert r["run_report"]["stop_reason"]=="cancelled"

def test_wall_budget_preserves_unverified_observation(monkeypatch):
    from algoxray import v4_engine
    clock=[0.0]
    monkeypatch.setattr(v4_engine,"RunLedger",lambda *a,**kw:RunLedger(*a,**kw,clock=lambda:clock[0]))
    def worker(*a,**kw):
        clock[0]+=.55
        return fake(*a,**kw)
    r=analyze_package(P,MUTANT,case={"n":2},reduce_calls=0,run=worker,session_seconds=1)
    assert r["status"]=="inconclusive"
    assert r["stop_reason"]=="session_wall_budget_exhausted"
    assert r["partial_observation"]["replay_verified"] is False
    assert r["partial_observation"]["witness"]["kind"]=="wrong_answer"
    assert r["run_report"]["physical_executions"]==2
    assert r["run_report"]["elapsed_ms"]>=1000
    assert r["run_report"]["pair_attempts"]==2
    assert next(s for s in r["run_report"]["stages"] if s["name"]=="replay")["status"]=="partial"

def test_call_budget_checked_before_launch():
    ledger=RunLedger("observe",CORRECT,max_executions=1)
    ledger.enter("student")
    ledger.execute(fake,"student",CORRECT,"2\n")
    with pytest.raises(BudgetExhausted,match="physical_execution_budget_exhausted"):
        ledger.execute(fake,"student",CORRECT,"3\n")
    assert len(ledger.workers)==1
