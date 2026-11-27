"""Export only named synthetic/public continuation evidence, never runtime stores."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];results=root/"results";out=Path(a.out).resolve()
    if out.exists():raise SystemExit("Choose a new evidence directory")
    jobs=["v4-provider-regression","v4-local-model-final","v4-final-reproduction","v4-delivery-browser","v4-final-isolation","v4-final-extra-isolation"]
    for name in jobs:
        state=json.loads((results/"jobs"/(name+".json")).read_text(encoding="utf-8"))
        if state.get("status")!="passed":raise SystemExit("Incomplete job: "+name)
    files=[("jobs/v4-provider-regression.log","unit-tests.txt"),
           ("v4-local-model-final/report.json","local-model.json"),
           ("v4-delivery-browser/report.json","browser/report.json"),
           ("v4-delivery-browser/evidence.json","browser/evidence.json"),
           ("v4-delivery-browser/timing.csv","browser/timing.csv"),
           ("v4-delivery-browser/profile-table.png","browser/profile-table.png"),
           ("v4-delivery-browser/profile-mobile.png","browser/profile-mobile.png"),
           ("v4-final-reproduction/progress.json","reproduction/progress.json"),
           ("v4-final-reproduction/vertical.json","reproduction/vertical.json"),
           ("v4-final-reproduction/pytest.log","reproduction/unit-tests.txt"),
           ("v4-final-isolation.json","isolation.json"),
           ("v4-final-extra-isolation.json","extra-isolation.json"),
           ("jobs/v4-timing-browser.json","earlier-failed-browser.json"),
           ("jobs/v4-timing-browser.log","earlier-failed-browser.txt")]
    for name in jobs:files.append(("jobs/"+name+".json","jobs/"+name+".json"))
    for name in ["freeze.json","summary.json"]:
        files.append(("v4-final-reproduction/external/"+name,"external/"+name))
    for family in ("gcd","get_factors","sieve","kth","quicksort","longest_common_subsequence","possible_change"):
        for role in ("control","fault"):
            name=family+"-"+role+".json"
            files.append(("v4-final-reproduction/external/"+name,"external/"+name))
    pattern=re.compile(r"(?:gsk_[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|sk-or-v1-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",re.I)
    secrets=[os.getenv(k,"") for k in ("GEMINI_API_KEY","GOOGLE_API_KEY","GROQ_API_KEY","OPENROUTER_API_KEY")]
    if os.name=="nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,"Environment") as key:
            for name in ("GEMINI_API_KEY","GOOGLE_API_KEY","GROQ_API_KEY","OPENROUTER_API_KEY"):
                try:secrets.append(winreg.QueryValueEx(key,name)[0])
                except FileNotFoundError:pass
    collected=[]
    for source,name in files:
        raw=(results/source).read_bytes()
        if not name.endswith(".png"):
            text=raw.decode("utf-8-sig")
            if pattern.search(text) or any(isinstance(s,str) and len(s)>10 and s in text for s in secrets):
                raise SystemExit("Credential check failed: "+name)
            if name.endswith(".json"):json.loads(text)
        collected.append((name,raw))
    # Validate every input before writing any export.
    out.mkdir(parents=True)
    manifest=[]
    for name,raw in collected:
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        manifest.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    (out/"MANIFEST.json").write_text(json.dumps(dict(scope="Explicit synthetic examples, licensed public benchmark adaptations and local-only model smoke. No user package/source store, credentials or private reviewer keys.",files=manifest),indent=2)+"\n",encoding="utf-8")
    print("Exported",len(manifest),"files;",sum(x["bytes"] for x in manifest),"bytes")


if __name__=="__main__":main()
