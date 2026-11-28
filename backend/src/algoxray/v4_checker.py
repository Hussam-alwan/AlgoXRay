"""Reviewed, bounded semantic output policies. No executable checker plugins.

Version 1 supports a pair of distinct array indices summing to a target, or
an explicit no-solution token. All legal pairs are accepted. The owner must
review that the statement really permits precisely these outputs.
"""
import re

VERSION=1

def validate_checker(manifest, checker):
    keys={"kind","version","array","target","index_base","no_solution"}
    if type(checker) is not dict or set(checker)!=keys:
        raise ValueError("Invalid checker shape")
    if checker["kind"]!="two_sum_indices" or type(checker["version"]) is not int or checker["version"]!=VERSION:
        raise ValueError("Unsupported semantic checker")
    if "repeat" in manifest:
        raise ValueError("Semantic checker V1 requires a single body")
    if manifest["output"]!="tokens":
        raise ValueError("Semantic checker V1 requires tokens output")
    fields={f["name"]:f for f in manifest["fields"]}
    for key,kind in (("array","ints"),("target","int")):
        name=checker[key]
        if type(name) is not str or fields.get(name,{}).get("kind")!=kind:
            raise ValueError("Invalid checker field: "+key)
    if type(checker["index_base"]) is not int or checker["index_base"] not in (0,1):
        raise ValueError("Index base must be 0 or 1")
    marker=checker["no_solution"]
    if type(marker) is not str or not re.fullmatch(r"(?:[A-Z_]{1,24}|-1)",marker):
        raise ValueError("Unsupported no-solution token")
    return checker

def semantic_answer(manifest,checker,case,output):
    from .v4_contracts import validate_case
    validate_checker(manifest,checker)
    validate_case(manifest,case)
    if type(output) is not str or len(output.encode("utf-8"))>8192:
        return {"status":"unavailable","reason":"output_outside_checker_budget"}
    tokens=output.split()
    a,target=case[checker["array"]],case[checker["target"]]
    if tokens==[checker["no_solution"]]:
        seen=set()
        for x in a:
            if target-x in seen:
                return {"status":"rejected","reason":"solution_exists"}
            seen.add(x)
        return {"status":"accepted","reason":"no_pair_exists"}
    if len(tokens)!=2 or any(not re.fullmatch(r"[+-]?[0-9]{1,18}",x) for x in tokens):
        return {"status":"rejected","reason":"expected_two_indices_or_no_solution_token"}
    i,j=(int(x)-checker["index_base"] for x in tokens)
    if not 0<=i<len(a) or not 0<=j<len(a):
        return {"status":"rejected","reason":"index_out_of_bounds"}
    if i==j:return {"status":"rejected","reason":"indices_not_distinct"}
    if a[i]+a[j]!=target:
        return {"status":"rejected","reason":"sum_does_not_match_target"}
    return {"status":"accepted","reason":"valid_distinct_pair","indices":[i,j],
            "values":[a[i],a[j]],"target":target}

def judge_output(package,case,actual,expected):
    """Tri-state judgment. A checker failure must never become wrong_answer."""
    from .v4_contracts import equal, numeric_output
    checker=package.get("checker")
    if checker is None:
        if type(actual) is not str or type(expected) is not str:
            return {"status":"unavailable","authority":"reviewed_reference","reason":"missing_output"}
        if package["manifest"]["output"] == "float_tokens":
            try:
                numeric_output(package["manifest"], expected)
            except ValueError:
                return {"status": "unavailable", "authority": "reviewed_reference", "reason": "reference_or_control_invalid"}
        return {"status":"accepted" if equal(package["manifest"],actual,expected) else "rejected",
                "authority":"reviewed_reference","policy":package["manifest"]["output"]}
    base={"authority":"owner_reviewed_semantic_checker","policy":checker.get("kind") if type(checker) is dict else None,
          "version":VERSION,"reference_output_is_example":True}
    try:
        # Do not accuse the student if the reviewed oracle itself is unavailable
        # or violates the semantic contract.
        trusted=semantic_answer(package["manifest"],checker,case,expected)
        if trusted["status"]!="accepted":
            return {**base,"status":"unavailable","reason":"reference_or_control_invalid","reference_check":trusted}
        return {**base,**semantic_answer(package["manifest"],checker,case,actual)}
    except Exception:
        return {**base,"status":"unavailable","reason":"checker_failed"}
