from algoxray.engine import Options,analyze
from algoxray.registry import local_submission
from algoxray.invariants import graph_violation,attainable_sum

def run(tmp_path,problem,source,case):
    p=tmp_path/"solver.py"
    p.write_text(source,encoding="utf-8")
    return analyze(local_submission(problem,p),Options(shrink=False),case=case,persist=False)

def test_graph_specific_invariant_without_known_names(tmp_path):
    result=run(tmp_path,"dijkstra_v1","def solve(data):\n    return [0, 1, None]\n",{"n":3,"source":0,"edges":[[0,1,1],[1,2,3]]})
    assert result["status"]=="witness_found"
    assert result["claims"][-1]["adapter_id"]=="graph_relaxation_invariant_v1"
    assert result["diagnosis"]["source_lines"]==[2]

def test_invariant_not_overclaimed_for_feasible_but_too_small_distances(tmp_path):
    result=run(tmp_path,"dijkstra_v1","def solve(data):\n    return [0, 0]\n",{"n":2,"source":0,"edges":[[0,1,2]]})
    assert result["diagnostic_status"]=="abstained"

def test_subarray_unattainable_sum(tmp_path):
    result=run(tmp_path,"max_subarray_v1","def solve(data):\n    return 4\n",{"array":[2,-10,2]})
    assert result["claims"][-1]["adapter_id"]=="subarray_attainability_invariant_v1"
    assert not attainable_sum(result["case"],4)
