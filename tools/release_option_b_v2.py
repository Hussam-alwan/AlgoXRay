"""Run ordered local release checks, frozen evaluation, audit and explanation ablation.

Never overwrites a previous evaluation or browser evidence. Stops on any stage failure.
Run from a clean checkout with the pinned Python environment.
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
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--job",required=True)
    p.add_argument("--port",type=int,default=8795)
    args=p.parse_args()
    out=args.out.resolve()
    directory=ROOT/"results/jobs"/args.job
    directory.mkdir(parents=True,exist_ok=False)
    if out.exists(): raise SystemExit("Evaluation output already exists; choose a fresh directory")
    py=sys.executable
    steps=[
        ("baseline",["tools/option_b_baseline.py","--verify"],360),
        ("browser",["tools/verify_option_b_browser.py","--out",str(directory/"browser"),"--port",str(args.port)],300),
        ("freeze",["benchmarks/option_b/evaluate.py","freeze","--out",str(out)],60),
        ("evaluate",["benchmarks/option_b/evaluate.py","run","--out",str(out)],1800),
        ("audit",["tools/audit_option_b_results.py","--input",str(out),"--report",str(out/"audit.json")],180),
        ("explanations",["tools/evaluate_option_b_explanations.py","--input",str(out),"--out",str(out/"explanation-review")],180),
    ]
    status={"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "status":"running","stages":[],"output":str(out)}
    def save():
        (directory/"progress.json").write_text(json.dumps(status,indent=2),encoding="utf-8")
    save()
    for name,command,timeout in steps:
        record={"name":name,"status":"running","started_at":datetime.now(timezone.utc).isoformat()}
        status["stages"].append(record)
        save()
        print("Starting "+name,flush=True)
        with (directory/(name+".log")).open("xb") as log:
            try:
                process=subprocess.run([py,*command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
                record["exit_code"]=process.returncode
                record["status"]="passed" if process.returncode==0 else "failed"
            except (OSError,subprocess.TimeoutExpired) as exc:
                record["status"]="failed";record["error"]=str(exc)
        record["finished_at"]=datetime.now(timezone.utc).isoformat()
        save()
        if record["status"]!="passed":
            status["status"]="failed";save();return 1
    status["status"]="passed";save()
    print(json.dumps(status,indent=2),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
