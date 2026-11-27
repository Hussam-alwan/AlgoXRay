import copy
from algoxray.v4_diagnostic_context import diagnostic_context,check_branches,sha
from algoxray.v4_contracts import digest
M={"id":"n","title":"n","statement":"Print n.","fields":[{"name":"n","kind":"int","min":0,"max":2}],"lines":[["n"]],"output":"tokens"}
P={"manifest":M,"reference":"ref","controls":[{"case":{"n":0},"expected":"0"},{"case":{"n":2},"expected":"2"}]}
E=[{"event_id":"E1","frame_id":"F1","line":2,"kind":"line","locals":{"n":1,"a":[1,2]}}]
W={"stdin":"1\n","student":{"stdout":"0\n","events":E,"trace_status":"complete"},"reference":{"stdout":"1\n"}}
def test_context_has_immutable_identity_full_contract_and_only_supplied_scalar_facts():
    source="n=1\nif n<2:\n    print(0)\n"
    data=diagnostic_context(P,source,W)
    assert data["identity"]=={"package_sha256":digest(P),"source_sha256":sha(source),"input_sha256":sha(W["stdin"])}
    assert data["manifest"]["fields"]==M["fields"] and data["statement_complete"]
    assert data["events"][0]["locals"]=={"n":1}

def test_large_context_is_explicitly_excerpted_and_bounded():
    p=copy.deepcopy(P);p["manifest"]["statement"]="s"*8000
    source="# untrusted comment\n"*1500
    w=copy.deepcopy(W);w["stdin"]="1"*10000
    data=diagnostic_context(p,source,w)
    assert data["context_bytes"]<=12000 and not data["statement_complete"] and not data["input_complete"]
    assert not data["source_complete"] and data["identity"]["source_sha256"]==sha(source)

def test_conditions_are_recomputed_and_contradictions_rejected():
    src="n=1\nif n<2:\n    print(n)\n"
    good=check_branches({"branches":[{"event_id":"E1","line":2,"condition":True}]},src,E)[0]
    assert good["status"]=="matches_recorded_condition" and good["frame_id"]=="F1" and not good["causal_verified"]
    bad=check_branches({"branches":[{"event_id":"E1","line":2,"condition":False}]},src,E)[0]
    assert bad["status"]=="contradicted"
    assert check_branches({"branches":[{"event_id":"fake","line":2,"condition":True}]},src,E)[0]["status"]=="unsupported"

def test_calls_and_source_injection_cannot_be_evaluated_on_host():
    src="n=1\nif __import__('os').system('bad'):\n    pass\n"
    assert check_branches({"branches":[{"event_id":"E1","line":2,"condition":True}]},src,E)[0]["status"]=="unsupported"
