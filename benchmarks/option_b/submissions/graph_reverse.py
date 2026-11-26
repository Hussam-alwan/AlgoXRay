def solve(payload):
    d=[None]*payload['n']; d[payload['source']]=0
    for _ in range(payload['n']-1):
        for u,v,w in payload['edges']:
            if d[v] is not None and (d[u] is None or d[v]+w<d[u]): d[u]=d[v]+w
    return d
