"""Fixed synthetic/public evidence export for the timeout diagnosis continuation."""
import argparse,hashlib,json,os,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def main():
 p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
 root=Path(__file__).resolve().parents[1];results=root/"results";out=Path(a.out)
 if out.exists():raise SystemExit("Choose a new export directory")
 jobs=("timeout-explanation-final-unit","timeout-explanation-browser","timeout-explanation-final-failbrowser","timeout-explanation-local","timeout-explanation-local-final")
 for name in jobs:
  if read(results/"jobs"/(name+".json")).get("status")!="passed":raise SystemExit("Incomplete job: "+name)
 if "239 passed" not in (results/"jobs/timeout-explanation-final-unit.log").read_text(encoding="utf-8"):raise SystemExit("Test checkpoint missing")
 normal=read(results/"v4-timeout-explanation-browser/report.json");failure=read(results/"v4-timeout-explanation-final-failbrowser/report.json")
 live=read(results/"v4-timeout-explanation-live.json")
 if len(normal["checks"])!=27 or len(failure["checks"])!=7 or live["status"]!="passed":raise SystemExit("Journey verification incomplete")
 files=[("jobs/timeout-explanation-final-unit.log","unit-tests.txt"),("v4-timeout-explanation-browser/report.json","browser/report.json"),
 ("v4-timeout-explanation-browser/timeout-finding.png","browser/timeout-finding.png"),
 ("v4-timeout-explanation-final-failbrowser/report.json","browser-failures/report.json"),
 ("v4-timeout-explanation-final-failbrowser/profile-outage.json","browser-failures/profile-outage.json"),
 ("v4-timeout-explanation-final-failbrowser/profile-fixture.json","browser-failures/profile-fixture.json"),
 ("v4-timeout-explanation-local/report.json","local/initial-conflicting-hypotheses.json"),
 ("v4-timeout-explanation-local-final/report.json","local/final-abstention.json"),("v4-timeout-explanation-live.json","live.json")]
 for name in jobs:files.append(("jobs/"+name+".json","jobs/"+name+".json"))
 names=("GEMINI_API_KEY","GOOGLE_API_KEY","GROQ_API_KEY","OPENROUTER_API_KEY","DASHSCOPE_API_KEY")
 secrets=[os.getenv(n,"") for n in names]
 if os.name=="nt":
  import winreg
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,"Environment") as key:
   for name in names:
    try:secrets.append(winreg.QueryValueEx(key,name)[0])
    except FileNotFoundError:pass
 pattern=re.compile(r"(?:gsk_[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|sk-or-v1-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",re.I)
 collected=[]
 for source,name in files:
  raw=(results/source).read_bytes()
  if not name.endswith(".png"):
   text=raw.decode("utf-8-sig")
   if pattern.search(text) or any(type(s) is str and len(s)>10 and s in text for s in secrets):raise SystemExit("Credential check failed: "+name)
   if name.endswith(".json"):json.loads(text)
  collected.append((name,raw))
 head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
 runtime=live["runtime_commit"]
 sources={}
 changed=subprocess.check_output(["git","diff","--name-only","d783135",runtime],text=True).splitlines()
 for name in changed:
  if name.startswith(("backend/src/","web/")):
   raw=subprocess.check_output(["git","show",runtime+":"+name])
   if raw!=(root/name).read_bytes():raise SystemExit("Runtime worktree mismatch: "+name)
   sources[name]=hashlib.sha256(raw).hexdigest()
 freeze={"created_at":datetime.now(timezone.utc).isoformat(),"runtime_commit":runtime,"packaging_parent_commit":head,"source_files":sources,
 "tests":239,"browser_checks":{"normal":27,"failure_and_fixture":7},"live_status":live["status"],
 "local_model_observations":"Initial valid response contained conflicting unverified hypotheses; later tuned response abstained. Both retained. No causal accuracy claim.",
 "scope":"Authored synthetic examples and a live summary for an intentional l=mid mutation. No user's unsaved editor captured, private package stores, credentials or cloud calls."}
 collected.append(("SOURCE_FREEZE.json",(json.dumps(freeze,indent=2)+"\n").encode()))
 collected.append(("compatibility-probe.json",(json.dumps({"source":"import sys\nprint(sys.stdin.buffer.read())\n","stdin":"123\n","observed_status":"exception","detail":"AttributeError","cleanup_confirmed":True,"scope":"Observed directly during roadmap review; current StringIO stdin compatibility gap, not a user-solution fault."},indent=2)+"\n").encode()))
 out.mkdir(parents=True);rows=[]
 for name,raw in collected:
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
  rows.append({"path":name,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)})
 (out/"MANIFEST.json").write_text(json.dumps({"scope":freeze["scope"],"files":rows},indent=2)+"\n",encoding="utf-8")
 for row in rows:
  raw=(out/row["path"]).read_bytes()
  assert len(raw)==row["bytes"] and hashlib.sha256(raw).hexdigest()==row["sha256"]
 print(json.dumps({"status":"verified","files":len(rows),"runtime":runtime}))
if __name__=="__main__":main()
