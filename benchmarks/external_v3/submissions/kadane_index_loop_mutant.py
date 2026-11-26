# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/c9ee6ed1887fadd25c1c43c31ed55a99b2be5f24/maths/largest_subarray_sum.py
from sys import maxsize


def max_sub_array_sum(a: list, size: int = 0):
    """
    >>> max_sub_array_sum([-13, -3, -25, -20, -3, -16, -23, -12, -5, -22, -15, -4, -7])
    -3
    """
    size = size or len(a)
    max_so_far = -maxsize - 1
    max_ending_here = 0
    for i in range(0, size):
        max_ending_here = a[i]
        max_so_far = max(max_so_far, max_ending_here)
        max_ending_here = max(max_ending_here, 0)
    return max_so_far

def solve(p):
    return max_sub_array_sum(p["array"])
