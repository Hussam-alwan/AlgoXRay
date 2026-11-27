import pytest
from algoxray.v4_contracts import validate_manifest, serialize, complexity, smaller
from algoxray.v4_engine import analyze_package
from algoxray.v4_shrinking import failure_signature

M = {"id":"triple","title":"Array sum","statement":"Read n integers and sum.",
     "fields":[{"name":"n","kind":"int","min":1,"max":100},
               {"name":"a","kind":"ints","min":0,"max":9,"length_from":"n"}],
     "lines":[["n"],["a"]],"output":"tokens"}
P = {"manifest":M,"reference":"ref","controls":[
    {"case":{"n":1,"a":[1]},"expected":"1"},
    {"case":{"n":3,"a":[7,7,7]},"expected":"21"}]}

def test_iterative_middle_witness():
    original={"n":100,"a":[0]*48+[7]*3+[0]*49}
    def run(src,stdin,trace_limit):
        n,*a=map(int,stdin.split())
        assert n==len(a)
        total=sum(a)
        if src=="bad" and a.count(7)>=3:total-=1
        return {"status":"ok","stdout":str(total),"events":[]}
    r=analyze_package(P,"bad",case=original,reduce_calls=32,run=run)
    assert r["status"]=="observed_mismatch"
    assert r["original_case"]==original
    assert r["witness"]["case"]=={"n":3,"a":[7,7,7]}
    red=r["reduction"]
    assert red["original_replay_count"]==red["reduced_replay_count"]==3
    assert len(red["accepted"])>1 and red["probes"]<=32
    assert r["executions"]==r["attempts"]*2
    assert all(serialize(M,s["case"])==s["stdin"] for s in red["accepted"])

def test_shared_dimension_and_middle_deletions():
    m={**M,"fields":[M["fields"][0],M["fields"][1],
        {"name":"b","kind":"ints","min":0,"max":9,"length_from":"n"}],
       "lines":[["n"],["a"],["b"]]}
    validate_manifest(m)
    case={"n":5,"a":[1,2,3,4,5],"b":[5,4,3,2,1]}
    options=list(smaller(m,case))
    assert {"n":4,"a":[1,2,4,5],"b":[5,4,2,1]} in options
    assert all(complexity(m,c)<complexity(m,case) for c in options)

def test_exception_signature_needs_location():
    result={"kind":"exception","student":{"detail":"IndexError"}}
    assert failure_signature(result) is None
    result["student"]["failure_location"]={"line":4,"function":"main"}
    assert failure_signature(result)=={"kind":"exception","detail":"IndexError","line":4,"function":"main"}

def test_wrong_answer_does_not_shrink_to_exception():
    def run(src,stdin,trace_limit):
        n,*a=map(int,stdin.split())
        if src=="bad" and n<3:
            return {"status":"exception","detail":"IndexError","failure_location":{"line":5},"stdout":"","events":[]}
        return {"status":"ok","stdout":str(sum(a)-(src=="bad")),"events":[]}
    r=analyze_package(P,"bad",case={"n":3,"a":[7,7,7]},reduce_calls=32,run=run)
    assert r["status"]=="observed_mismatch" and r["kind"]=="wrong_answer"
    assert r["witness"]["case"]["n"]==3
