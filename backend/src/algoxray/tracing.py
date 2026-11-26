"""Bounded snapshots. Values are copied, never references into a running frame."""
import math

SELECTED = {"dist", "heap", "seen", "visited", "d", "u", "v", "w", "arr", "target", "lo", "hi", "mid",
            "distance", "node", "start", "end", "nextnode", "unvisited_nodes", "visited_nodes"}


def safe_value(value, depth=0):
    if value is None or type(value) in (bool, int, str):
        return value[:2000] if type(value) is str else value
    if type(value) is float:
        if math.isinf(value) and value > 0:
            return None
        return value if math.isfinite(value) else {"invalid_number": str(value)}
    if depth >= 5:
        return "<depth limit>"
    if type(value) in (list, tuple, set):
        items = sorted(value) if type(value) is set and all(type(v) is int for v in value) else list(value)
        result = [safe_value(v, depth + 1) for v in items[:64]]
        if len(items) > 64:
            result.append("<item limit>")
        return result
    if type(value) is dict:
        return {str(k)[:100]: safe_value(v, depth + 1) for k, v in list(value.items())[:64]}
    return "<" + type(value).__name__ + ">"
