"""Versioned input strategies for catalog packages."""
import random

from .v4_contracts import dimension, digest, parse_stdin, serialize
from .v4_spec_v2 import bounds, element_bounds


VERSION = 1
LEVELS = ("published", "minimum", "maximum", "near_limits", "middle", "varied")
PATTERNS = {"duplicate", "ascending", "descending", "left_cluster", "right_cluster",
            "interior_cluster", "dominant_inner_gap"}


def validate_test_plan(package):
    config = package["test_plan"]
    if type(config) is not dict or set(config) != {"version", "patterns"} or type(config["version"]) is not int or config["version"] != VERSION:
        raise ValueError("Unsupported test plan")
    patterns = config["patterns"]
    if type(patterns) is not dict:
        raise ValueError("Expected patterns indexed by field name")
    fields = {f["name"]: f for f in package["manifest"]["fields"]}
    for field, strategies in patterns.items():
        spec = fields.get(field, {})
        if spec.get("kind") != "ints" or type(strategies) is not list or len(strategies) > len(PATTERNS):
            raise ValueError("Patterns require an integer list")
        if any(type(strategy) is not str or strategy not in PATTERNS for strategy in strategies):
            raise ValueError("Unsupported list pattern")
        if spec.get("unique") and set(strategies) - {"ascending", "descending"}:
            raise ValueError("Cluster and duplicate patterns require non-unique elements")
        if spec.get("sorted") and "descending" in strategies:
            raise ValueError("Descending pattern conflicts with sorted input")


def _position(lo, hi, level, rng):
    if level == "minimum":
        return lo
    if level == "maximum":
        return hi
    if level == "near_limits":
        return rng.choice((lo, min(lo + 1, hi), max(hi - 1, lo), hi))
    if level == "middle":
        return (lo + hi) // 2
    return rng.randint(lo, hi)


def _list_values(n, lo, hi, level, rng, field, pattern):
    if field.get("unique"):
        if level == "minimum":
            values = list(range(lo, lo + n))
        elif level == "maximum":
            values = list(range(hi - n + 1, hi + 1))
        else:
            values = rng.sample(range(lo, hi + 1), n)
    else:
        start, end = lo, hi
        span = (hi - lo) // 8
        if pattern == "left_cluster":
            end = lo + span
        elif pattern == "right_cluster":
            start = hi - span
        elif pattern == "interior_cluster":
            start, end = (lo + hi) // 2 - span, (lo + hi) // 2 + span
        if pattern == "duplicate":
            values = [rng.randint(lo, hi)] * n
        elif pattern == "dominant_inner_gap":
            values = [rng.randint(lo, lo + span) if i % 2 == 0 else rng.randint(hi - span, hi) for i in range(n)]
        else:
            values = [_position(start, end, level, rng) for _ in range(n)]
    if field.get("sorted") or pattern == "ascending":
        values.sort()
    elif pattern == "descending":
        values.sort(reverse=True)
    return values


def construct(manifest, seed, level, patterns=None):
    """Uniform conditional sampling when level is varied and patterns are empty."""
    rng = random.Random(seed)
    patterns = patterns or {}

    def body():
        case = {}
        for field in manifest["fields"]:
            name, kind = field["name"], field["kind"]
            lo, hi = field["min"], field["max"]
            if kind == "int":
                value = _position(*bounds(manifest, field, case), level, rng)
            elif kind == "word":
                size = _position(lo, hi, level, rng)
                value = "".join(rng.choice(field["alphabet"]) for _ in range(size))
            elif kind == "matrix":
                value = [[_position(lo, hi, level, rng) for _ in range(dimension(field, "cols", case))]
                         for _ in range(dimension(field, "rows", case))]
            else:
                n = dimension(field, "length", case)
                lo, hi = element_bounds(field, case)
                choices = patterns.get(name, [])
                pattern = rng.choice(choices) if level == "varied" and choices else None
                value = _list_values(n, lo, hi, level, rng, field, pattern)
            case[name] = value
        return case

    if "repeat" in manifest:
        repeat = manifest["repeat"]
        t = _position(repeat["min"], repeat["max"], level, rng)
        return {"t": t, "cases": [body() for _ in range(t)]}
    return body()


def plan(package, seed, count, generator="catalog"):
    """Yield saved tests first, then seed-derived proposals in declared order."""
    manifest = package["manifest"]
    for control in package["controls"]:
        origin = control.get("origin", "owner_reviewed")
        yield {"case": control["case"], "level": "published" if origin == "published" else "varied",
               "origin": origin, "strategy": "saved_control"}
    rng = random.Random(seed)
    for index in range(count):
        level = "varied" if generator == "uniform_random" else LEVELS[1 + index % (len(LEVELS) - 1)]
        case_seed = rng.getrandbits(32)
        patterns = package["test_plan"]["patterns"] if generator == "catalog" else None
        case = construct(manifest, case_seed, level, patterns)
        yield {"case": case, "level": level, "seed": case_seed,
               "origin": "reference_derived", "strategy": generator}


def unique_proposals(manifest, proposals, stats):
    """Deduplicate canonical stdin and record proposal losses before execution."""
    seen = set()
    for row in proposals:
        stats["proposed"] += 1
        try:
            stdin = serialize(manifest, row["case"])
            if parse_stdin(manifest, stdin) != row["case"]:
                raise ValueError("Input did not round trip")
        except ValueError:
            stats["rejected_invalid"] += 1
            continue
        identity = digest(stdin)
        if identity in seen:
            stats["duplicate"] += 1
            continue
        seen.add(identity)
        yield row, identity
