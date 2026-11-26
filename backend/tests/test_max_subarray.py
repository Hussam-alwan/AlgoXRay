import pytest
from algoxray.problems import validate_case, reference, check_output, complexity
from algoxray.reduction import smaller_cases
from algoxray.certificate import checked_example
from algoxray.engine import analyze, Options
from algoxray.registry import get_submission

P = "max_subarray_v1"

def test_negative_array_certificate():
    case = validate_case(P, {"array": [-5, -2, -7]})
    assert reference(P, case) == -2
    assert check_output(P, case, 0, -2) == "wrong_answer"
    assert checked_example(P, case, 0, -2)["segment"] == [-2]
    for candidate in smaller_cases(P, case):
        validate_case(P, candidate)
        assert complexity(P, candidate) < complexity(P, case)

def test_manual_witness():
    bundle = analyze(get_submission("max_subarray_empty_bug"), Options(shrink=False), case={"array": [-2]}, persist=False)
    assert bundle["status"] == "witness_found"
    assert bundle["expected_output"] == -2
    assert bundle["observed_output"] == 0
