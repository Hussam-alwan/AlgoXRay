"""Publish an explicit allowlist of synthetic V4 evidence only.
Never copy user packages, secrets, quota databases, review keys, or arbitrary logs.
"""
import argparse,hashlib,json,os,re,shutil
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--root",default=".");parser.add_argument("--out",required=True);args=parser.parse_args()
    root=Path(args.root).resolve();results=root/"results";out=Path(args.out).resolve()
    if out.exists():raise SystemExit("Use a new output directory")
    paths=[
        "v4-expansion-vertical.json","v4-extra-isolation.json","v4-isolation-smoke-expanded.json",
        "v4-runtime.json","v4-gemini-smoke.json","v4-gemini-smoke-retry.json",
        "v4-expanded-browser-retry/report.json","v4-expanded-browser-retry/evidence.json",
        "v4-external-pilot/freeze.json","v4-external-pilot/summary.json",
        "v4-expanded-ai/codeforces.json","v4-expanded-ai/deterministic_baseline.json",
        "v4-expanded-ai/guided.json","v4-expanded-ai/reference_draft.json",
        "v4-expanded-ai/source_only.json","v4-expanded-ai/witness.json",
        "v4-expanded-ai/trace.json","v4-expanded-ai/trace-retry.json",
        "v4-live-ai-evaluation/summary.json",
    ]
    for family in ("gcd","get_factors","sieve","kth","quicksort","longest_common_subsequence","possible_change"):
        for role in ("control","fault"):paths.append(f"v4-external-pilot/{family}-{role}.json")
    # Include clean reproduction data only after the process exited successfully.
    state=json.loads((results/"jobs/v4-clean-reproduction.json").read_text())
    if state.get("status")=="passed":
        paths.extend(["v4-clean-reproduction/progress.json","v4-clean-reproduction/vertical.json","v4-clean-reproduction/external/freeze.json","v4-clean-reproduction/external/summary.json"])
    secrets=[os.environ.get(k,"") for k in ("GEMINI_API_KEY","GOOGLE_API_KEY","GROQ_API_KEY","OPENROUTER_API_KEY")]
    if os.name=="nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,"Environment") as key:
            for name in ("GEMINI_API_KEY","GOOGLE_API_KEY","GROQ_API_KEY","OPENROUTER_API_KEY"):
                try:secrets.append(winreg.QueryValueEx(key,name)[0])
                except FileNotFoundError:pass
    secret_pattern=re.compile(r"(?:gsk_[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|sk-or-v1-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",re.I)
    collected=[]
    for name in paths:
        source=results/name
        raw=source.read_bytes()
        data=raw.decode("utf-8")
        json.loads(data)
        if any(isinstance(s,str) and len(s)>10 and s in data for s in secrets) or secret_pattern.search(data):
            raise SystemExit("Possible credential in "+name+"; no export written")
        collected.append((name,raw))
    out.mkdir(parents=True)
    manifest=[]
    for name,raw in collected:
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        manifest.append({"path":name,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)})
    (out/"MANIFEST.json").write_text(json.dumps({"scope":"Explicit synthetic development and licensed public benchmark results; not user submissions or a blind holdout. No review key or raw runtime logs.","files":manifest},indent=2)+"\n")
    print("Exported",len(manifest),"JSON files;",sum(x["bytes"] for x in manifest),"bytes")
if __name__=="__main__":main()
