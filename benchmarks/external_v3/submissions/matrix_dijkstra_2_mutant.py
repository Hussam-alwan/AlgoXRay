# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/graphs/dijkstra_2.py
def min_dist(mdist, vset, v):
    """
    Returns the vertex with the minimum distance from the source vertex
    that has not yet been visited.

    >>> min_dist([0, 4, 2, float('inf')], [True, False, False, False], 4)
    2
    >>> min_dist([0, 4, 2, 1], [True, False, True, False], 4)
    3
    >>> min_dist([0, 4, 2, 1], [True, True, True, True], 4)
    -1
    >>> min_dist([float('inf'), float('inf')], [False, False], 2)
    -1
    >>> min_dist([0, 1, 6], [True, False, False], 3)
    1
    """
    min_val = float("inf")
    min_ind = -1
    for i in range(v):
        if (not vset[i]) and mdist[i] < min_val:
            min_ind = i
            min_val = mdist[i]
    return min_ind


def dijkstra(graph, v, src) -> None:
    """
    Runs Dijkstra's algorithm and prints distances.

    Calculate the shortest path from source to all other vertices
    using Dijkstra's algorithm.

    >>> g = [
    ...     [0.0, 5.0, float('inf'), 10.0],
    ...     [float('inf'), 0.0, 3.0, float('inf')],
    ...     [float('inf'), float('inf'), 0.0, 1.0],
    ...     [float('inf'), float('inf'), float('inf'), 0.0],
    ... ]
    >>> dijkstra(g, 4, 0)
    Vertex Distance
    0    0
    1    5
    2    8
    3    9
    >>> g2 = [
    ...     [0.0, float('inf')],
    ...     [float('inf'), 0.0],
    ... ]
    >>> dijkstra(g2, 2, 0)
    Vertex Distance
    0    0
    1    INF
    >>> dijkstra([[0.0]], 1, 0)
    Vertex Distance
    0    0
    >>> graph = [[0.0, 1.0, 6.0],\
                [float("inf"), 0.0, 3.0],\
                [float("inf"), float("inf"), 0.0]]
    >>> dijkstra(graph, 3, 0) # doctest: +NORMALIZE_WHITESPACE
    Vertex Distance
    0    0
    1    1
    2    4
    """
    mdist = [float("inf") for _ in range(v)]
    vset = [False for _ in range(v)]
    mdist[src] = 0.0

    for _ in range(v - 1):
        u = min_dist(mdist, vset, v)
        vset[u] = True

        for i in range(v):
            if (
                (not vset[i])
                and graph[u][i] != float("inf")
                and mdist[u] + graph[u][i] < mdist[i]
            ):
                mdist[i] = graph[u][i]

    return mdist

def solve(p):
    n=p["n"]
    g=[[float("inf")]*n for _ in range(n)]
    for i in range(n): g[i][i]=0
    for u,v,w in p["edges"]: g[u][v]=w
    return [None if x==float("inf") else int(x) if type(x) is float and x.is_integer() else x for x in dijkstra(g,n,p["source"])]
