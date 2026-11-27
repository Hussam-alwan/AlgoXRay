"""Synthetic public development smoke fixture; exposed development data, not a benchmark."""
import json
from pathlib import Path
from algoxray.v4_contracts import validate_package
from algoxray.v4_engine import review, analyze_package
from algoxray.v4_isolation import configured_image

manifest = {
    "id":"positive_triple_windows",
    "title":"Positive equal triple windows",
    "statement":"Read n (3 <= n <= 100) and n integers (0 <= a[i] <= 9). Count contiguous windows of three equal positive integers.",
    "fields":[{"name":"n","kind":"int","min":3,"max":100},
              {"name":"a","kind":"ints","min":0,"max":9,"length_from":"n"}],
    "lines":[["n"],["a"]],"output":"tokens"}
reference = "import sys\nn,*a=map(int,sys.stdin.buffer.read().split())\nprint(sum(a[i]==a[i+1]==a[i+2] and a[i]>0 for i in range(n-2)))\n"
student = reference.replace("range(n-2)", "range(n-3)")
package={"manifest":manifest,"reference":reference,"controls":[
    {"case":{"n":3,"a":[1,1,1]},"expected":"1"},
    {"case":{"n":4,"a":[0,2,2,2]},"expected":"1"}]}
case={"n":100,"a":[0]*97+[7,7,7]}
if __name__=="__main__":
    validate_package(package)
    reviewed=review(package)
    if not reviewed["passed"]:
        raise RuntimeError("Reference control review failed: "+str(reviewed))
    r=analyze_package(package,student,case=case,reduce_calls=1)
    evidence={"scope":"Development smoke; not independent evaluation or security proof.",
        "image_id":configured_image(),"review":reviewed,
        "status":r.get("status"),"attempts":r.get("attempts"),
        "executions":r.get("executions"),"reduction":r.get("reduction"),
        "elapsed_ms":r.get("elapsed_ms"),"original_case":r.get("original_case"),
        "original_witness":r.get("original_witness"),"witness":r.get("witness")}
    out=Path("docs/mvp-evidence/positive-triple-smoke.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({k:evidence[k] for k in ("status","attempts","executions","elapsed_ms")}))
    assert r["status"]=="observed_mismatch",r.get("scope")
    assert r["witness"]["case"]=={"n":3,"a":[7,7,7]}
    assert r["reduction"]["original_replay_count"]==r["reduction"]["reduced_replay_count"]==3
    assert r["witness"]["reference"]["stdout"].strip()=="1"
    assert r["witness"]["student"]["stdout"].strip()=="0"
    print("Verified original 100 -> reduced 3 in Docker, with 3 replays of each witness.")
