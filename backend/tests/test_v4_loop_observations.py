from algoxray.v4_loop_observations import loop_observations

def event(i,line,frame="F1",kind="line"):
    return {"event_id":"E"+str(i),"frame_id":frame,"line":line,"kind":kind,"locals":{}}
def test_loop_header_and_body_counts_differ():
    src="for i in range(2):\n    print(i)\nprint('done')\n"
    trace={"trace_status":"complete","events":[event(1,1),event(2,2),event(3,1),event(4,2),event(5,1),event(6,3)]}
    row=loop_observations(src,trace)["loops"][0]
    assert row["header_visits"]==3 and row["observed_body_entries"]==2
    assert row["body_event_ids"]==["E2","E4"]

def test_recursive_frames_are_not_merged():
    src="def f(n):\n    while n>0:\n        n-=1\n"
    trace={"trace_status":"complete","events":[event(1,2),event(2,3),event(3,2,"F2"),event(4,3,"F2"),event(5,2)]}
    rows=loop_observations(src,trace)["loops"]
    assert len(rows)==2 and all(x["observed_body_entries"]==1 for x in rows)

def test_truncation_is_not_presented_as_total_iterations():
    src="while True:\n    pass\n"
    row=loop_observations(src,{"trace_status":"truncated","events":[event(1,1),event(2,2)]})["loops"][0]
    assert row["status"]=="observed_partial_trace" and row["observed_body_entries"]==1

def test_multiline_or_single_line_body_and_invalid_source_are_explicit():
    for src in ["for i in (\n range(2)\n):\n    pass\n","while True: pass\n"]:
        assert loop_observations(src,{"events":[]})["loops"][0]["status"]=="unsupported_header_mapping"
    assert loop_observations("if !!!",{})["status"]=="unavailable"
