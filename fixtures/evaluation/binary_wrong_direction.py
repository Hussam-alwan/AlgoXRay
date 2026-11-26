"""Authored evaluation fixture: searches the wrong half."""


def solve(payload):
    arr, target = payload['array'], payload['target']
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            hi = mid - 1
        else:
            lo = mid + 1
    return -1
