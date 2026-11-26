def solve(payload):
    n=payload['n']; d=[[float('inf')]*n for _ in range(n)]
    for i in range(n): d[i][i]=0
    for u,v,w in payload['edges']: d[u][v]=w
    for k in range(n):
        for i in range(n):
            for j in range(n): d[i][j]=min(d[i][j],d[i][k]+d[k][j])
    return d[payload['source']]
