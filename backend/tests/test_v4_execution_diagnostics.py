import copy
from algoxray.v4_execution_diagnostics import execution_diagnostics

SOURCE="l=1\nr=2\nwhile l < r:\n    mid=(l+r)//2\n    l=mid\n"
def stalled(status="timeout"):
    lines=[3,4,5]*4+[3]
    return {"status":status,"trace_status":"truncated","events":[
        {"event_id":"E"+str(i+1),"frame_id":"F1","line":line,"kind":"line","locals":{"l":1,"r":2,"mid":1}} for i,line in enumerate(lines)],
        "profile":{"status":"partial","blocks":[{"line":3,"end_line":5,"kind":"while","hits":14000}]}}

def test_timeout_guard_and_unchanged_assignment_have_real_source_event_anchors():
    report=execution_diagnostics(SOURCE,stalled())
    f=report["findings"][0]
    assert f["line"]==3 and f["condition_values"]=={"l":1,"r":2}
    assert f["observed_repeated_headers"]==5 and f["causal_verified"] is False
    a=f["assignments"][0]
    assert a["line"]==5 and a["before"]==a["after"]==1 and a["reads"]=={"mid":1}
    ids={e["event_id"] for e in stalled()["events"]}
    assert set(f["event_ids"])<=ids and a["before_event_id"] in ids and a["after_event_id"] in ids
    assert report["timed_loops"][0]["hits"]==14000

def test_successful_repetition_is_not_a_timeout_finding():
    assert execution_diagnostics(SOURCE,stalled("ok"))["findings"]==[]

def test_changing_condition_values_are_not_reported_as_stalled():
    run=stalled()
    for i,event in enumerate(run["events"]):event["locals"]["l"]=-100+i
    assert execution_diagnostics(SOURCE,run)["findings"]==[]

def test_condition_call_is_never_executed_and_no_unsupported_guard_claim():
    source="while dangerous():\n    l=1\n"
    run=stalled()
    for e in run["events"]:e["line"]=1;e["locals"]["dangerous"]=1
    assert execution_diagnostics(source,run)["findings"]==[]

def test_boolean_and_integer_values_are_not_mistaken_for_identical_snapshots():
    run=stalled()
    for i,e in enumerate(run["events"]):e["locals"]["l"]=True if i%2 else 1
    assert execution_diagnostics(SOURCE,run)["findings"]==[]

def test_constant_condition_missing_trace_and_syntax_errors_do_not_invent_values():
    run=stalled()
    assert execution_diagnostics("while True:\n    pass\n",run)["findings"]==[]
    run["events"]=[]
    assert execution_diagnostics(SOURCE,run)["findings"]==[]
    assert execution_diagnostics("while !!!",run)["findings"]==[]

def test_unsupported_update_calls_are_not_evaluated():
    source=SOURCE.replace("l=mid","l=unknown()")
    report=execution_diagnostics(source,stalled())
    assert report["findings"] and report["findings"][0]["assignments"]==[]

def test_frames_are_not_merged_to_create_fake_repetition():
    run=stalled();run["events"]=run["events"][:6]
    for i,e in enumerate(run["events"]):e["frame_id"]="F"+str(i)
    assert execution_diagnostics(SOURCE,run)["findings"]==[]
