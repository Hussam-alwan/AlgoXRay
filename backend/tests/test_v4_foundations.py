import pytest
from algoxray.v4_isolation import docker_command,IMAGE,execute_stdio
from algoxray.v4_graph import observed_graph
from algoxray.v4_provider import MockProvider,ProviderError,check_hypotheses

def test_docker_policy():
    c=docker_command("test",IMAGE)
    for flag in ["--network","--read-only","--cap-drop","--security-opt","--memory","--pids-limit","--pull=never","--log-driver"]:
        assert flag in c
    assert not any(x in c for x in ["-v","--volume","--mount","--privileged"])
    with pytest.raises(ValueError): docker_command("test","latest")

def test_bad_budget():
    with pytest.raises(ValueError): execute_stdio("print(1)","",seconds=10)
    with pytest.raises(ValueError): execute_stdio("print(1)","",trace_limit=300)

def test_graph_and_anchors():
    events=[{"event_id":"E1","frame_id":"F1","line":1,"kind":"line","locals":{"x":1}},
            {"event_id":"E2","frame_id":"F1","line":2,"kind":"line","locals":{"x":2}},
            {"event_id":"E3","frame_id":"F1","line":1,"kind":"line","locals":{"x":3}},
            {"event_id":"E4","frame_id":"F1","line":2,"kind":"line","locals":{"x":4}}]
    graph=observed_graph(events)
    assert len(graph["nodes"])==2 and graph["edges"][0]["count"]==2
    assert graph["changes"][0]["before_event_id"]=="E1"
    assert not graph["causal_fault_proven"]
    h={"hypotheses":[{"text":"Possible cause","event_ids":["E2"],"line":2}]}
    assert check_hypotheses(MockProvider(h).propose("diagnosis",{},{}),events)[0]["status"]=="hypothesis"
    h["hypotheses"][0]["event_ids"]=["invented"]
    assert check_hypotheses(h,events)[0]["status"]=="unsupported"
    with pytest.raises(ProviderError): check_hypotheses({"verified":True},events)
