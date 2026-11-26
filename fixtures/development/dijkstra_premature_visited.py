"""Authored defective fixture: marking a vertex seen on insertion."""
from heapq import heappop, heappush


def solve(payload):
    adj = [[] for _ in range(payload['n'])]
    for u, v, w in payload['edges']:
        adj[u].append((v, w))
    dist = [float('inf')] * payload['n']
    dist[payload['source']] = 0
    seen = {payload['source']}
    heap = [(0, payload['source'])]
    while heap:
        d, u = heappop(heap)
        for v, w in adj[u]:
            if v in seen:
                continue
            if d + w < dist[v]:
                dist[v] = d + w
                seen.add(v)
                heappush(heap, (dist[v], v))
    return dist
