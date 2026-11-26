from copy import deepcopy
import json

from hypothesis import given, settings
import pytest

from algoxray.generation import strategy_for
from algoxray.problems import InvalidCase, PROBLEMS, check_output, reference, validate_case
from algoxray.registry import get_submission


def test_unreachable_vertices_and_nonzero_source():
    c = {"n": 4, "edges": [[2, 1, 5], [1, 0, 2]], "source": 2}
    assert reference("dijkstra_v1", validate_case("dijkstra_v1", c)) == [7, 5, 0, None]


@pytest.mark.parametrize("changes", [{"n": True}, {"source": 4}, {"edges": [[0, 0, 1]]},
                                     {"edges": [[0, 1, -1]]}, {"edges": [[0, 1, 2], [0, 1, 3]]},
                                     {"extra": 1}, {"edges": [[0, 1, True]]}])
def test_illegal_graphs_are_rejected(changes):
    c = deepcopy(PROBLEMS["dijkstra_v1"]["example"])
    c.update(changes)
    with pytest.raises(InvalidCase):
        validate_case("dijkstra_v1", c)


@pytest.mark.parametrize("actual", [[0, 1], [False, 1, 2], [0, -1, 2], {"dist": [0, 1, 2]}])
def test_bad_output_shape_is_not_a_valid_answer(actual):
    c = PROBLEMS["dijkstra_v1"]["example"]
    assert check_output("dijkstra_v1", c, actual, [0, 1, 2]) == "contract_violation"


def test_any_matching_duplicate_index_is_accepted():
    c = {"array": [1, 2, 2, 2, 9], "target": 2}
    assert reference("binary_search_v1", c) == 1
    assert check_output("binary_search_v1", c, 3, 1) is None
    assert check_output("binary_search_v1", c, -1, 1) == "wrong_answer"
    assert check_output("binary_search_v1", c, True, 1) == "contract_violation"


@pytest.mark.parametrize("case", [{"array": [2, 1], "target": 1}, {"array": [], "target": 21},
                                  {"array": [False], "target": 0}])
def test_invalid_arrays_rejected(case):
    with pytest.raises(InvalidCase):
        validate_case("binary_search_v1", case)


@given(strategy_for("dijkstra_v1"))
@settings(max_examples=75, deadline=None, derandomize=True)
def test_correct_dijkstra_against_two_oracles(case):
    case = validate_case("dijkstra_v1", case)
    namespace = {}
    exec(compile(get_submission("dijkstra_correct").source, "control.py", "exec"), namespace)
    actual = namespace["solve"](deepcopy(case))
    actual = [None if x == float("inf") else x for x in actual]
    assert check_output("dijkstra_v1", case, actual, reference("dijkstra_v1", case)) is None


@given(strategy_for("binary_search_v1"))
@settings(max_examples=75, deadline=None, derandomize=True)
def test_correct_binary_and_generator_contract(case):
    case = validate_case("binary_search_v1", case)
    namespace = {}
    exec(compile(get_submission("binary_correct").source, "control.py", "exec"), namespace)
    actual = namespace["solve"](case)
    assert check_output("binary_search_v1", case, actual, reference("binary_search_v1", case)) is None
