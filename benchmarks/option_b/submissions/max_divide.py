def solve(payload):
    def work(a):
        if len(a)==1:
            return a[0]
        m=len(a)//2
        left,right=a[:m],a[m:]
        cross=max(sum(left[i:]) for i in range(len(left)))+max(sum(right[:j]) for j in range(1,len(right)+1))
        return max(work(left),work(right),cross)
    return work(payload['array'])
