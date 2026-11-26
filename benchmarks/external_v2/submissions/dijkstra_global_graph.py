# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/12a16d63b7bdc1da0e0b215dfd5d8b938234f4ed/graphs/dijkstra.py
import heapq


def dijkstra(graph, start, end):
    heap = [(0, start)]  # cost from start node,end node
    visited = []
    while heap:
        (cost, u) = heapq.heappop(heap)
        if u in visited:
            continue
        visited.append(u)
        if u == end:
            return cost
        for v, c in G[u]:
            if v in visited:
                continue
            next = cost + c
            heapq.heappush(heap, (next, v))
    return (-1, -1)


G = {'A': [['B', 2], ['C', 5]],
     'B': [['A', 2], ['D', 3], ['E', 1]],
     'C': [['A', 5], ['F', 3]],
     'D': [['B', 3]],
     'E': [['B', 1], ['F', 3]],
     'F': [['C', 3], ['E', 3]]}

def solve(payload):
    names = [chr(65+i) for i in range(payload["n"])]
    graph = {name: [] for name in names}
    for u, v, w in payload["edges"]:
        graph[names[u]].append((names[v], w))
    values = [dijkstra(graph, names[payload["source"]], end) for end in names]
    return [None if value == -1 or value == (-1, -1) else value for value in values]
