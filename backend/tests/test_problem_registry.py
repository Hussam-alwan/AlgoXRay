import pytest
from algoxray.problem_registry import REGISTRY, spec_for
from algoxray.problems import InvalidCase

@pytest.mark.parametrize("problem", list(REGISTRY))
def test_registered_problem_contract(problem):
    spec = spec_for(problem)
    case = spec.validate(spec.metadata["example"])
    expected = spec.reference(case)
    assert spec.check(case, expected, expected) is None
    for smaller in spec.smaller(case):
        assert spec.complexity(spec.validate(smaller)) < spec.complexity(case)

def test_unknown_problem_is_rejected():
    with pytest.raises(InvalidCase):
        spec_for("unknown")
