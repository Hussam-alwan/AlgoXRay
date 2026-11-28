import json,subprocess,sys,threading
import pytest
from algoxray.v4_isolation import GUEST
from algoxray.v4_observation import observe_source,benchmark_source,generated_size_inputs
from algoxray.v4_contracts import serialize

M={"id":"scale","title":"Scale","statement":"Read n and n values, print sum",
   "fields":[{"name":"n","kind":"int","min":1,"max":100},
             {"name":"a","kind":"ints","min":0,"max":9,"length_from":"n"}],
   "lines":[["n"],["a"]],"output":"tokens"}
P={"manifest":M,"reference":"ref","controls":[{"case":{"n":1,"a":[2]},"expected":"2"},
                                              {"case":{"n":2,"a":[1,3]},"expected":"4"}]}

def guest(source,stdin,*,mode,trace_limit,seconds,cancel):
    req={"source":source,"stdin":stdin,"mode":mode,"trace_limit":trace_limit,"seconds":seconds}
    return json.loads(subprocess.check_output([sys.executable,"-I","-c",GUEST],
                    input=(json.dumps(req)+"\n").encode(),timeout=5))

def test_manual_trace_without_oracle_and_sample_scope():
    source="a=int(input())\nprint(a*2)"
    r=observe_source(source,"3\n",run=guest,expected="9",expected_reviewed=False)
    assert r["status"]=="manual_observation" and r["judgment"]["status"]=="oracle_unavailable"
    assert r["witness"]["reference"]["status"]=="not_run"
    assert r["witness"]["student"]["stdout"]=="6\n" and r["student_graph"]["nodes"]
    assert r["judgment"]["expected"] is None and r["replay_count"]==0
    for expected,status in [("6","sample_match"),("9","sample_mismatch")]:
        r=observe_source(source,"3\n",run=guest,expected=expected,expected_reviewed=True)
        assert r["judgment"]["status"]==status
        assert r["judgment"]["general_correctness_claim"] is False
        assert r["judgment"]["input_validity"]=="not_verified_against_problem"

def test_manual_syntax_and_uninstrumented():
    assert observe_source("if","",run=guest)["kind"]=="syntax_error"
    r=observe_source("import sys; print(sys.gettrace() is None)","",mode="benchmark_uninstrumented",run=guest)
    assert r["witness"]["student"]["stdout"]=="True\n"
    assert r["witness"]["student"]["trace_status"]=="disabled"

def fake(src,stdin,*,mode,trace_limit,seconds,cancel):
    assert mode=="benchmark_uninstrumented" and trace_limit==0
    n,*a=map(int,stdin.split());total=sum(a)
    cost = n*n*(10 if src=="bad" else 100)
    return {"status":"ok","stdout":str(total if src!="bad" else total+1),"elapsed_ms":20,"cleanup_confirmed":True,
            "profile":{"method":"uninstrumented_execution","execution_wall_ns":cost,
                       "execution_cpu_ns":cost*4//5}}

def test_legal_scaling_and_correctness():
    sizes=[5,10,20];inputs=generated_size_inputs(M,"n",sizes,2026)
    assert [p["case"]["n"] for p in inputs]==sizes
    assert all(p["stdin"]==serialize(M,p["case"]) for p in inputs)
    r=benchmark_source("good",inputs,repeats=3,package=P,size_field="n",run=fake)
    assert r["physical_executions"]==12
    assert all(p["correctness"]=="recorded_match" and p["summary"]["completed"]==3 for p in r["points"])
    assert r["growth"]["wall_log_log_exponent"]==2
    bad=benchmark_source("bad",inputs,repeats=3,package=P,size_field="n",run=fake)
    assert all(p["correctness"]=="recorded_mismatch" for p in bad["points"])
    assert all(b["summary"]["wall_ns"]["median"] < g["summary"]["wall_ns"]["median"]
               for b, g in zip(bad["points"], r["points"]))
    assert bad["growth"]["status"]=="incomplete_noisy_or_incorrect"

def test_bad_sizes_and_timeout_retention():
    for sizes in ([0],[10,5],[1,101],[4,4]):
        with pytest.raises(ValueError):generated_size_inputs(M,"n",sizes,1)
    inputs=generated_size_inputs(M,"n",[1,4,16],1)
    def timeout(src,stdin,**kw):
        return {"status":"timeout","elapsed_ms":100}
    r=benchmark_source("good",inputs,repeats=3,size_field="n",run=timeout)
    assert all(p["summary"]["timeouts"]==3 and p["summary"]["completed"]==0 for p in r["points"])
    assert r["growth"]["status"]=="incomplete_noisy_or_incorrect"
    cancel=threading.Event();cancel.set()
    r=benchmark_source("good",inputs,repeats=3,size_field="n",run=fake,cancel=cancel)
    assert r["stop_reason"]=="cancelled" and r["physical_executions"]==0


def test_scaling_either_matrix_dimension_preserves_the_other_bound():
    matrix = {
        "id": "scale_matrix", "title": "Matrix scaling", "statement": "Read an r by c matrix.",
        "fields": [
            {"name": "r", "kind": "int", "min": 1, "max": 4},
            {"name": "c", "kind": "int", "min": 1, "max": 4},
            {"name": "a", "kind": "matrix", "min": 0, "max": 9, "rows_from": "r", "cols_from": "c"},
        ],
        "lines": [["r", "c"], ["a"]], "output": "tokens",
    }
    for dimension, other in (("r", "c"), ("c", "r")):
        manifest = {**matrix, "fields": [
            {**field, "min": 2, "max": 2} if field["name"] == other else field
            for field in matrix["fields"]
        ]}
        points = generated_size_inputs(manifest, dimension, [1, 2, 4], 2026)
        assert [p["case"][dimension] for p in points] == [1, 2, 4]
        for p in points:
            case = p["case"]
            assert case[other] == 2 and p["stdin"] == serialize(manifest, case)
            assert len(case["a"]) == case["r"] and all(len(row) == case["c"] for row in case["a"])


def test_growth_abstains_for_narrow_range_and_unstable_measurements():
    narrow = generated_size_inputs(M, "n", [4, 5, 6], 2026)
    result = benchmark_source("good", narrow, repeats=3, package=P, size_field="n", run=fake)
    assert result["growth"]["status"] == "insufficient_size_range"

    sizes = generated_size_inputs(M, "n", [4, 8, 16], 2026)
    calls = 0

    def noisy(source, stdin, **kwargs):
        nonlocal calls
        measurement = fake(source, stdin, **kwargs)
        calls += 1
        if calls % 3 == 0:
            measurement["profile"]["execution_wall_ns"] *= 3
        return measurement

    result = benchmark_source("good", sizes, repeats=3, size_field="n", run=noisy)
    assert result["growth"]["status"] == "incomplete_noisy_or_incorrect"
    assert all(len(p["runs"]) == p["summary"]["completed"] == 3 for p in result["points"])


def test_in_flight_cancellation_preserves_completed_measurements():
    cancel = threading.Event()
    calls = 0

    def run(source, stdin, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            kwargs["cancel"].set()
            return {"status": "cancelled", "cleanup_confirmed": True}
        return fake(source, stdin, **kwargs)

    points = generated_size_inputs(M, "n", [4, 8], 2026)
    result = benchmark_source("good", points, repeats=3, size_field="n", run=run, cancel=cancel)
    assert result["stop_reason"] == "cancelled" and result["physical_executions"] == 2
    assert len(result["points"]) == 1 and result["points"][0]["summary"]["completed"] == 1
    assert result["growth"]["status"] == "not_applicable_or_incomplete"
    assert result["run_report"]["stages"][-1]["status"] == "partial"
    stopped = result["run_report"]["workers"][-1]
    assert stopped["status"] == "cancelled" and stopped["cleanup_confirmed"] is True

def test_manual_api_requires_review(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from algoxray import v4_observation
    from algoxray.v4_api import router_for
    original=v4_observation.observe_source
    monkeypatch.setattr(v4_observation,"observe_source",lambda *a,**kw:original(*a,**kw,run=guest))
    app=FastAPI();app.include_router(router_for(lambda req:None,"test"))
    c=TestClient(app);headers={"X-AlgoXRay-Token":"test"}
    body={"source":"print(input())","stdin":"3\n"}
    assert c.post("/api/v4/observe",json=body,headers=headers).status_code==403
    r=c.post("/api/v4/observe",json={**body,"trusted_local_source":True},headers=headers)
    assert r.status_code==200 and r.json()["judgment"]["status"]=="oracle_unavailable"
    assert c.post("/api/v4/benchmark",json={"source":"print(1)","stdin":""},headers=headers).status_code==403
