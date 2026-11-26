"""Legal structural reduction candidates, independent of execution orchestration."""
from copy import deepcopy
from . import max_subarray

def smaller_cases(problem_id, case):
    if problem_id == max_subarray.ID:
        yield from max_subarray.smaller(case)
    elif problem_id == "dijkstra_v1":
        for i in range(len(case["edges"])):
            yield {**case, "edges": case["edges"][:i] + case["edges"][i + 1:]}
        if case["n"] > 2:
            for deleted in range(case["n"]):
                if deleted == case["source"]:
                    continue
                remap = {v: i for i, v in enumerate(v for v in range(case["n"]) if v != deleted)}
                yield {"n": case["n"] - 1, "source": remap[case["source"]],
                       "edges": [[remap[u], remap[v], w] for u, v, w in case["edges"] if u != deleted and v != deleted]}
        for i, (_, _, weight) in enumerate(case["edges"]):
            if weight > 1:
                edges = deepcopy(case["edges"])
                edges[i][2] = 1
                yield {**case, "edges": edges}
    elif problem_id == "binary_search_v1":
        for i in range(len(case["array"])):
            yield {**case, "array": case["array"][:i] + case["array"][i + 1:]}


    else:
        raise ValueError("Unknown problem")
