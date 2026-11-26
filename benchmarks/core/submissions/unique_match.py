def solve(payload):
    items, key = payload["array"], payload["target"]
    seen = [i for i, value in enumerate(items) if value == key]
    return seen[0] if len(seen) == 1 else -1
