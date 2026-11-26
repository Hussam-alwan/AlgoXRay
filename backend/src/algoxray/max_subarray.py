"""Non-empty maximum contiguous subarray; independent exhaustive and linear references."""
from hypothesis import strategies as st

ID = "max_subarray_v1"
METADATA = {"id": ID, "name": "Maximum Subarray", "name_ar": "أكبر مجموع لمقطع متصل",
            "description_ar": "مصفوفة غير فارغة، المطلوب أكبر مجموع لمقطع متصل غير فارغ.",
            "constraints": {"length": [1, 24], "values": [-20, 20]},
            "example": {"array": [-5, -2, -7]}}

def validate(case):
    if type(case) is not dict or set(case) != {"array"}:
        raise ValueError("Expected array only")
    a = case["array"]
    if type(a) is not list or not 1 <= len(a) <= 24 or any(type(v) is not int or not -20 <= v <= 20 for v in a):
        raise ValueError("Expected 1–24 integers in [-20, 20]")
    return {"array": a.copy()}

def best_segment(a):
    return max((sum(a[i:j]), i, j) for i in range(len(a)) for j in range(i + 1, len(a) + 1))

def reference(case):
    a = case["array"]
    exhaustive = best_segment(a)[0]
    best = current = a[0]
    for v in a[1:]:
        current = max(v, current + v)
        best = max(best, current)
    if exhaustive != best:
        raise RuntimeError("Independent subarray oracles disagree")
    return exhaustive

def check(case, actual, expected):
    if type(actual) is not int:
        return "contract_violation"
    return None if actual == expected else "wrong_answer"

def strategy():
    return st.builds(lambda a: {"array": a}, st.lists(st.integers(-20, 20), min_size=1, max_size=24))

def random_case(rng):
    return {"array": [rng.randint(-20, 20) for _ in range(rng.randint(1, 24))]}

def smaller(case):
    a = case["array"]
    if len(a) > 1:
        for i in range(len(a)):
            yield {"array": a[:i] + a[i+1:]}
    for i, v in enumerate(a):
        if v:
            yield {"array": a[:i] + [0] + a[i+1:]}

def certificate(case, actual):
    total, start, end = best_segment(case["array"])
    return {"kind": "max_subarray", "start": start, "end_exclusive": end,
            "segment": case["array"][start:end], "sum": total, "returned": actual}
