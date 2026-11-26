"""External-source pilot; reuse frozen V3 evaluation without changing its engine."""
import argparse
import hashlib
import importlib.util
from itertools import combinations_with_replacement, product
import json
from pathlib import Path
import platform
import random
import runpy
import subprocess
import sys
from importlib.metadata import version

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V2="09e3920656c8081aaa1fde5ccdfe30430c571e0f"
sys.path.insert(0,str(ROOT/"backend/src"))
from algoxray.problem_registry import spec_for
loader=importlib.util.spec_from_file_location("v2_evaluation",ROOT/"benchmarks/option_b/evaluate.py")
v2=importlib.util.module_from_spec(loader)
loader.loader.exec_module(v2)

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")

def inventory():
    rows=[]
    for r in load(HERE/"manifest.json"):
        p=HERE/r["file"]
        raw=HERE/r["upstream_archive"]
        rows.append({**r,"file":p.relative_to(ROOT).as_posix(),"sha256":digest(p),"upstream_sha256":digest(raw)})
    if len({r["sha256"] for r in rows})!=len(rows): raise ValueError("Duplicate source")
    return rows

def truth(problem,c):
    if problem=="binary_search_v1":
        return [i for i,v in enumerate(c["array"]) if v==c["target"]]
    if problem=="max_subarray_v1":
        a=c["array"]
        return max(sum(a[i:j]) for i in range(len(a)) for j in range(i+1,len(a)+1))
    best=[None]*c["n"]
    stack=[(c["source"],0,{c["source"]})]
    while stack:
        u,d,seen=stack.pop()
        if best[u] is None or d<best[u]: best[u]=d
        for a,b,w in c["edges"]:
            if a==u and b not in seen: stack.append((b,d+w,seen|{b}))
    return best

def agrees(problem,c,value):
    expected=truth(problem,c)
    if problem=="binary_search_v1":
        return type(value) is int and value in (expected or [-1])
    if problem=="max_subarray_v1":
        return type(value) is int and value==expected
    return type(value) is list and all(x is None or type(x) is int for x in value) and value==expected

def cases(problem):
    if problem=="binary_search_v1":
        for n in range(5):
            for a in combinations_with_replacement(range(-2,3),n):
                for target in range(-3,4): yield {"array":list(a),"target":target}
    elif problem=="max_subarray_v1":
        for n in range(1,5):
            for a in product(range(-2,3),repeat=n): yield {"array":list(a)}
    else:
        for n in (2,3):
            pairs=[(a,b) for a in range(n) for b in range(n) if a!=b]
            for mask in range(1<<len(pairs)):
                edges=[[a,b,1+(i%3)] for i,(a,b) in enumerate(pairs) if mask&(1<<i)]
                for s in range(n): yield {"n":n,"source":s,"edges":edges}
    rng=random.Random(8093)
    for _ in range(150): yield spec_for(problem).random_case(rng)

def preflight():
    records=[]
    for r in inventory():
        solver=runpy.run_path(str(ROOT/r["file"]))["solve"]
        checks=0;bad=[]
        inputs=[r["known_case"]] if r["label"]=="buggy" else cases(r["problem"])
        for c in inputs:
            checks+=1
            try:
                value=solver(c)
                if not agrees(r["problem"],c,value): bad.append({"case":c,"reason":"contract mismatch","actual":repr(value)[:500]})
            except Exception as exc:
                bad.append({"case":c,"reason":type(exc).__name__,"actual":str(exc)[:500]})
            if len(bad)>=3: break
        passed=bool(bad) if r["label"]=="buggy" else not bad
        records.append({"id":r["id"],"label":r["label"],"checked":checks,"mismatches":bad,"passed":passed})
    return {"status":"passed" if all(r["passed"] for r in records) else "failed","records":records,
            "method":"Independent simple-path enumeration, exhaustive subarray enumeration and membership; bounded controls, not proof. Known failing cases withheld from discovery."}

def freeze():
    # Do not include editable-install metadata; compare tracked implementation against the measured revision.
    changed=subprocess.check_output(["git","diff","--name-only",V2,"--","backend/src","backend/tests","contracts","fixtures","web","requirements.lock.txt","backend/pyproject.toml","benchmarks/option_b"],cwd=ROOT,text=True).strip()
    dirty=subprocess.check_output(["git","status","--porcelain","--untracked-files=no"],cwd=ROOT,text=True).strip()
    if changed or dirty: raise ValueError("Measured implementation changed or tracked tree dirty: "+changed+" "+dirty)
    paths=subprocess.check_output(["git","ls-files","--","backend/src","backend/tests","contracts","fixtures","web","requirements.lock.txt","backend/pyproject.toml","benchmarks/option_b","benchmarks/external_v3","tools/audit_option_b_results.py","tools/evaluate_option_b_explanations.py","tools/option_b_human_review.py"],cwd=ROOT,text=True).splitlines()
    return {"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"engine_revision":V2,
            "files":{name:digest(ROOT/name) for name in sorted(paths)},"corpus":inventory(),"policy":load(ROOT/"benchmarks/option_b/protocol.json"),
            "environment":{"python":platform.python_version(),"platform":platform.platform(),"hypothesis":version("hypothesis"),"networkx":version("networkx")}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=["freeze","run"]);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.action=="freeze":
        a.out.mkdir(parents=True,exist_ok=False)
        label=preflight()
        dump(a.out/"label-preflight.json",label)
        print(json.dumps(label,ensure_ascii=False,indent=2))
        if label["status"]!="passed": raise SystemExit(1)
        dump(a.out/"freeze.json",freeze())
    else:
        if load(a.out/"label-preflight.json")["status"]!="passed": raise ValueError("Label preflight failed")
        v2.freeze=freeze
        v2.run(a.out,load(a.out/"freeze.json"))

if __name__=="__main__": main()
