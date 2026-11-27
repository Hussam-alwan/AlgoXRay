import copy,math
import pytest
from algoxray.v4_contracts import validate_manifest,serialize,equal,generate
M={"id":"n","title":"n","statement":"test","fields":[{"name":"n","kind":"int","min":0,"max":2},{"name":"a","kind":"ints","min":-1,"max":1,"length_from":"n"}],"lines":[["n"],["a"]],"output":"tokens"}

def test_empty_list_contract_and_original_token_policy():
    validate_manifest(M)
    assert serialize(M,{"n":0,"a":[]})=="0\n\n"
    assert list(generate(M,2,5))[0]=={"n":0,"a":[]}
    assert equal(M,"1 2","1\n2") and not equal(M,"1 2","2 1")

def test_unordered_policy_preserves_multiplicity():
    m={**M,"output":"unordered_tokens"};validate_manifest(m)
    assert equal(m,"2 1 2","2\n2 1")
    assert not equal(m,"1 2 2","1 1 2")
    assert not equal(m,"1 2","1 2 2")

def test_finite_explicit_numeric_tolerance():
    m={**M,"output":"float_tokens","tolerance":{"abs":.000001,"rel":.000001}}
    validate_manifest(m)
    assert equal(m,"0.33333333 1000000.5","0.333333 1000000")
    assert not equal(m,"0.4","0.333333")
    assert not equal(m,"1 2","1")
    for value in ["NaN","Infinity","1e999","1,2","x"]:
        assert not equal(m,value,value)

def test_numeric_tolerance_is_not_silently_enabled():
    with pytest.raises(ValueError):validate_manifest({**M,"output":"float_tokens"})
    with pytest.raises(ValueError):validate_manifest({**M,"tolerance":{"abs":0,"rel":0}})
    for value in [True,float("nan"),float("inf"),.5,-1]:
        with pytest.raises(ValueError):validate_manifest({**M,"output":"float_tokens","tolerance":{"abs":value,"rel":0}})
    m={**M,"output":"float_tokens","tolerance":{"abs":0,"rel":0}}
    a="1234567890123456789012345678901234567890"
    assert not equal(m,a,str(int(a)+1))
