def solve(payload):
    size, start = payload["n"], payload["source"]
    distances = [float("inf")] * size
    distances[start] = 0
    unused = set(range(size))
    while unused:
        node = min(unused, key=distances.__getitem__)
        unused.remove(node)
        for a, b, weight in payload["edges"]:
            if a == node and distances[b] > distances[a] + weight:
                distances[b] = distances[a] + weight
    return distances
