def solve(payload):
    a=payload['array']
    return max(sum(a[:j]) for j in range(1,len(a)+1))
