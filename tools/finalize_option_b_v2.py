"""Package audited v2 results, prepare external-review materials, and reproduce in a new worktree.

Runs only after the original release pipeline passes. Outputs are separate, never overwritten.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--job",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--worktree",required=True,type=Path)
    p.add_argument("--port",type=int,default=8796)
    a=p.parse_args()
    run,job,out,worktree=map(lambda x:x.resolve(),(a.input,a.job,a.out,a.worktree))
    progress=json.loads((job/"progress.json").read_text(encoding="utf-8"))
    freeze=json.loads((run/"freeze.json").read_text(encoding="utf-8"))
    if progress["status"]!="passed" or freeze["source_commit"]!=progress["source_commit"]:
        raise ValueError("Original release has not passed")
    out.mkdir(parents=True,exist_ok=False)
    state={"source_commit":freeze["source_commit"],"status":"running","stages":[]}
    def save():
        (out/"progress.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
    def step(name,command,cwd,timeout):
        rec={"name":name,"status":"running","started_at":datetime.now(timezone.utc).isoformat()}
        state["stages"].append(rec);save()
        print("Starting "+name,flush=True)
        with (out/(name+".log")).open("xb") as log:
            try:
                completed=subprocess.run(command,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
                rec.update(exit_code=completed.returncode,status="passed" if completed.returncode==0 else "failed")
            except (OSError,subprocess.TimeoutExpired) as exc:
                rec.update(status="failed",error=str(exc))
        rec["finished_at"]=datetime.now(timezone.utc).isoformat()
        save()
        if rec["status"]!="passed":
            state["status"]="failed";save();return False
        return True
    py=sys.executable
    save()
    if not step("conference",[py,"tools/package_option_b_conference.py","--input",str(run),"--job",str(job),"--out",str(run/"conference")],ROOT,180): return 1
    if not step("human-review",[py,"tools/option_b_human_review.py","prepare","--input",str(run),"--out",str(run/"human-review")],ROOT,120): return 1
    if worktree.exists():
        raise ValueError("Clean worktree already exists")
    if not step("clean-checkout",["git","worktree","add","--detach",str(worktree),freeze["source_commit"]],ROOT,120): return 1
    if not step("new-environment",[py,"-m","venv",str(worktree/".venv")],worktree,180): return 1
    newpy=str(worktree/".venv"/("Scripts/python.exe" if sys.platform=="win32" else "bin/python"))
    if not step("locked-install",[newpy,"-m","pip","install","--disable-pip-version-check","--retries","2","--timeout","30","-r","requirements.lock.txt"],worktree,600): return 1
    if not step("editable-install",[newpy,"-m","pip","install","--disable-pip-version-check","--no-deps","-e","./backend"],worktree,300): return 1
    if not step("clean-reproduction",[newpy,"tools/release_option_b_v2.py","--out","results/option-b-v2","--job","clean-reproduction","--port",str(a.port)],worktree,2400): return 1
    repeated=json.loads((worktree/"results/option-b-v2/summary.json").read_text(encoding="utf-8"))
    original=json.loads((run/"summary.json").read_text(encoding="utf-8"))
    comparison={"source_commit":freeze["source_commit"],"original":original,"clean_repeat":repeated,
                "note":"Fresh environment and checkout on the same computer; not independent-machine or human replication. Timing-dependent outcomes may vary."}
    (out/"reproduction-comparison.json").write_text(json.dumps(comparison,indent=2),encoding="utf-8")
    state["status"]="passed";save()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
