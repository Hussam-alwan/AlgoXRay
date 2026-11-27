import copy
from algoxray.v4_package_audit import small_cases,audit_package
M={"id":"n","title":"n","statement":"Double n","fields":[{"name":"n","kind":"int","min":0,"max":2}],"lines":[["n"]],"output":"tokens"}
P={"manifest":M,"reference":"double","reference_alt":"shift","controls":[{"case":{"n":0},"expected":"0"},{"case":{"n":2},"expected":"4"}]}
def run(src,text,trace_limit):
    return {"status":"ok","stdout":str(2*int(text)),"events":[]}

def test_finite_domain_agreement_and_hashes():
    r=audit_package(P,run=run)
    assert r["status"]=="finite_domain_agreement" and r["enumeration_complete"]
    assert len(r["checks"])==3 and r["reference_sha256"]!=r["alternative_sha256"]

def test_hidden_reference_disagreement_is_not_accepted():
    def disagree(src,text,trace_limit):
        n=int(text);return {"status":"ok","stdout":str(9 if src=="shift" and n==1 else 2*n),"events":[]}
    r=audit_package(P,run=disagree)
    assert r["status"]=="reference_disagreement_or_failure" and not r["enumeration_complete"]

def test_primary_reference_is_not_its_own_independent_check():
    p={k:v for k,v in P.items() if k!="reference_alt"}
    r=audit_package(p,run=run)
    assert r["status"]=="controls_only_no_second_reference" and not r["enumeration_complete"]

def test_large_domains_do_not_allocate_or_enumerate():
    m=copy.deepcopy(M);m["fields"][0].update(min=1,max=10**15)
    assert small_cases(m,16) is None

def test_dependent_lists_and_zero_length_are_enumerated():
    m={**M,"fields":[{"name":"n","kind":"int","min":0,"max":2},{"name":"a","kind":"ints","min":0,"max":1,"length_from":"n"}],"lines":[["n"],["a"]]}
    cases=small_cases(m,16)
    assert len(cases)==7 and {"n":0,"a":[]} in cases
