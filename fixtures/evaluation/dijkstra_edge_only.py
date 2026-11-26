"""Authored evaluation fixture: forgets the prefix path distance."""
from heapq import heappop, heappush


def solve(payload):
    adj = [[] for _ in range(payload['n'])]
    for u, v, w in payload['edges']:
        adj[u].append((v, w))
    dist = [float('inf')] * payload['n']
    dist[payload['source']] = 0
    heap = [(0, payload['source'])]
    while heap:
        d, u = heappop(heap)
        if d != dist[u]:
            continue
        for v, w in adj[u]:
            if w < dist[v]:
                dist[v] = w
                heappush(heap, (dist[v], v))
    return dist
