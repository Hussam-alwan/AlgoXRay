"""Review bounded test manifests against an installed, trusted ProblemSpec.

Passing checks are evidence about the supplied cases, never automatic approval of a new contract.
"""
import json
import random
from itertools import islice
from hashlib import sha256
from .problem_registry import spec_for

def review_package(problem_id, controls, seed=2026, sample_count=12):
    spec=spec_for(problem_id)
    if type(controls) is not list or not 1<=len(controls)<=20:
        raise ValueError("Supply 1–20 independent control cases")
    if type(sample_count) is not int or not 1<=sample_count<=40 or type(seed) is not int or not 0<=seed<=2**32-1:
        raise ValueError("Invalid review budget or seed")
    encoded=json.dumps(controls,sort_keys=True,allow_nan=False,separators=(",",":")).encode()
    failures=[]
    checks={"controls":0,"generated":0,"reductions":0}
    details=[]
    def check_case(case,expected,where,control=False):
        try:
            legal=spec.validate(case)
            ref=spec.reference(legal)
            if spec.check(legal,ref,ref) is not None:
                failures.append({"check":where,"error":"Reference rejected by its checker"})
            if control and spec.check(legal,expected,ref) is not None:
                failures.append({"check":where,"error":"Supplied control answer disagrees with contract"})
            checks["controls" if control else "generated"]+=1
            for reduced in islice(spec.smaller(legal),64):
                checks["reductions"]+=1
                reduced=spec.validate(reduced)
                if spec.complexity(reduced)>=spec.complexity(legal):
                    failures.append({"check":where,"error":"Reducer did not strictly decrease complexity"})
                answer=spec.reference(reduced)
                if spec.check(reduced,answer,answer) is not None:
                    failures.append({"check":where,"error":"Reduced case reference rejected"})
            if control: details.append({"case":legal,"supplied":expected,"reference":ref})
        except Exception as exc:
            failures.append({"check":where,"error":f"{type(exc).__name__}: {exc}"})
    for i,item in enumerate(controls):
        if type(item) is not dict or set(item)!={"case","expected"}:
            failures.append({"check":f"control:{i}","error":"Expected case and expected fields"})
        else: check_case(item["case"],item["expected"],f"control:{i}",True)
    rng=random.Random(seed)
    for i in range(sample_count):
        try: case=spec.random_case(rng)
        except Exception as exc:
            failures.append({"check":f"generator:{i}","error":f"{type(exc).__name__}: {exc}"})
            continue
        check_case(case,None,f"generator:{i}")
    return {"status":"checks_failed" if failures else "checks_passed",
            "approval":"requires_human_review","problem_id":problem_id,"oracle_id":spec.oracle_id,
            "control_manifest_sha256":sha256(encoded).hexdigest(),"seed":seed,"checks":checks,
            "control_results":details,"failures":failures[:100],"failure_count":len(failures),
            "limits":"Registered trusted package only; random generator sampled; reducer legality/complexity sampled; not a proof or automatic registration."}
