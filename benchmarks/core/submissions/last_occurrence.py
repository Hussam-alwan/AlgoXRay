def solve(payload):
    positions = {value: index for index, value in enumerate(payload["array"])}
    return positions.get(payload["target"], -1)
