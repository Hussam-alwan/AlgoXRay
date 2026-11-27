from algoxray.v4_cfg import static_cfg,output_chain
from algoxray.v4_graph import observed_graph
def test_static_cfg_is_separate():
    g=static_cfg("x=1\nwhile x<3:\n    x+=1\nprint(x)")
    assert {"from":"module:2","to":"module:3","kind":"loop_body"} in g["edges"]
    assert {"from":"module:2","to":"module:4","kind":"loop_exit"} in g["edges"]
    assert static_cfg("while True:\n    break")["unsupported"]
def test_partial_output_chain():
    source="x=a+1\ny=x+2\nprint(y)"
    events=[{"event_id":"E"+str(i),"frame_id":"F1","line":i,"kind":"line","locals":v} for i,v in [(1,{"a":1}),(2,{"a":1,"x":2}),(3,{"a":1,"x":2,"y":4})]]
    g=observed_graph(events,source);r=output_chain(source,{"events":events,"stdout":"4\n"},g)
    assert r["status"]=="snapshot_compatible_with_stdout" and len(r["links"])==2 and not r["causal_verified"]
    assert output_chain(source,{"events":events,"stdout":"5\n"},g)["status"]=="unsupported"
