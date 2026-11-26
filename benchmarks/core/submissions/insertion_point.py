from bisect import bisect_left

def solve(payload):
    position = bisect_left(payload["array"], payload["target"])
    return position
