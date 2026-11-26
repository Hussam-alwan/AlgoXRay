import pytest
from algoxray.reduction import smaller_cases
from algoxray.problems import validate_case, complexity
from algoxray.generation import random_case, strategy_for
import random

@pytest.mark.parametrize("problem,case", [
    ("binary_search_v1", {"array": [-1, 0, 2], "target": 0}),
    ("dijkstra_v1", {"n": 3, "source": 0, "edges": [[0, 1, 3], [1, 2, 2]]}),
])
def test_reductions_are_legal_and_strict(problem, case):
    for candidate in smaller_cases(problem, case):
        validate_case(problem, candidate)
        assert complexity(problem, candidate) < complexity(problem, case)

def test_unknown_problem_does_not_fall_back_to_binary_search():
    with pytest.raises(ValueError):
        random_case("unknown", random.Random(1))
    with pytest.raises(ValueError):
        strategy_for("unknown")
    with pytest.raises(ValueError):
        list(smaller_cases("unknown", {}))
