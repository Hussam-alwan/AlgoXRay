def solve(payload):
    a,t=payload['array'],payload['target']
    lo,hi=0,len(a)-1
    while lo<=hi:
        if a[lo]==t: return lo
        if a[hi]==t: return hi
        lo+=1
        hi-=1
    return -1
