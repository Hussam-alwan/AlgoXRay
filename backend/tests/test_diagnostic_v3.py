from copy import deepcopy
from types import SimpleNamespace
import pytest
from algoxray.engine import Options,analyze,validate_bundle
from algoxray.registry import local_submission
from algoxray.hints import build_hints
from algoxray.claim_verifier import abstain_on_unsupported
from algoxray.localization import rank_observations
from algoxray.explanation import explanation_cards

def run(tmp_path,source,case,problem="max_subarray_v1"):
    path=tmp_path/"solution.py";path.write_text(source,encoding="utf-8")
    return analyze(local_submission(problem,path),Options(shrink=False),case=case,persist=False)

@pytest.mark.parametrize("source,case",[
("def solve(p):\n    return max(p['array'])\n",{"array":[2,3]}),
("def solve(p):\n    a=p['array']\n    return max(sum(a[:j]) for j in range(1,len(a)+1))\n",{"array":[-3,2]})])
def test_restricted_candidate_observation(tmp_path,source,case):
    b=run(tmp_path,source,case)
    assert b["claims"][-1]["adapter_id"]=="subarray_restricted_candidates_v3"
    assert b["diagnosis"]["status"]=="supported"
    validate_bundle(b)

def test_constant_attainable_wrong_answer_abstains(tmp_path):
    b=run(tmp_path,"def solve(p):\n    return 2\n",{"array":[2,3]})
    assert b["diagnosis"]["status"]=="witness_only"

def test_shadowed_builtin_abstains(tmp_path):
    b=run(tmp_path,"def max(a):\n    return 2\n\ndef solve(p):\n    return max(p['array'])\n",{"array":[2,3]})
    assert b["diagnosis"]["status"]=="witness_only"

def test_old_v2_observation_reconstruction(tmp_path):
    b=run(tmp_path,"def solve(p):\n    return max(p['array'])\n",{"array":[2,3]})
    old=deepcopy(b);old["evidence_revision"]="option-b.2"
    old["claims"],old["hints"]=build_hints(old,SimpleNamespace(source=old["submission"]["source"],origin=old["submission"]["origin"],adapter=None))
    abstain_on_unsupported(old)
    old["evidence_level"]="E2";old["diagnostic_status"]="abstained"
    old["ranked_observations"]=rank_observations(old)
    old["explanation_cards"]=explanation_cards(old)
    assert len(old["claims"])==1
    validate_bundle(old)
