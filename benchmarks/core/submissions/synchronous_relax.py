def solve(payload):
    n = payload["n"]
    last = [float("inf")] * n
    last[payload["source"]] = 0
    for _ in range(n-1):
        nxt = last.copy()
        for a, b, w in payload["edges"]:
            nxt[b] = min(nxt[b], last[a] + w)
        last = nxt
    return last
