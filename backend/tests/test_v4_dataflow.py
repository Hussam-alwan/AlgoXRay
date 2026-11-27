from algoxray.v4_dataflow import relations
from algoxray.v4_provider import check_facts,check_hypotheses
def ev(i,line,locals):return {"event_id":"E"+str(i),"frame_id":"F1","kind":"line","line":line,"locals":locals}
def test_links():
    source="x=2\nx+=3\nif x>4:\n    print(x)\n"
    events=[ev(1,1,{}),ev(2,2,{"x":2}),ev(3,3,{"x":5}),ev(4,4,{"x":5})]
    r=relations(source,events)
    assert r["data"][0]["write"]=={"name":"x","value":5}
    assert r["control"][0]["target_line"]==4
    assert relations(source,[*events[:2],ev(3,3,{"x":7})])["data"]==[]
def test_facts_are_not_causal():
    events=[ev(1,1,{"x":4})]
    r={"hypotheses":[],"facts":[{"event_id":"E1","variable":"x","value":4},{"event_id":"E1","variable":"x","value":False}]}
    assert check_hypotheses(r,events)==[]
    assert [f["status"] for f in check_facts(r,events)]==["matches_recorded_snapshot","unsupported"]
