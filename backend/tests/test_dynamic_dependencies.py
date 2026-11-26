from algoxray.dependencies import dynamic_dependencies

def event(i,line,values,frame="F1",kind="line"):
    return {"event_id":str(i),"kind":kind,"line":line,"frame_id":frame,"locals":values}

def test_exact_arithmetic_link():
    source="def solve(x):\n    y = x + 2\n    return y\n"
    events=[event(1,2,{"x":3}),event(2,3,{"x":3,"y":5})]
    link=dynamic_dependencies(source,events)[0]
    assert link["reads"]=={"x":3} and link["write"]=={"name":"y","value":5}
    assert not link["causal_fault_proven"]

def test_mismatch_or_different_frame_abstains():
    source="def solve(x):\n    y = x + 2\n    return y\n"
    before=event(1,2,{"x":3})
    assert not dynamic_dependencies(source,[before,event(2,3,{"y":8})])
    assert not dynamic_dependencies(source,[before,event(2,3,{"y":5},"F2")])

def test_call_and_multi_statement_unsupported():
    events=[event(1,2,{"x":3}),event(2,3,{"x":3,"y":5})]
    assert not dynamic_dependencies("def solve(x):\n    y = helper(x)\n    return y\n",events)
    assert not dynamic_dependencies("def solve(x):\n    y=x+2; z=0\n    return y\n",events)
