from algoxray.v4_dataflow import relations
from algoxray.v4_compare import rank
def ev(i,line,loc):return {"event_id":str(i),"frame_id":"F1","kind":"line","line":line,"locals":loc}
def test_index_and_def_use():
    src="x=a[i]\ny=x+1\nprint(y)"
    events=[ev(1,1,{"a":[1,4],"i":1}),ev(2,2,{"a":[1,4],"i":1,"x":4}),ev(3,3,{"a":[1,4],"i":1,"x":4,"y":5})]
    r=relations(src,events)
    assert r["data"][0]["reads"]["a[1]"]==4
    assert r["def_use"][0]["name"]=="x"
def test_coverage_requires_complete_trace():
    f={"trace_status":"complete","events":[ev(1,1,{}),ev(2,2,{})]}
    p={"trace_status":"complete","events":[ev(1,1,{})]}
    r=rank(f,[p])
    assert r["ranked"][0]["line"]==2
    assert rank({**f,"trace_status":"truncated"},[p])["status"]=="insufficient_complete_traces"
