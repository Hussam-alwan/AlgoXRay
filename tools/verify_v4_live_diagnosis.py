"""Live development evaluation; synthetic code only, explicit operator opt-in.
Never claim human review or automatically execute arbitrary AI code.
"""
import argparse,ast,json,time
from pathlib import Path
from algoxray.v4_engine import review,analyze_package
from algoxray.v4_gemini import provider_for
from algoxray.v4_repair import propose_repair,verify_repair
from algoxray.v4_provider import ProviderError

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    p.add_argument("--allow-cloud-synthetic",action="store_true")
    p.add_argument("--models",nargs="+",required=True)
    a=p.parse_args()
    if not a.allow_cloud_synthetic:raise SystemExit("Explicit synthetic cloud test consent required")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    d=json.loads(Path("web/static/v4-demos.json").read_text(encoding="utf-8"))["sum"]
    package=d["package"];source=d["mutant"]
    checked=review(package)
    if not checked["passed"]:raise SystemExit("Fixture reference failed controls")
    def write(name,data):
        with (out/name).open("x",encoding="utf-8") as f:json.dump(data,f,indent=2)
    control=analyze_package(package,d["correct"],count=2,reduce_calls=0)
    baseline=analyze_package(package,source,count=2,reduce_calls=0)
    write("baseline.json",{"review":checked,"control":control,"fault":baseline})
    if baseline["status"]!="observed_mismatch":raise SystemExit("No fixture witness")
    summary=[]
    for i,model in enumerate(a.models):
        entry={"model":model,"scope":"one synthetic development bug, not independent accuracy"}
        start=time.monotonic()
        try:
            provider=provider_for(model,True)
            run=analyze_package(package,source,count=2,reduce_calls=0,case=baseline["witness"]["case"],provider=provider)
            entry["diagnosis_status"]=run.get("ai_status")
            entry["diagnosis_error"]=run.get("ai_error")
            entry["hypotheses"]=run.get("hypotheses",[])
            entry["facts"]=run.get("ai_facts",[])
            entry["diagnosis_usage"]=run.get("ai_usage",{})
            entry["witness_reproduced"]=run["status"]=="observed_mismatch"
            write(f"{i}-diagnosis.json",run)
            try:
                patch=propose_repair(provider,package,source,baseline["witness"]["case"])
                entry["repair_status"]=patch["status"]
                entry["repair_usage"]=getattr(provider,"usage",{})
                write(f"{i}-proposal.json",patch)
                # Strict pre-reviewed equivalence only, not automatic arbitrary model code execution.
                if ast.dump(ast.parse(patch["candidate"]))==ast.dump(ast.parse(d["correct"])):
                    verified=verify_repair(package,source,d["correct"],baseline["witness"]["case"],count=3)
                    entry["repair_status"]=verified["status"]
                    write(f"{i}-verification.json",verified)
                else:entry["repair_status"]="needs_manual_review"
            except (ProviderError,ValueError,SyntaxError) as e:entry["repair_status"]="unavailable_or_invalid";entry["repair_error"]=type(e).__name__+":"+str(e)[:100]
        except (ProviderError,ValueError) as e:entry["error"]=type(e).__name__+":"+str(e)[:100]
        entry["seconds"]=round(time.monotonic()-start,2)
        summary.append(entry);write(f"{i}-summary.json",entry)
        print(json.dumps({k:v for k,v in entry.items() if k not in ("facts","hypotheses")}),flush=True)
    write("summary.json",summary)
if __name__=="__main__":main()
