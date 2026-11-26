import threading
import time
from algoxray.engine import analyze, Options
from algoxray.registry import local_submission
from algoxray.runner import Runner

def sub(tmp_path, code):
    p=tmp_path/"solver.py"
    p.write_text(code,encoding="utf-8")
    return local_submission("binary_search_v1",p)

def test_pre_cancelled_never_accuses(tmp_path):
    token=threading.Event(); token.set()
    b=analyze(sub(tmp_path,"def solve(x): return -1\n"),case={"array":[1],"target":1},cancel=token,persist=False)
    assert b["status"]=="cancelled" and not b["claims"] and b["statistics"]["total_solver_calls"]==0

def test_cancel_running_native_call(tmp_path):
    token=threading.Event()
    t=threading.Timer(.3,token.set)
    t.start()
    try:
        b=analyze(sub(tmp_path,"import time\ndef solve(x): time.sleep(10)\n"),Options(per_case_seconds=3),case={"array":[1],"target":1},cancel=token,persist=False)
        assert b["status"]=="cancelled" and not b["claims"]
    finally: t.cancel()

def test_fresh_process_resets_imported_module_state(tmp_path):
    s=sub(tmp_path,"import math\ndef solve(x):\n    math.algoxray_counter = getattr(math,'algoxray_counter',0)+1\n    return math.algoxray_counter\n")
    with Runner(s,fresh_process=True) as r:
        assert r.run({})["output"]==r.run({})["output"]==1
        assert r.startups==2 and r.process is None
