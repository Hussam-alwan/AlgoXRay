# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/graphs/dijkstra.py
import heapq


def dijkstra(graph: dict[str, list[tuple[str, int]]], start: str, end: str) -> int:
    """Return the cost of the shortest path between vertices start and end.

    >>> dijkstra(G, "E", "C")
    6
    >>> dijkstra(G2, "E", "F")
    3
    >>> dijkstra(G3, "E", "F")
    3
    """
    heap: list[tuple[int, str]] = [(0, start)]  # (cost, node)
    visited: set[str] = set()
    costs: dict[str, int] = {start: 0}  # Store minimum costs to reach each node

    while heap:
        cost, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        if u == end:
            return cost

        for v, c in graph[u]:
            if v in visited:
                continue
            next_cost = cost + c
            # Only push to heap if a cheaper path is found
            if next_cost < costs.get(v, float("inf")):
                costs[v] = next_cost
                heapq.heappush(heap, (next_cost, v))

    return -1

def solve(payload):
    names = [chr(65+i) for i in range(payload["n"])]
    graph = {name: [] for name in names}
    for u, v, w in payload["edges"]:
        graph[names[u]].append((names[v], w))
    values = [dijkstra(graph, names[payload["source"]], end) for end in names]
    return [None if value == -1 or value == (-1, -1) else value for value in values]
