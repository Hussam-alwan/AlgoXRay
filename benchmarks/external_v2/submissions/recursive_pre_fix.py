# Derived from TheAlgorithms/Python (MIT); see LICENSE.txt and manifest.json.
# Upstream: https://github.com/TheAlgorithms/Python/blob/c4234192facc1b13ad3cb7be25dbd829c32fbe2d/searches/binary_search.py
def binary_search_by_recursion(sorted_collection, item, left, right):

    """Pure implementation of binary search algorithm in Python by recursion

    Be careful collection must be sorted, otherwise result will be
    unpredictable
    First recursion should be started with left=0 and right=(len(sorted_collection)-1)

    :param sorted_collection: some sorted collection with comparable items
    :param item: item value to search
    :return: index of found item or None if item is not found

    Examples:
    >>> binary_search_std_lib([0, 5, 7, 10, 15], 0)
    0

    >>> binary_search_std_lib([0, 5, 7, 10, 15], 15)
    4

    >>> binary_search_std_lib([0, 5, 7, 10, 15], 5)
    1

    >>> binary_search_std_lib([0, 5, 7, 10, 15], 6)

    """
    midpoint = left + (right - left) // 2

    if sorted_collection[midpoint] == item:
        return midpoint
    elif sorted_collection[midpoint] > item:
        return binary_search_by_recursion(sorted_collection, item, left, midpoint-1)
    else:
        return binary_search_by_recursion(sorted_collection, item, midpoint+1, right)

def solve(payload):
    a = payload["array"]
    x = binary_search_by_recursion(a, payload["target"], 0, len(a)-1)
    return -1 if x is None else x
