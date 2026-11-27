import json
import subprocess
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from algoxray.v4_isolation import GUEST
from algoxray.v4_profiling import ExecutionProfiler, attach_profile
from algoxray.v4_graph import observed_graph


def guest(source, limit=256):
    request = json.dumps(dict(source=source, stdin="", seconds=1, trace_limit=limit))
    return json.loads(subprocess.check_output([sys.executable, "-I", "-c", GUEST],
                                             input=request.encode(), timeout=5))


def test_parent_and_child_segments_do_not_double_count_self_time():
    p = ExecutionProfiler("def f():\n    return 2\nx=f()\n")
    parent = SimpleNamespace(f_code=SimpleNamespace(co_name="<module>", co_firstlineno=1), f_lineno=3)
    child = SimpleNamespace(f_code=SimpleNamespace(co_name="f", co_firstlineno=1), f_lineno=2)
    p.event(parent, "call", "F1"); p.event(parent, "line", "F1")
    p.last = (0, 0); p.tick(10, 5)
    p.event(child, "call", "F2"); p.event(child, "line", "F2")
    p.last = (10, 5); p.tick(40, 20)
    p.event(child, "return", "F2")
    p.last = (40, 20); p.tick(50, 25)
    a, b = p.lines[("F1", 3)], p.lines[("F2", 2)]
    assert (a["self_wall_ns"], a["inclusive_wall_ns"]) == (20, 50)
    assert (b["self_wall_ns"], b["inclusive_wall_ns"]) == (30, 30)
    assert (a["self_cpu_ns"], a["inclusive_cpu_ns"]) == (10, 25)
    assert p.blocks[0]["inclusive_wall_ns"] == 50


def test_sleep_loop_calls_and_unexecuted_block():
    source = "import time\ndef work():\n    time.sleep(.01)\n    return 2\nx=0\nfor i in range(3):\n    x+=work()\nif False:\n    x=99\nprint(x)\n"
    r = guest(source)
    assert r["status"] == "ok" and r["stdout"] == "6\n"
    p = r["profile"]
    assert p["status"] == "complete" and p["execution_wall_ns"] >= 25_000_000
    f = next(b for b in p["blocks"] if b["kind"] == "function")
    loop = next(b for b in p["blocks"] if b["kind"] == "for")
    assert f["hits"] == 3 and loop["hits"] == 4
    assert f["self_wall_ns"] >= 25_000_000
    assert f["self_cpu_ns"] < f["self_wall_ns"]
    assert not any(x["line"] == 9 for x in p["lines"])
    g = attach_profile(observed_graph(r["events"], source), r)
    assert g["frames"] and g["timeline"] and any(n["timing"] for n in g["nodes"])
    assert len({x["frame_id"] for x in p["lines"] if x["function"] == "work"}) == 3


def test_recursion_frames_and_early_return():
    r = guest("def f(n):\n    if n == 0:\n        return 1\n    return n*f(n-1)\nprint(f(4))\n")
    p = r["profile"]
    assert r["stdout"] == "24\n" and p["status"] == "complete"
    f = next(x for x in p["blocks"] if x["kind"] == "function")
    assert f["hits"] == 5 and f["inclusive_wall_ns"] >= f["self_wall_ns"]
    assert len({x["frame_id"] for x in p["lines"] if x["function"] == "f"}) == 5


def test_profile_continues_after_snapshot_trace_limit_and_disabled_search():
    source = "s=0\nfor i in range(200):\n    s+=i\nprint(s)\n"
    r = guest(source, 3)
    assert r["trace_status"] == "truncated"
    assert len(r["events"]) == 3 and r["profile"]["status"] == "complete"
    loop = next(b for b in r["profile"]["blocks"] if b["kind"] == "for")
    assert loop["hits"] == 201
    off = guest(source, 0)
    assert off["profile"]["status"] == "disabled" and off["profile"]["lines"] == []


def test_profile_exception_syntax_error_and_caps_are_explicit():
    r = guest("x=1\nraise ValueError('test')\n")
    assert r["status"] == "exception" and r["profile"]["status"] == "partial"
    assert guest("if !!!\n")["profile"]["lines"] == []
    p = ExecutionProfiler("x=1\n", max_events=1)
    f = SimpleNamespace(f_code=SimpleNamespace(co_name="<module>", co_firstlineno=1), f_lineno=1)
    p.event(f, "call", "F1"); p.event(f, "line", "F1")
    assert p.report("ok", 10, 5)["status"] == "partial"
    r = guest("s=0\nfor i in range(40000):\n    s+=i\nprint(s)\n")
    assert len(json.dumps(r)) < 512 * 1024


def test_missing_historical_profile_is_unavailable():
    g = attach_profile(observed_graph([dict(event_id="E1", frame_id="F1", line=1,
        kind="line", locals={})]), {})
    assert g["profile"]["status"] == "unavailable" and g["nodes"][0]["timing"] is None


def test_profile_route_requires_review_and_valid_input_without_ai(monkeypatch, tmp_path):
    from algoxray import v4_api
    from algoxray.v4_contracts import PackageStore
    monkeypatch.setenv("ALGOXRAY_V4_PACKAGE_STORE", str(tmp_path))
    manifest = dict(id="n", title="n", statement="Print n", fields=[dict(name="n", kind="int", min=1, max=4)], lines=[["n"]], output="tokens")
    pkg = dict(manifest=manifest, reference="print(int(input()))", controls=[dict(case=dict(n=1), expected="1"), dict(case=dict(n=4), expected="4")])
    key = PackageStore(tmp_path).save(pkg)
    called = []
    def run(src, stdin, **kwargs):
        called.append(stdin)
        r = guest("print(" + stdin.strip() + ")")
        return r
    monkeypatch.setattr(v4_api, "execute_stdio", run)
    monkeypatch.setattr(v4_api, "provider_for", lambda *a: (_ for _ in ()).throw(AssertionError("AI not needed")))
    app = FastAPI(); app.include_router(v4_api.router_for(lambda r: None, "test"))
    client = TestClient(app)
    body = dict(package_key=key, source="print(int(input()))", use_ai=True)
    assert client.post("/api/v4/profile", json=body).status_code == 403
    headers = {"X-AlgoXRay-Token": "test"}
    assert client.post("/api/v4/profile", json=body, headers=headers).status_code == 403
    body.update(trusted_local_source=True, case=dict(n=3))
    r = client.post("/api/v4/profile", json=body, headers=headers)
    assert r.status_code == 200 and r.json()["status"] == "profiled_execution"
    assert r.json()["kind"] == "match" and r.json()["replay_count"] == 0
    assert called == ["3\n", "3\n"]
    body["case"] = dict(n=100)
    assert client.post("/api/v4/profile", json=body, headers=headers).status_code == 422
