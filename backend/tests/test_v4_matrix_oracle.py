import pytest
from algoxray.v4_contracts import *
from algoxray.v4_engine import analyze_package,review
M={"id":"matrix","title":"Matrix sum","statement":"Read r c and r rows of c ints, print sum.","fields":[{"name":"r","kind":"int","min":1,"max":4},{"name":"c","kind":"int","min":1,"max":4},{"name":"a","kind":"matrix","min":-3,"max":4,"rows_from":"r","cols_from":"c"}],"lines":[["r","c"],["a"]],"output":"tokens"}
CASE={"r":2,"c":2,"a":[[1,2],[3,4]]}
def test_matrix():
    validate_manifest(M)
    assert serialize(M,CASE)=="2 2\n1 2\n3 4\n"
    with pytest.raises(ValueError):serialize(M,{**CASE,"a":[[1],[2]]})
    for c in generate(M,42,25):
        serialize(M,c)
        assert all(complexity(M,d)<complexity(M,c) for d in smaller(M,c))
def test_matrix_reference_disagreement():
    p={"manifest":M,"reference":"ref","reference_alt":"alt","controls":[{"case":CASE,"expected":"10"},{"case":{"r":1,"c":1,"a":[[1]]},"expected":"1"}]}
    def run(src,stdin,trace_limit):
        return {"status":"ok","stdout":str(sum(map(int,stdin.split()[2:])) if src=="ref" else 0),"events":[]}
    assert not review(p,run=run)["passed"]
    assert analyze_package(p,"student",case=CASE,run=run)["status"]=="oracle_unavailable"
