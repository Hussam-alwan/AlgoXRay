def solve(payload):
    d=[None]*payload['n']; s=payload['source']; d[s]=0
    for u,v,w in payload['edges']:
        if u==s: d[v]=w
    return d
