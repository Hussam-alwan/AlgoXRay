"""Exact bounded output encoding, independent of lossy trace snapshots."""
import math

MAX_NODES = 4096
MAX_DEPTH = 32
MAX_STRING = 65536
MAX_INTEGER_BITS = 1024


class UnsupportedOutput(ValueError):
    pass


def encode_output(value):
    """Preserve supported JSON values exactly; never turn a tuple into a list."""
    remaining = MAX_NODES
    active = set()

    def visit(item, depth):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > MAX_DEPTH:
            raise UnsupportedOutput("output structure exceeds limit")
        kind = type(item)
        if item is None or kind is bool:
            return item
        if kind is int:
            if item.bit_length() > MAX_INTEGER_BITS:
                raise UnsupportedOutput("integer exceeds limit")
            return item
        if kind is float:
            if not math.isfinite(item):
                raise UnsupportedOutput("non-finite float")
            return item
        if kind is str:
            if len(item) > MAX_STRING:
                raise UnsupportedOutput("string exceeds limit")
            return item
        if kind not in (list, dict):
            raise UnsupportedOutput("unsupported output type: " + kind.__name__)
        identity = id(item)
        if identity in active:
            raise UnsupportedOutput("cyclic output")
        active.add(identity)
        try:
            if len(item) > remaining:
                raise UnsupportedOutput("output structure exceeds limit")
            if kind is list:
                return [visit(child, depth + 1) for child in item]
            if any(type(key) is not str or len(key) > MAX_STRING for key in item):
                raise UnsupportedOutput("invalid object key")
            return {key: visit(child, depth + 1) for key, child in item.items()}
        finally:
            active.remove(identity)

    return visit(value, 0)
