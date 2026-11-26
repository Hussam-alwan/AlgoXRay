from collections import deque
def solve(payload):
    d=[None]*payload['n']
    s=payload['source']; d[s]=0; q=deque([s])
    while q:
        u=q.popleft()
        for a,b,w in payload['edges']:
            if a==u and (d[b] is None or d[u]+w<d[b]):
                d[b]=d[u]+w; q.append(b)
    return d
