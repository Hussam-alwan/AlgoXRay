# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/c9ee6ed1887fadd25c1c43c31ed55a99b2be5f24/dynamic_programming/max_sum_contiguous_subsequence.py
def max_subarray_sum(nums: list) -> int:
    """
    >>> max_subarray_sum([6 , 9, -1, 3, -7, -5, 10])
    17
    """
    if not nums:
        return 0
    n = len(nums)

    res, s, s_pre = nums[0], nums[0], nums[0]
    for i in range(1, n):
        s = max(nums[i], s_pre + nums[i])
        s_pre = s
        res = min(res, s)
    return res

def solve(p):
    return max_subarray_sum(p["array"])
