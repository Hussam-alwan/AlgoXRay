"""Concrete, input-level evidence. These values do not identify a faulty source line."""
from collections import deque


def checked_example(problem, case, actual, expected):
    if problem == "binary_search_v1":
        array, target = case["array"], case["target"]
        return {"kind": "membership", "target": target, "returned": actual,
                "matching_indices": [i for i, value in enumerate(array) if value == target],
                "returned_value": array[actual] if 0 <= actual < len(array) else None}

    target = next(i for i, answer in enumerate(actual) if answer != expected[i])
    source = case["source"]
    if expected[target] is None:
        return {"kind": "unreachable", "source": source, "target": target, "returned": actual[target],
                "reachable_vertices": [i for i, distance in enumerate(expected) if distance is not None]}
    # Tight edges preserve the checked reference distance; positive weights make progress strict.
    queue, parent = deque([source]), {source: None}
    while queue and target not in parent:
        u = queue.popleft()
        for a, v, weight in case["edges"]:
            if a == u and v not in parent and expected[u] + weight == expected[v]:
                parent[v] = (u, weight)
                queue.append(v)
    vertices, weights = [target], []
    while vertices[-1] != source:
        u, weight = parent[vertices[-1]]
        vertices.append(u)
        weights.append(weight)
    return {"kind": "shortest_path", "source": source, "target": target,
            "vertices": list(reversed(vertices)), "weights": list(reversed(weights)),
            "cost": expected[target], "returned": actual[target]}
