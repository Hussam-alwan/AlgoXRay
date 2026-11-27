from algoxray.v4_guidance import hypothesis_cases,suggestions,classify_probe
from algoxray.v4_provider import MockProvider
from algoxray.v4_engine import analyze_package
from algoxray.v4_contracts import serialize
M={"id":"twice","title":"Twice","statement":"Print 2*n","fields":[{"name":"n","kind":"int","min":1,"max":9}],"lines":[["n"]],"output":"tokens"}
P={"manifest":M,"reference":"ref","controls":[{"case":{"n":1},"expected":"2"},{"case":{"n":9},"expected":"18"}]}
def test_hypothesis_cases():
    a=hypothesis_cases(M,7,8)
    assert a==hypothesis_cases(M,7,8) and a
    for c in a:serialize(M,c)
def test_suggestions_reject_invalid():
    p={"case":{"n":3},"prediction":"mismatch","hypothesis_index":-1}
    q={**p,"case":{"n":20}}
    good,rejected=suggestions(MockProvider({"proposals":[p,p,q]}),M,"code")
    assert good==[p] and rejected==2
    assert classify_probe(p,{"kind":"match"})["status"]=="prediction_contradicted"
def test_guidance_finds_missed_case():
    class Provider:
        model="mock"
        def propose(self,task,data,schema):
            if task=="case_suggestions":return {"proposals":[{"case":{"n":3},"prediction":"mismatch","hypothesis_index":-1}]}
            return {"hypotheses":[],"facts":[]}
    def run(src,stdin,trace_limit):
        n=int(stdin)
        return {"status":"ok","stdout":str(2*n if src=="ref" or n!=3 else n),"events":[]}
    r=analyze_package(P,"bad",count=2,reduce_calls=0,provider=Provider(),guided=True,run=run)
    assert r["status"]=="observed_mismatch" and r["witness"]["case"]=={"n":3}
    assert r["guidance"]["probes"][0]["status"]=="prediction_supported"
    assert not r["guidance"]["probes"][0]["causal_verified"]
