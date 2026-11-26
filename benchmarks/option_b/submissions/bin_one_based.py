def solve(payload):
    a,t=payload['array'],payload['target']
    for i,x in enumerate(a,1):
        if x==t: return i
    return -1
