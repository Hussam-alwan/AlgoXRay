import copy
import pytest
from algoxray.v4_contracts import validate_manifest, validate_case, serialize, generate, smaller, complexity
from algoxray.v4_guidance import hypothesis_cases, case_schema
from algoxray.v4_package_audit import small_cases
from jsonschema import Draft202012Validator

M={"schema_version":2,"id":"repeated_sorted","title":"Repeat",
   "statement":"Read T; for each case read n and k followed by n sorted distinct integers.",
   "fields":[{"name":"n","kind":"int","min":1,"max":4},
             {"name":"k","kind":"int","min":1,"max":4},
             {"name":"a","kind":"ints","min":-3,"max":3,"length_from":"n","sorted":True,"unique":True}],
   "lines":[["n","k"],["a"]],"output":"tokens","repeat":{"min":1,"max":3},
   "relations":[{"left":"n","op":"ge","right":"k"}]}
C={"t":2,"cases":[{"n":3,"k":2,"a":[-3,0,2]},{"n":2,"k":1,"a":[0,1]}]}

def test_repeated_serialization_and_generation():
    validate_manifest(M)
    assert serialize(M,C)=="2\n3 2\n-3 0 2\n2 1\n0 1\n"
    for cases in (list(generate(M,7,30)),hypothesis_cases(M,7,30)):
        assert cases
        for c in cases:
            validate_case(M,c)
            Draft202012Validator(case_schema(M)).validate(c)
            assert serialize(M,c).startswith(str(c["t"])+"\n")
    assert list(generate(M,8,6))==list(generate(M,8,6))
    assert small_cases(M,32) is None

@pytest.mark.parametrize("change",["t","sorted","unique","relation"])
def test_illegal_cases(change):
    c=copy.deepcopy(C)
    if change=="t":c["t"]=1
    elif change=="sorted":c["cases"][0]["a"]=[2,0,-3]
    elif change=="unique":c["cases"][0]["a"]=[0,0,2]
    else:c["cases"][0]["k"]=4
    with pytest.raises(ValueError):serialize(M,c)

def test_repeat_shrink_legal_and_strict():
    xs=list(smaller(M,C))
    assert {"t":1,"cases":[C["cases"][1]]} in xs
    assert {"t":1,"cases":[C["cases"][0]]} in xs
    assert any(x["t"]==2 and x["cases"][0]["n"]<3 for x in xs)
    for x in xs:
        validate_case(M,x)
        assert complexity(M,x)<complexity(M,C)

def test_invalid_schema_and_feasibility():
    for change in ("version","unique","relation","repeat","unknown","output"):
        m=copy.deepcopy(M)
        if change=="version":m["schema_version"]=True
        elif change=="unique":m["fields"][2].update(min=0,max=1)
        elif change=="relation":m["relations"]=[{"left":"k","right":"n","op":"le"}]
        elif change=="repeat":m["repeat"]["max"]=17
        elif change=="output":m["output"]="unordered_tokens"
        else:m["unimplemented_constraint"]="sum of n"
        with pytest.raises(ValueError):validate_manifest(m)

def test_v2_flat_equality():
    m=copy.deepcopy(M);m.pop("repeat")
    m["relations"]=[{"left":"n","right":"k","op":"eq"}]
    validate_manifest(m)
    for c in generate(m,11,12):
        assert c["n"]==c["k"]
        validate_case(m,c)
