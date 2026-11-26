def solve(payload):
    best = current = 0
    for value in payload["array"]:
        current = max(0, current + value)
        best = max(best, current)
    return best
