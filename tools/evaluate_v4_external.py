"""Paired external benchmark smoke; no AI, no human claims; preserve raw evidence."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
from algoxray.v4_engine import review,analyze_package
from algoxray.v4_contracts import digest
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);p.add_argument("--seed",type=int,default=2026);a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    path=Path("benchmarks/v4_external/manifest.json")
    data=json.loads(path.read_text(encoding="utf-8"))
    snapshot={"git_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"manifest_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"seed":a.seed,"scope":data["scope"],"python":sys.version}
    (out/"freeze.json").write_text(json.dumps(snapshot,indent=2))
    rows=[]
    for f in data["families"]:
        pkg=f["package"];checks=review(pkg)
        for role in ("control","fault"):
            start=time.monotonic()
            r=analyze_package(pkg,f[role],seed=a.seed,count=3,reduce_calls=1,generator="hypothesis",spectrum=True) if checks["passed"] else {"status":"reference_review_failed"}
            result={"family":f["family"],"role":role,"package_sha256":digest(pkg),"reference_review":checks,"known_bug_line":f["fault_line_in_adaptation"],"result":r}
            (out/(f["family"]+"-"+role+".json")).write_text(json.dumps(result,indent=2))
            row={"family":f["family"],"role":role,"status":r["status"],"kind":r.get("kind"),"replay_count":r.get("replay_count",0),"trace":r.get("witness",{}).get("student",{}).get("trace_status"),"rank_status":r.get("suspiciousness",{}).get("status"),"seconds":round(time.monotonic()-start,2)}
            rows.append(row);print(json.dumps(row),flush=True)
    report={"scope":snapshot["scope"],"trials":len(rows),"fault_detected":sum(r["role"]=="fault" and r["status"]=="observed_mismatch" for r in rows),"fault_total":sum(r["role"]=="fault" for r in rows),"control_accusations":sum(r["role"]=="control" and r["status"]=="observed_mismatch" for r in rows),"control_total":sum(r["role"]=="control" for r in rows),"replays":sum(r["replay_count"] for r in rows),"rows":rows}
    (out/"summary.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!="rows"}),flush=True)
if __name__=="__main__":main()
