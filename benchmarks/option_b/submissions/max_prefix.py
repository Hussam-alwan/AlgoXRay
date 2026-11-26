def solve(payload):
    prefix = minimum = 0
    best = -10**9
    for x in payload['array']:
        prefix += x
        best = max(best, prefix-minimum)
        minimum = min(minimum, prefix)
    return best
