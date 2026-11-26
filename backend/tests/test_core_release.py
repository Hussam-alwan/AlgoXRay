import hashlib
from copy import deepcopy

import pytest

from algoxray.certificate import checked_example
from algoxray.engine import Options, analyze
from algoxray.registry import local_submission
from algoxray.replay import replay_witness


def run(tmp, source, case, problem="binary_search_v1", **kwargs):
    path = tmp / "reviewed.py"
    path.write_bytes(source.encode())
    return analyze(local_submission(problem, path), Options(shrink=False, **kwargs), case, persist=False)


def test_file_bytes_and_exact_replay(tmp_path):
    source = "\ufeffdef solve(x):\r\n    return -1\r\n"
    result = run(tmp_path, source, {"array": [9], "target": 9})
    assert result["submission"]["source"] == source
    assert result["submission"]["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    assert replay_witness(result)["matched"]
    tampered = deepcopy(result)
    tampered["submission"]["source"] += "#changed"
    with pytest.raises(ValueError, match="SHA256"):
        replay_witness(tampered)


@pytest.mark.parametrize("container", ["(0, 1)", "{0, 1}"])
def test_non_list_distances_do_not_become_legal_lists(tmp_path, container):
    r = run(tmp_path, "def solve(x):\n    return " + container, {"n": 2, "source": 0, "edges": [[0, 1, 1]]}, "dijkstra_v1")
    assert r["failure_kind"] == "contract_violation"


@pytest.mark.parametrize("actual, expected, kind", [
    ([0, 12, 4], [0, 7, 4], "shortest_path"), ([0, 2, 4], [0, 7, 4], "shortest_path"),
    ([0, 3, None], [0, None, None], "unreachable")])
def test_graph_certificate(actual, expected, kind):
    case = {"n": 3, "source": 0, "edges": [[0, 2, 4], [2, 1, 3]] if kind == "shortest_path" else []}
    detail = checked_example("dijkstra_v1", case, actual, expected)
    assert detail["kind"] == kind
    if kind == "shortest_path":
        assert detail["vertices"] == [0, 2, 1] and sum(detail["weights"]) == detail["cost"] == 7
    else:
        assert detail["reachable_vertices"] == [0]


def test_witness_return_points_to_real_return(tmp_path):
    case = {"array": [2, 5, 5], "target": 5}
    r = run(tmp_path, "def solve(x):\n    k = 0\n    return k\n", case)
    assert r["witness_explanation"]["matching_indices"] == [1, 2]
    assert r["claims"][-1]["adapter_id"] == "python_returned_index_v1"
    assert r["events"][-1]["return_value"] == 0 and r["diagnosis"]["source_lines"] == [3]
    short = run(tmp_path, "def solve(x):\n    k = 0\n    return k\n", case, trace_limit=1)
    assert short["diagnostic_status"] == "abstained"


def test_pass_on_manual_case_keeps_actual_and_accepts_duplicate(tmp_path):
    r = run(tmp_path, "def solve(data):\n    return 2\n", {"array": [2, 5, 5], "target": 5})
    assert r["manual_check"]["status"] == "pass"
    assert r["manual_check"]["observed"] == 2 and r["manual_check"]["expected"] == 1
    assert not r["claims"]


def test_nonzero_source_and_isolated_vertex():
    case = {"n": 4, "edges": [[2, 3, 6], [3, 0, 2]], "source": 2}
    proof = checked_example("dijkstra_v1", case, [11, None, 0, 6], [8, None, 0, 6])
    assert proof["vertices"] == [2, 3, 0] and proof["cost"] == 8
