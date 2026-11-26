"""Strict problem contracts, checkers, and independently cross-checked oracles."""
from copy import deepcopy
import math

import networkx as nx
from . import max_subarray


class InvalidCase(ValueError):
    pass


class OracleDisagreement(RuntimeError):
    pass


PROBLEMS = {
    "dijkstra_v1": {
        "id": "dijkstra_v1", "name": "Dijkstra", "name_ar": "أقصر مسار",
        "description_ar": "غراف موجه بأوزان موجبة. الخرج قائمة المسافات من المصدر؛ null للعقدة غير القابلة للوصول.",
        "constraints": {"vertices": [2, 8], "edges_max": 20, "weight": [1, 20]},
        "example": {"n": 3, "edges": [[0, 1, 1], [0, 2, 3], [1, 2, 1]], "source": 0},
    },
    "binary_search_v1": {
        "id": "binary_search_v1", "name": "Binary Search", "name_ar": "البحث الثنائي",
        "description_ar": "مصفوفة مرتبة مع السماح بالتكرار. أي فهرس يحتوي الهدف صحيح؛ -1 عند غيابه.",
        "constraints": {"length": [0, 32], "values": [-20, 20]},
        "example": {"array": [0], "target": 0},
    },
}


PROBLEMS[max_subarray.ID] = max_subarray.METADATA


def validate_case(problem_id, case):
    if problem_id == max_subarray.ID:
        try:
            return max_subarray.validate(case)
        except ValueError as exc:
            raise InvalidCase(str(exc)) from exc
    if problem_id not in PROBLEMS:
        raise InvalidCase("Unknown problem")
    if type(case) is not dict:
        raise InvalidCase("Input must be a JSON object")
    case = deepcopy(case)
    if problem_id == "dijkstra_v1":
        if set(case) != {"n", "edges", "source"}:
            raise InvalidCase("Expected n, edges, source only")
        n, edges, source = case["n"], case["edges"], case["source"]
        if type(n) is not int or not 2 <= n <= 8:
            raise InvalidCase("n must be an integer in [2, 8]")
        if type(source) is not int or not 0 <= source < n:
            raise InvalidCase("source must be an existing vertex")
        if type(edges) is not list or len(edges) > min(20, n * (n - 1)):
            raise InvalidCase("Too many edges or invalid edges list")
        seen = set()
        for e in edges:
            if not isinstance(e, (list, tuple)) or len(e) != 3 or any(type(v) is not int for v in e):
                raise InvalidCase("Each edge must contain three integers")
            u, v, w = e
            if not 0 <= u < n or not 0 <= v < n or u == v or not 1 <= w <= 20:
                raise InvalidCase("Invalid endpoints or weight")
            if (u, v) in seen:
                raise InvalidCase("Duplicate edge")
            seen.add((u, v))
        case["edges"] = [list(e) for e in edges]
    else:
        if set(case) != {"array", "target"}:
            raise InvalidCase("Expected array and target only")
        a, t = case["array"], case["target"]
        if type(a) is not list or len(a) > 32 or any(type(v) is not int or not -20 <= v <= 20 for v in a):
            raise InvalidCase("array must contain at most 32 integers in [-20, 20]")
        if a != sorted(a) or type(t) is not int or not -20 <= t <= 20:
            raise InvalidCase("Array must be sorted and target must be in [-20, 20]")
    return case


def independent_distances(case):
    """Small Floyd-Warshall implementation, independent of NetworkX Bellman-Ford."""
    n = case["n"]
    d = [[math.inf] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
    for u, v, w in case["edges"]:
        d[u][v] = w
    for k in range(n):
        for i in range(n):
            for j in range(n):
                d[i][j] = min(d[i][j], d[i][k] + d[k][j])
    return [None if math.isinf(v) else v for v in d[case["source"]]]


def reference(problem_id, case):
    if problem_id == max_subarray.ID:
        try:
            return max_subarray.reference(case)
        except RuntimeError as exc:
            raise OracleDisagreement(str(exc)) from exc
    if problem_id not in PROBLEMS:
        raise InvalidCase('Unknown problem')
    if problem_id == "binary_search_v1":
        return case["array"].index(case["target"]) if case["target"] in case["array"] else -1
    graph = nx.DiGraph()
    graph.add_nodes_from(range(case["n"]))
    graph.add_weighted_edges_from(case["edges"])
    d = nx.single_source_bellman_ford_path_length(graph, case["source"])
    result = [d.get(i) for i in range(case["n"])]
    if result != independent_distances(case):
        raise OracleDisagreement("Bellman-Ford and independent Floyd-Warshall disagree")
    return result


def check_output(problem_id, case, actual, expected):
    """Return None, contract_violation or wrong_answer; never assume text equality."""
    if problem_id == max_subarray.ID:
        return max_subarray.check(case, actual, expected)
    if problem_id not in PROBLEMS:
        raise InvalidCase("Unknown problem")
    if problem_id == "dijkstra_v1":
        if type(actual) is not list or len(actual) != case["n"]:
            return "contract_violation"
        if any(v is not None and (type(v) is not int or v < 0) for v in actual):
            return "contract_violation"
        return None if actual == expected else "wrong_answer"
    if type(actual) is not int:
        return "contract_violation"
    a, t = case["array"], case["target"]
    if actual == -1:
        return None if t not in a else "wrong_answer"
    return None if 0 <= actual < len(a) and a[actual] == t else "wrong_answer"


def size(problem_id, case):
    if problem_id not in PROBLEMS:
        raise InvalidCase('Unknown problem')
    return {"vertices": case["n"], "edges": len(case["edges"])} if problem_id == "dijkstra_v1" else {"length": len(case["array"])}


def complexity(problem_id, case):
    if problem_id == max_subarray.ID:
        return (len(case['array']), sum(abs(v) for v in case['array']))
    if problem_id not in PROBLEMS:
        raise InvalidCase('Unknown problem')
    if problem_id == "dijkstra_v1":
        return (len(case["edges"]), case["n"], sum(w for _, _, w in case["edges"]))
    return (len(case["array"]), sum(abs(v) for v in case["array"]) + abs(case["target"]))
