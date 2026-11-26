def solve(payload):
    result = [float("inf")] * payload["n"]
    result[payload["source"]] = 0
    for origin, dest, weight in payload["edges"]:
        result[dest] = min(result[dest], result[origin] + weight)
    return result
