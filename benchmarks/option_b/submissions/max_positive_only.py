def solve(payload):
    a=payload['array']
    return sum(x for x in a if x>0) if max(a)>0 else max(a)
