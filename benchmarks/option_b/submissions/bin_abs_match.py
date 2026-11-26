def solve(payload):
    for i,x in enumerate(payload['array']):
        if abs(x)==abs(payload['target']): return i
    return -1
