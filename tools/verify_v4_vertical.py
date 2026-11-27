"""Actual Docker evaluation of three distinct declarative packages; development examples only."""
import argparse,json
from pathlib import Path
from algoxray.v4_engine import review,analyze_package
from algoxray.v4_contracts import PackageStore
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args()
    demos=json.loads(Path("web/static/v4-demos.json").read_text())
    report={}
    for name,d in demos.items():
        p=d["package"]
        checked=review(p)
        good=analyze_package(p,d["correct"],count=2,reduce_calls=0)
        bad=analyze_package(p,d["mutant"],count=2,reduce_calls=2)
        passed=checked["passed"] and good["status"]=="no_witness_found" and bad["status"]=="observed_mismatch" and bad["replay_count"]==3 and bool(bad["student_graph"]["nodes"])
        if name=="hamburgers":passed=passed and bool(bad["student_graph"]["relations"]["data"])
        report[name]={"passed":passed,"reference_review":checked,"correct":good,"faulty":bad}
        print(name,passed,good["status"],bad["status"],flush=True)
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2)
    return 0 if all(r["passed"] for r in report.values()) else 1
if __name__=="__main__":raise SystemExit(main())
