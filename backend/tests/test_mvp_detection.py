"""Detection acceptance for legal inputs, runtime failures and replay."""

import pytest

from algoxray.v4_engine import analyze_package


PACKAGE = {
    "manifest": {
        "id": "detect_double", "title": "Double", "statement": "Read n and print its double.",
        "fields": [{"name": "n", "kind": "int", "min": 0, "max": 9}],
        "lines": [["n"]], "output": "tokens",
    },
    "reference": "reference",
    "controls": [
        {"case": {"n": 0}, "expected": "0"},
        {"case": {"n": 1}, "expected": "2"},
    ],
}


def runner(source, stdin, trace_limit):
    n = int(stdin)
    if source == "times_out":
        return {"status": "timeout", "basis": "host_wall_clock", "events": []}
    if source == "unavailable":
        return {"status": "infrastructure_error", "detail": "docker_unavailable", "events": []}
    if source == "raises":
        return {"status": "exception", "detail": "ValueError", "failure_location": {"line": 1}, "events": []}
    return {"status": "ok", "stdout": str(n if source == "half" else 2*n), "events": []}


@pytest.mark.parametrize(("source", "outcome"), [("times_out", "timeout"), ("unavailable", "infrastructure_error")])
def test_unjudged_student_execution_does_not_become_a_witness(source, outcome):
    report = analyze_package(PACKAGE, source, case={"n": 3}, run=runner)
    assert report["status"] == "inconclusive" and "witness" not in report
    assert report["inconclusive_student_outcomes"] == {outcome: 1}
    assert report["run_report"]["physical_executions"] == 2


@pytest.mark.parametrize(("source", "kind"), [("half", "wrong_answer"), ("raises", "exception")])
def test_legal_failure_is_replayed_three_times(source, kind):
    report = analyze_package(PACKAGE, source, case={"n": 3}, reduce_calls=0, run=runner)
    assert report["status"] == "observed_mismatch" and report["kind"] == kind
    assert report["witness"]["stdin"] == "3\n"
    assert report["replay_count"] == 3


def test_valid_solution_and_invalid_input_have_separate_outcomes():
    result = analyze_package(PACKAGE, "correct", case={"n": 3}, run=runner)
    assert result["status"] == "no_witness_found" and result["inconclusive_student_outcomes"] == {}

    def never_run(*args, **kwargs):
        pytest.fail("A manual case outside its contract must not start a worker")

    with pytest.raises(ValueError):
        analyze_package(PACKAGE, "correct", case={"n": 10}, run=never_run)


def test_reference_failure_during_replay_stops_before_student():
    calls = []

    def run(source, stdin, trace_limit):
        calls.append(source)
        if source == "reference" and trace_limit:
            return {"status": "timeout", "basis": "host_wall_clock", "events": []}
        return runner(source, stdin, trace_limit)

    report = analyze_package(PACKAGE, "half", case={"n": 3}, reduce_calls=0, run=run)
    assert report["status"] == "oracle_unavailable"
    assert report["detail"]["reference"]["status"] == "timeout"
    assert report["partial_observation"]["replay_verified"] is False
    assert calls == ["reference", "half", "reference"]
