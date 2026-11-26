"""Authored evaluation fixture: reverses directed edges."""
from heapq import heappop, heappush


def solve(payload):
    adj = [[] for _ in range(payload['n'])]
    for u, v, w in payload['edges']:
        adj[v].append((u, w))
    dist = [float('inf')] * payload['n']
    dist[payload['source']] = 0
    heap = [(0, payload['source'])]
    while heap:
        d, u = heappop(heap)
        if d != dist[u]:
            continue
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heappush(heap, (dist[v], v))
    return dist
