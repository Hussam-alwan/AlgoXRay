import pytest

from algoxray.engine import Options, analyze
from algoxray.problems import PROBLEMS
from algoxray.registry import local_submission
from algoxray.runner import Runner


def custom(tmp_path, source):
    p = tmp_path / "reviewed.py"
    p.write_text(source, encoding="utf-8")
    return local_submission("dijkstra_v1", p)


def test_exception_separate_from_wrong_answer(tmp_path):
    sub = custom(tmp_path, "def solve(payload):\n    raise RuntimeError('fixture exception')\n")
    r = analyze(sub, Options(shrink=False), case=PROBLEMS["dijkstra_v1"]["example"], persist=False)
    assert r["failure_kind"] == "exception" and r["exception"]["type"] == "RuntimeError"


def test_missing_solve_is_invalid_submission(tmp_path):
    r = analyze(custom(tmp_path, "x = 1\n"), Options(), case=PROBLEMS["dijkstra_v1"]["example"], persist=False)
    assert r["status"] == "invalid_submission" and not r["claims"]


def test_syntax_error_is_invalid_submission(tmp_path):
    r = analyze(custom(tmp_path, "def solve(:\n"), Options(), case=PROBLEMS["dijkstra_v1"]["example"], persist=False)
    assert r["status"] == "invalid_submission"


def test_native_sleep_is_killed_and_worker_can_restart(tmp_path):
    sub = custom(tmp_path, "import time\ndef solve(payload):\n    if payload['source'] == 0:\n        time.sleep(5)\n    return [0, 1]\n")
    with Runner(sub, timeout=0.08) as runner:
        response = runner.run({"n": 2, "edges": [], "source": 0})
        assert response["status"] == "timeout" and runner.process is None
        assert runner.run({"n": 2, "edges": [], "source": 1})["output"] == [0, 1]
        assert runner.startups == 2
    assert runner.process is None


def test_namespace_reset_prevents_cross_case_global_state(tmp_path):
    sub = custom(tmp_path, "counter = 0\ndef solve(payload):\n    global counter\n    counter += 1\n    return [counter, 0]\n")
    with Runner(sub) as runner:
        assert runner.run({})["output"] == runner.run({})["output"] == [1, 0]


def test_submission_output_is_captured_and_bounded(tmp_path):
    sub = custom(tmp_path, "def solve(payload):\n    print('hello')\n    return [0, 1]\n")
    with Runner(sub) as runner:
        r = runner.run({})
    assert r["status"] == "ok" and r["stdout"] == "hello\n"
