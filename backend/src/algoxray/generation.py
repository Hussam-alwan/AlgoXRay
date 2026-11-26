import random
from hypothesis import strategies as st


@st.composite
def graph_cases(draw):
    n = draw(st.integers(2, 8))
    source = draw(st.integers(0, n - 1))
    pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    items = draw(st.lists(st.tuples(st.sampled_from(pairs), st.integers(1, 20)),
                         max_size=min(20, len(pairs)), unique_by=lambda x: x[0]))
    return {"n": n, "edges": [[u, v, w] for (u, v), w in items], "source": source}


def strategy_for(problem_id):
    if problem_id == "dijkstra_v1":
        return graph_cases()
    return st.builds(lambda array, target: {"array": sorted(array), "target": target},
                     st.lists(st.integers(-20, 20), max_size=32), st.integers(-20, 20))


def random_case(problem_id, rng: random.Random):
    if problem_id == "dijkstra_v1":
        n = rng.randint(2, 8)
        pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
        picked = rng.sample(pairs, rng.randint(0, min(20, len(pairs))))
        return {"n": n, "edges": [[u, v, rng.randint(1, 20)] for u, v in picked], "source": rng.randrange(n)}
    return {"array": sorted(rng.randint(-20, 20) for _ in range(rng.randint(0, 32))), "target": rng.randint(-20, 20)}
