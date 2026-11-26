# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/dynamic_programming/max_subarray_sum.py
from collections.abc import Sequence


def max_subarray_sum(
    arr: Sequence[float], allow_empty_subarrays: bool = False
) -> float:
    """
    Solves the maximum subarray sum problem using Kadane's algorithm.
    :param arr: the given array of numbers
    :param allow_empty_subarrays: if True, then the algorithm considers empty subarrays

    >>> max_subarray_sum([2, 8, 9])
    19
    >>> max_subarray_sum([0, 0])
    0
    >>> max_subarray_sum([-1.0, 0.0, 1.0])
    1.0
    >>> max_subarray_sum([1, 2, 3, 4, -2])
    10
    >>> max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4])
    6
    >>> max_subarray_sum([2, 3, -9, 8, -2])
    8
    >>> max_subarray_sum([-2, -3, -1, -4, -6])
    -1
    >>> max_subarray_sum([-2, -3, -1, -4, -6], allow_empty_subarrays=True)
    0
    >>> max_subarray_sum([])
    0
    """
    if not arr:
        return 0

    max_sum = 0 if allow_empty_subarrays else float("-inf")
    curr_sum = 0.0
    for num in arr:
        curr_sum = max(0 if allow_empty_subarrays else num, curr_sum + num)
        max_sum = curr_sum

    return max_sum

def solve(payload):
    x = max_subarray_sum(payload["array"])
    return int(x) if type(x) is float and x.is_integer() else x
