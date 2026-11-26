def solve(payload):
    a,t=payload['array'],payload['target']
    for i in range(len(a)-1,-1,-1):
        if a[i]==t:
            return i
    return -1
