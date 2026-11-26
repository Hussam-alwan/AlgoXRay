from algoxray.engine import analyze,Options
from algoxray.registry import local_submission
from algoxray.problem_registry import spec_for

def test_worker_exit_is_not_a_student_accusation(tmp_path):
    p=tmp_path/"exit_solver.py"
    p.write_text("import os\ndef solve(data):\n    os._exit(7)\n",encoding="utf-8")
    b=analyze(local_submission("binary_search_v1",p),Options(shrink=False),case={"array":[1],"target":1},persist=False)
    assert b["status"]=="infrastructure_error" and b["failure_kind"] is None
    assert not b["claims"] and b["evidence_level"]=="E0"

def test_registered_metadata_exposes_trust_boundary():
    m=spec_for("dijkstra_v1").public_metadata()
    assert m["visualization"]=="graph" and m["oracle_id"]
    assert not m["capabilities"]["hostile_code_sandbox"]
