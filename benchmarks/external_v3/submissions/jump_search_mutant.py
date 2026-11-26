# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/searches/jump_search.py
import math
from collections.abc import Sequence
from typing import Any, Protocol


class Comparable(Protocol):
    def __lt__(self, other: Any, /) -> bool: ...


def jump_search[T: Comparable](arr: Sequence[T], item: T) -> int:
    """
    Python implementation of the jump search algorithm.
    Return the index if the `item` is found, otherwise return -1.

    Examples:
    >>> jump_search([0, 1, 2, 3, 4, 5], 3)
    3
    >>> jump_search([-5, -2, -1], -1)
    2
    >>> jump_search([0, 5, 10, 20], 8)
    -1
    >>> jump_search([0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610], 55)
    10
    >>> jump_search(["aa", "bb", "cc", "dd", "ee", "ff"], "ee")
    4
    >>> jump_search([], 1)
    -1
    """
    if not arr:
        return -1
    arr_size = len(arr)
    block_size = int(math.sqrt(arr_size))

    prev = 0
    step = block_size
    while arr[min(step, arr_size) - 1] < item:
        prev = step
        step += block_size
        if prev >= arr_size:
            return -1

    while arr[prev] <= item:
        prev += 1
        if prev == min(step, arr_size):
            return -1
    if arr[prev] == item:
        return prev
    return -1

def solve(p):
    return jump_search(p["array"],p["target"])
