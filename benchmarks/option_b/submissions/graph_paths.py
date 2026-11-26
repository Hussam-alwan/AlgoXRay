def solve(payload):
    n,s=payload['n'],payload['source']
    best=[None]*n
    def visit(u,cost,seen):
        if best[u] is None or cost<best[u]: best[u]=cost
        for a,b,w in payload['edges']:
            if a==u and b not in seen: visit(b,cost+w,seen|{b})
    visit(s,0,{s})
    return best
