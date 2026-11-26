def solve(payload):
    a = payload['array']
    best = a[0]
    for i in range(len(a)):
        total = 0
        for x in a[i:]:
            total += x
            best = max(best, total)
    return best
