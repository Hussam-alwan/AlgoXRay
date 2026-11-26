def solve(payload):
    data, key = payload["array"], payload["target"]
    def search(begin, end):
        if begin == end:
            return -1
        split = (begin + end) // 2
        if data[split] == key:
            return split
        if data[split] > key:
            return search(begin, split)
        return search(split + 1, end)
    return search(0, len(data))
