from algoxray.spectrum import rank_spectrum
from algoxray.engine import analyze, Options, validate_bundle
from algoxray.registry import get_submission
import pytest
from copy import deepcopy

def test_spectrum_needs_both_outcomes():
    assert not rank_spectrum([{"outcome":"fail","lines":[1]}],[{"line":1,"kind":"line","event_id":"E1"}])

def test_spectrum_prioritizes_failure_only_line():
    samples=[{"outcome":"fail","lines":[1,2]},{"outcome":"pass","lines":[1]}]
    events=[{"line":i,"kind":"line","event_id":str(i)} for i in (1,2)]
    rows=rank_spectrum(samples,events)
    assert [r["line"] for r in rows]==[2,1] and not rows[0]["causal_fault_proven"]

def test_new_observation_and_sample_links():
    b=analyze(get_submission("max_subarray_empty_bug"),Options(shrink=False,diagnostic_samples=2),case={"array":[-5,-2]},persist=False)
    assert b["diagnosis"]["status"]=="supported"
    assert b["claims"][-1]["adapter_id"]=="max_subarray_zero_negative_v1"
    assert b["diagnostic_samples"]
    changed=deepcopy(b); changed["diagnostic_samples"][0]["lines"]=[]
    with pytest.raises(ValueError,match="coverage mismatch"): validate_bundle(changed)
