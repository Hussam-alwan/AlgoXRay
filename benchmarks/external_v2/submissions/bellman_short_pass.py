# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/graphs/bellman_ford.py
from __future__ import annotations


def print_distance(distance: list[float], src) -> None:
    print(f"Vertex\tShortest Distance from vertex {src}")
    for i, d in enumerate(distance):
        print(f"{i}\t\t{d}")


def check_negative_cycle(
    graph: list[dict[str, int]], distance: list[float], edge_count: int
) -> bool:
    for j in range(edge_count):
        u, v, w = (graph[j][k] for k in ["src", "dst", "weight"])
        if distance[u] != float("inf") and distance[u] + w < distance[v]:
            return True
    return False


def bellman_ford(
    graph: list[dict[str, int]], vertex_count: int, edge_count: int, src: int
) -> list[float]:
    """
    Returns shortest paths from a vertex src to all
    other vertices.
    >>> edges = [(2, 1, -10), (3, 2, 3), (0, 3, 5), (0, 1, 4)]
    >>> g = [{"src": s, "dst": d, "weight": w} for s, d, w in edges]
    >>> bellman_ford(g, 4, 4, 0)
    [0.0, -2.0, 8.0, 5.0]
    >>> g = [{"src": s, "dst": d, "weight": w} for s, d, w in edges + [(1, 3, 5)]]
    >>> bellman_ford(g, 4, 5, 0)
    Traceback (most recent call last):
     ...
    Exception: Negative cycle found
    """
    distance = [float("inf")] * vertex_count
    distance[src] = 0.0

    for _ in range(vertex_count - 2):
        for j in range(edge_count):
            u, v, w = (graph[j][k] for k in ["src", "dst", "weight"])

            if distance[u] != float("inf") and distance[u] + w < distance[v]:
                distance[v] = distance[u] + w

    negative_cycle_exists = check_negative_cycle(graph, distance, edge_count)
    if negative_cycle_exists:
        raise Exception("Negative cycle found")

    return distance

def solve(payload):
    graph = [{"src":u,"dst":v,"weight":w} for u,v,w in payload["edges"]]
    vals = bellman_ford(graph, payload["n"], len(graph), payload["source"])
    return [None if v == float("inf") else int(v) if type(v) is float and v.is_integer() else v for v in vals]
