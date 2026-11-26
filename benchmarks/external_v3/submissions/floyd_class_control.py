# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/dynamic_programming/floyd_warshall.py
import math


class Graph:
    def __init__(self, n=0) -> None:  # a graph with Node 0,1,...,N-1
        self.n = n
        self.w = [
            [math.inf for j in range(n)] for i in range(n)
        ]  # adjacency matrix for weight
        self.dp = [
            [math.inf for j in range(n)] for i in range(n)
        ]  # dp[i][j] stores minimum distance from i to j

    def add_edge(self, u, v, w) -> None:
        """
        Adds a directed edge from node u
        to node v with weight w.

        >>> g = Graph(3)
        >>> g.add_edge(0, 1, 5)
        >>> g.dp[0][1]
        5
        """
        self.dp[u][v] = w

    def floyd_warshall(self) -> None:
        """
        Computes the shortest paths between all pairs of
        nodes using the Floyd-Warshall algorithm.

        >>> g = Graph(3)
        >>> g.add_edge(0, 1, 1)
        >>> g.add_edge(1, 2, 2)
        >>> g.floyd_warshall()
        >>> g.show_min(0, 2)
        3
        >>> g.show_min(2, 0)
        inf
        """
        for k in range(self.n):
            for i in range(self.n):
                for j in range(self.n):
                    self.dp[i][j] = min(self.dp[i][j], self.dp[i][k] + self.dp[k][j])

    def show_min(self, u, v):
        """
        Returns the minimum distance from node u to node v.

        >>> g = Graph(3)
        >>> g.add_edge(0, 1, 3)
        >>> g.add_edge(1, 2, 4)
        >>> g.floyd_warshall()
        >>> g.show_min(0, 2)
        7
        >>> g.show_min(1, 0)
        inf
        """
        return self.dp[u][v]

def solve(p):
    g=Graph(p["n"])
    for i in range(p["n"]): g.dp[i][i]=0
    for u,v,w in p["edges"]: g.add_edge(u,v,w)
    g.floyd_warshall()
    return [None if x==float("inf") else x for x in g.dp[p["source"]]]
