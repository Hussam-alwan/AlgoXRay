def solve(payload):
    a=payload['array']
    return 0 if a and a[0]==payload['target'] else -1
