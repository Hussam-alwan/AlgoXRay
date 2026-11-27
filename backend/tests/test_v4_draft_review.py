import copy,hashlib
import pytest
from algoxray.v4_draft_review import review_draft,validate_provenance
from algoxray.v4_contracts import validate_package
M={"id":"n","title":"n","statement":"Read n, where 0 <= n <= 2. Print n.","fields":[{"name":"n","kind":"int","min":0,"max":2}],"lines":[["n"]],"output":"tokens"}
E=[{"field":"n","attribute":a,"quote":"0 <= n <= 2"} for a in ("min","max")]
def package():
    return {"manifest":copy.deepcopy(M),"reference":"ref","controls":[{"case":{"n":0},"expected":"0"},{"case":{"n":2},"expected":"2"}]}

def test_quotations_preserve_source_and_do_not_claim_semantics():
    r=review_draft(M["statement"],M,E,[])
    assert r["uncited_attributes"]==[] and r["provenance"]["unresolved"]==[]
    assert all(x["status"]=="literal_present_requires_semantic_review" for x in r["checks"])
    p=package();p["provenance"]=r["provenance"]
    assert validate_package(p)==p
    p["manifest"]["statement"]+=" changed"
    with pytest.raises(ValueError,match="hash"):validate_package(p)

def test_fabricated_quote_missing_attribute_and_unresolved_are_blocked():
    bad=[{**x,"quote":"n is between zero and two"} for x in E]
    r=review_draft(M["statement"],M,bad,[])
    assert len(r["uncited_attributes"])==2
    p=package();p["provenance"]=r["provenance"]
    with pytest.raises(ValueError):validate_package(p)
    p["provenance"]=review_draft(M["statement"],M,E,["Need human decision"])["provenance"]
    with pytest.raises(ValueError,match="Resolve draft"):validate_package(p)

def test_manual_packages_remain_compatible_and_extra_fields_rejected():
    assert validate_package(package())
    with pytest.raises(ValueError):review_draft(M["statement"],M,[{"field":"n","attribute":"exec","quote":"n"}],[])

def test_variable_length_quote_is_not_replaced_by_fixed_length():
    m={**M,"fields":[M["fields"][0],{"name":"a","kind":"ints","min":0,"max":2,"length_from":"n"}],"lines":[["n"],["a"]],"statement":"Read n with 0 <= n <= 2, then exactly n integers from 0 to 2."}
    r=review_draft(m["statement"],m,[{"field":"a","attribute":"length_from","quote":"exactly n integers"}],[])
    assert r["checks"][0]["declared_value"]=="n"
    assert not any(x=="a.length_from" for x in r["uncited_attributes"])
