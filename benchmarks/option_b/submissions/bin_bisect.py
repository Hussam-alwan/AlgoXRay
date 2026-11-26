from bisect import bisect_left
def solve(payload):
    a,t=payload['array'],payload['target']
    i=bisect_left(a,t)
    return i if i<len(a) and a[i]==t else -1
