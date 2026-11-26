def solve(payload):
    d=[None]*payload['n']; d[payload['source']]=0
    for _ in range(payload['n']-1):
        for u,v,w in payload['edges']:
            if d[u] is not None and (d[v] is None or max(d[u],w)<d[v]): d[v]=max(d[u],w)
    return d
