"""Same-machine clean-checkout deterministic reproduction, no live cloud inference."""
import argparse,json,os,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument("--checkout",required=True);p.add_argument("--out",required=True);p.add_argument("--commit",required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];checkout=Path(a.checkout).resolve();out=Path(a.out).resolve()
    if checkout.exists() or out.exists():raise SystemExit("Choose new checkout and output paths")
    out.mkdir(parents=True);steps=[]
    env={k:v for k,v in os.environ.items() if k not in ("GEMINI_API_KEY","GOOGLE_API_KEY","GROQ_API_KEY","OPENROUTER_API_KEY","ALGOXRAY_V4_PACKAGE_STORE","ALGOXRAY_V4_REPAIR_STORE")}
    # No live model tasks are invoked in this deterministic reproduction.
    runtime=json.loads((root/"results/v4-runtime.json").read_text(encoding="utf-8"))
    env["ALGOXRAY_V4_IMAGE"]=runtime["image_id"]
    def run(name,cmd,cwd):
        print(name,flush=True)
        with (out/(name+".log")).open("wb") as f:
            r=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
        steps.append({"name":name,"exit":r.returncode})
        (out/"progress.json").write_text(json.dumps({"commit":a.commit,"steps":steps,"scope":"same machine and same pinned worker, no live AI"},indent=2))
        if r.returncode:raise SystemExit(r.returncode)
    run("checkout",["git","worktree","add","--detach",str(checkout),a.commit],root)
    run("venv",[sys.executable,"-m","venv",str(checkout/".venv")],checkout)
    py=str(checkout/".venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python"))
    run("lock",[py,"-m","pip","install","-r","requirements.lock.txt"],checkout)
    run("install",[py,"-m","pip","install","--no-deps","-e","backend"],checkout)
    run("pytest",[py,"-m","pytest","backend/tests","-q"],checkout)
    run("vertical",[py,"tools/verify_v4_vertical.py","--out",str(out/"vertical.json")],checkout)
    run("external",[py,"tools/evaluate_v4_external.py","--out",str(out/"external"),"--seed","2026"],checkout)
    print("REPRODUCTION PASSED",flush=True)
if __name__=="__main__":main()
