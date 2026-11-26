from collections import deque

def solve(payload):
    n, source = payload["n"], payload["source"]
    links = [[] for _ in range(n)]
    for a, b, cost in payload["edges"]:
        links[a].append(b)
    steps = [None] * n
    steps[source] = 0
    todo = deque([source])
    while todo:
        node = todo.popleft()
        for nxt in links[node]:
            if steps[nxt] is None:
                steps[nxt] = steps[node] + 1
                todo.append(nxt)
    return steps
