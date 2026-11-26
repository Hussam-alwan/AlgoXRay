"""Execute the external-source pilot in order and retain stage logs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--job",type=Path,required=True)
    a=p.parse_args()
    out=a.out.resolve();job=a.job.resolve();job.mkdir(parents=True,exist_ok=False)
    state={"status":"running","stages":[]}
    def save(): (job/"progress.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
    for name,cmd in [
        ("freeze",["benchmarks/external_v2/evaluate.py","freeze","--out",str(out)]),
        ("evaluate",["benchmarks/external_v2/evaluate.py","run","--out",str(out)]),
        ("audit",["tools/audit_option_b_results.py","--input",str(out),"--report",str(out/"audit.json")]),
        ("explanations",["tools/evaluate_option_b_explanations.py","--input",str(out),"--out",str(out/"explanation-review")]),
        ("human-review",["tools/option_b_human_review.py","prepare","--input",str(out),"--out",str(out/"human-review")])]:
        record={"name":name,"status":"running","started_at":datetime.now(timezone.utc).isoformat()};state["stages"].append(record);save()
        with (job/(name+".log")).open("xb") as f:
            result=subprocess.run([sys.executable,*cmd],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        record.update(status="passed" if result.returncode==0 else "failed",exit_code=result.returncode,finished_at=datetime.now(timezone.utc).isoformat());save()
        if result.returncode: state["status"]="failed";save();return 1
    state["status"]="passed";save();return 0
if __name__=="__main__": raise SystemExit(main())
