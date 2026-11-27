import json,subprocess,sys
from algoxray.v4_isolation import GUEST
from algoxray.v4_branches import observed_branches
from algoxray.v4_compare import rank
from algoxray.v4_diagnostic_context import diagnose_execution,diagnostic_context
from algoxray.v4_graph import observed_graph
from algoxray.v4_cfg import output_chain
from algoxray.v4_localization import localize
from algoxray.v4_provider import MockProvider,ProviderError

SOURCE="n=int(input())\nif n>0:\n    out=1\nelse:\n    out=0\nprint(out)\n"
P={"manifest":{"id":"sign","title":"Sign","statement":"Print 1 if n is positive, otherwise 0.","fields":[{"name":"n","kind":"int","min":-4,"max":4}],"lines":[["n"]],"output":"tokens"},"reference":"ref","controls":[{"case":{"n":-1},"expected":"0"},{"case":{"n":1},"expected":"1"}]}
def guest(source,stdin):
    req={"source":source,"stdin":stdin,"seconds":1,"trace_limit":256}
    return json.loads(subprocess.check_output([sys.executable,"-I","-c",GUEST],input=(json.dumps(req)+"\n").encode(),timeout=5))
def test_branch_spectrum_observed_and_partial():
    fail=guest(SOURCE,"1\n");good=guest(SOURCE,"-1\n");extra=guest(SOURCE,"2\n")
    true=observed_branches(SOURCE,fail)["observed"]
    false=observed_branches(SOURCE,good)["observed"]
    assert any(r["line"]==2 and r["target_line"]==3 and r["kind"]=="condition_true" for r in true)
    assert any(r["line"]==2 and r["target_line"]==5 and r["kind"]=="condition_false" for r in false)
    r=rank(fail,[good,{**good,"trace_status":"truncated"}],source=SOURCE,additional_failing=[extra])
    assert r["failing_count"]==2 and r["passing_count"]==1
    assert r["branches"]["ranked"][0]["ochiai"]==1
    assert r["branches"]["ranked"][0]["witness_event_pairs"]
    assert rank({**fail,"trace_status":"truncated"},[good],source=SOURCE)["ranked"]==[]
    assert not observed_branches(SOURCE,{**fail,"trace_status":"truncated"})["complete_spectrum_eligible"]
def test_ambiguous_same_line_not_claimed():
    source="n=1\nif n: x=2; y=3\nprint(n)\n"
    r=observed_branches(source,guest(source,""))
    assert not r["observed"]
def test_ai_static_and_missing_condition_are_not_observed_claims():
    fail=guest(SOURCE,"1\n")
    witness={"stdin":"1\n","student":fail,"reference":{"stdout":"0\n"},"kind":"wrong_answer"}
    event=next(e for e in fail["events"] if e["kind"]=="line" and e["line"]==2)
    proposal={"hypotheses":[{"text":"Inspect an unexecuted alternative","event_ids":[event["event_id"]],"line":5,"basis":"static"},
                            {"text":"Consider missing guard","event_ids":[event["event_id"]],"line":2,"basis":"missing_condition"},
                            {"text":"Fake anchor","event_ids":["E999"],"line":3}],
              "facts":[{"event_id":event["event_id"],"variable":"n","value":999}]}
    graph=observed_graph(fail["events"],SOURCE)
    graph["output_chain"]=output_chain(SOURCE,fail,graph)
    ranking=rank(fail,[guest(SOURCE,"-1\n")],source=SOURCE)
    loc=localize(SOURCE,witness,graph,ranking)
    branches=observed_branches(SOURCE,fail)
    context=diagnostic_context(P,SOURCE,witness,ranking,localization=loc,branches=branches)
    assert context["context_version"]==2 and context["context_bytes"]<=12000
    ids={e["event_id"] for e in context["events"]}
    assert context["location_candidates"]
    assert all(set(r["event_ids"])<=ids for r in context["location_candidates"])
    assert all(set(pair)<=ids for r in context["observed_branches"] for pair in r["event_pairs"])
    r=diagnose_execution(P,SOURCE,witness,MockProvider(proposal),ranking,localization=loc,branches=branches)
    assert r["ai_status"]=="ok"
    assert [h["status"] for h in r["hypotheses"]]==["hypothesis","hypothesis","unsupported"]
    assert not r["hypotheses"][0]["line_observed_in_supplied_anchors"]
    assert all(not h["causal_verified"] and not h["text_semantically_verified"] for h in r["hypotheses"])
    assert r["ai_conflicting_claims"]==1 and all(h["conflicting_claims"] for h in r["hypotheses"])
    assert r["ai_facts"][0]["status"]=="contradicted"
def test_provider_outage_does_not_create_facts():
    fail=guest(SOURCE,"1\n")
    w={"stdin":"1\n","student":fail,"reference":{"stdout":"0\n"}}
    class Broken:
        def propose(self,*args):raise ProviderError("fixture_unavailable")
    r=diagnose_execution(P,SOURCE,w,Broken())
    assert r["ai_status"]=="unavailable_or_invalid" and not r["hypotheses"] and not r["ai_facts"]
