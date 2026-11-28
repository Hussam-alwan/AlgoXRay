"""Constraint-aware, strictly decreasing candidate transformations.

The validator remains the authority. This is a bounded greedy search vocabulary,
not a guarantee of global or one-minimal input size.
"""
from .v4_contracts import validate_case, serialize, digest

def complexity(manifest, case):
    size = cost = 0
    for field in manifest["fields"]:
        value = case[field["name"]]
        if type(value) is int:
            cost += abs(value)
        elif type(value) is str:
            size += len(value)
            cost += sum(field["alphabet"].index(x) for x in value)
        elif field["kind"] == "matrix":
            size += sum(map(len, value))
            cost += sum(abs(x) for row in value for x in row)
        else:
            size += len(value)
            cost += sum(abs(x) for x in value)
    return size, cost

def deletion_windows(length, minimum):
    """Try large contiguous removals first, including middle blocks."""
    remove = length - minimum
    while remove > 0:
        starts = list(range(0, length - remove + 1, remove))
        if starts[-1] != length - remove:
            starts.append(length - remove)
        for start in starts:
            yield start, start + remove
        remove //= 2

def numeric_values(value, low, high):
    target = min(high, max(low, 0))
    for v in (target, target + (value-target)//2, low, high):
        if low <= v <= high and abs(v) < abs(value):
            yield v

def candidates(manifest, case):
    from .v4_spec_v2 import bounds, element_bounds

    validate_case(manifest, case)
    fields = manifest["fields"]
    original = complexity(manifest, case)
    seen = set()
    def valid(candidate):
        try:
            serialize(manifest, candidate)
            key = digest(candidate)
            if key not in seen and complexity(manifest, candidate) < original:
                seen.add(key)
                return candidate
        except ValueError:
            pass
        return None

    # Resize a shared dimension in all dependent fields using the same indices.
    for field in fields:
        name = field["name"]
        value = case[name]
        if field["kind"] != "int":
            continue
        dependents = [f for f in fields if name in
                      (f.get("length_from"), f.get("rows_from"), f.get("cols_from"))]
        if not dependents:
            continue
        for start, stop in deletion_windows(value, field["min"]):
            d = {**case, name: value-(stop-start)}
            def cut(seq):
                return seq[:start] + seq[stop:]
            for f in dependents:
                v = case[f["name"]]
                if f["kind"] == "ints":
                    v = cut(v)
                else:
                    if f.get("rows_from") == name:
                        v = cut(v)
                    if f.get("cols_from") == name:
                        v = [cut(row) for row in v]
                d[f["name"]] = v
            candidate = valid(d)
            if candidate is not None:
                yield candidate

    for field in fields:
        name, kind = field["name"], field["kind"]
        v = case[name]
        low, high = field["min"], field["max"]
        if kind == "int":
            low, high = bounds(manifest, field, case)
            for dependent in fields:
                if dependent.get("max_from") == name and case[dependent["name"]]:
                    low = max(low, max(case[dependent["name"]]))
                if dependent.get("min_from") == name and case[dependent["name"]]:
                    high = min(high, min(case[dependent["name"]]))
            options = numeric_values(v, low, high)
        elif kind == "word":
            def words():
                for a,b in deletion_windows(len(v), low):
                    yield v[:a] + v[b:]
                first = field["alphabet"][0]
                yield first * len(v)
                for i in range(len(v)):
                    yield v[:i] + first + v[i+1:]
            options = words()
        else:
            low, high = element_bounds(field, case)
            target = min(high, max(low, 0))
            def arrays():
                if kind == "matrix":
                    yield [[target for x in row] for row in v]
                    for i,row in enumerate(v):
                        for j,x in enumerate(row):
                            for y in numeric_values(x,low,high):
                                yield v[:i]+[row[:j]+[y]+row[j+1:]]+v[i+1:]
                else:
                    yield [target]*len(v)
                    for a,b in deletion_windows(len(v), 0):
                        yield v[:a]+[target]*(b-a)+v[b:]
                    for i,x in enumerate(v):
                        for y in numeric_values(x,low,high):
                            yield v[:i]+[y]+v[i+1:]
            options = arrays()
        for x in options:
            candidate = valid({**case,name:x})
            if candidate is not None:
                yield candidate

def failure_signature(result):
    """Compatible symptoms, not a proof of identical root cause."""
    kind = result.get("kind")
    if kind == "wrong_answer":
        return {"kind":kind}
    if kind == "exception":
        student = result.get("student", {})
        location = student.get("failure_location")
        detail = student.get("detail")
        if type(location) is dict and type(location.get("line")) is int and type(detail) is str:
            return {"kind":kind,"detail":detail,"line":location["line"],
                    "function":location.get("function")}
    return None
