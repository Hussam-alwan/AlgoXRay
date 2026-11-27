"""Publish a fixed allowlist of synthetic/public completion evidence and verify exact bytes."""
import argparse,hashlib,json,os,re,subprocess
from datetime import datetime,timezone
from pathlib import Path

FAMILIES=("gcd","get_factors","sieve","kth","quicksort","longest_common_subsequence","possible_change")
def read(path):return json.loads(path.read_text(encoding="utf-8-sig"))
def verify(out):
 manifest=read(out/"MANIFEST.json")
 for row in manifest["files"]:
  path=(out/row["path"]).resolve()
  if not path.is_relative_to(out.resolve()):raise SystemExit("Evidence path escapes root")
  raw=path.read_bytes()
  if len(raw)!=row["bytes"] or hashlib.sha256(raw).hexdigest()!=row["sha256"]:raise SystemExit("Evidence mismatch: "+row["path"])
 print(json.dumps({"status":"verified","files":len(manifest["files"])}))
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--out",required=True);parser.add_argument("--verify-only",action="store_true");parser.add_argument("--checkout",default="D:/icips-v4-repro-completion");a=parser.parse_args()
 out=Path(a.out).resolve()
 if a.verify_only:return verify(out)
 root=Path(__file__).resolve().parents[1];results=root/"results"
 if out.exists():raise SystemExit("Choose a new evidence directory")
 jobs=("complete-d-unit","complete-d-browser","complete-e-failbrowser-fixed","complete-context-ablation","complete-clean-reproduction","complete-isolation","complete-extra-isolation")
 for name in jobs:
  if read(results/"jobs"/(name+".json")).get("status")!="passed":raise SystemExit("Incomplete job: "+name)
 live=read(results/"v4-completion-live.json")
 if live.get("status")!="passed" or live.get("v3_health_http")!=200:raise SystemExit("Live release verification incomplete")
 normal=read(results/"v4-completion-d-browser/report.json");negative=read(results/"v4-completion-e-failure-browser-fixed/report.json")
 study=read(results/"v4-completion-context-ablation/summary.json");repro=read(results/"v4-completion-reproduction/progress.json");external=read(results/"v4-completion-reproduction/external/summary.json")
 if normal["status"]!="passed" or negative["status"]!="passed" or normal["page_errors"] or negative["page_errors"]:raise SystemExit("Browser acceptance failed")
 if len(repro["steps"])!=7 or any(x["exit"]!=0 for x in repro["steps"]):raise SystemExit("Reproduction incomplete")
 if study["families"]!=7 or study["model_requests"]!=21:raise SystemExit("Ablation incomplete")
 if (external["fault_detected"],external["fault_total"],external["control_accusations"],external["control_total"],external["replays"])!=(7,7,0,7,21):raise SystemExit("External pilot changed; inspect results")
 unit=(results/"jobs/complete-d-unit.log").read_text(encoding="utf-8")
 if not re.search(r"223 passed",unit):raise SystemExit("Expected test checkpoint not present")
 files=[("v4-completion-live.json","live.json"),("jobs/complete-d-unit.log","unit-tests.txt"),("v4-completion-d-browser/report.json","browser/report.json"),
 ("v4-completion-d-browser/evidence.json","browser/evidence.json"),("v4-completion-d-browser/timing.csv","browser/timing.csv"),
 ("v4-completion-d-browser/profile-table.png","browser/profile-table.png"),("v4-completion-d-browser/profile-mobile.png","browser/profile-mobile.png"),
 ("v4-completion-e-failure-browser-fixed/report.json","browser-failures/report.json"),
 ("v4-completion-e-failure-browser-fixed/outage.json","browser-failures/outage.json"),("v4-completion-e-failure-browser-fixed/missing-trace.png","browser-failures/missing-trace.png"),
 ("jobs/complete-e-failbrowser.json","earlier-failures/browser-controls-job.json"),("jobs/complete-e-failbrowser.log","earlier-failures/browser-controls.txt"),
 ("v4-completion-a-local/report.json","earlier-failures/draft-a.json"),("v4-completion-b-local/report.json","earlier-failures/draft-b.json"),
 ("v4-completion-b-shape-local/report.json","local-draft-and-cache.json"),("v4-completion-isolation.json","isolation.json"),
 ("v4-completion-extra-isolation.json","extra-isolation.json"),("v4-completion-reproduction/progress.json","reproduction/progress.json"),
 ("v4-completion-reproduction/pytest.log","reproduction/unit-tests.txt"),("v4-completion-reproduction/vertical.json","reproduction/vertical.json")]
 for name in jobs:files.append(("jobs/"+name+".json","jobs/"+name+".json"))
 for prefix,folder in (("v4-completion-reproduction/external/","external/"),("v4-completion-context-ablation/","ablation/")):
  for name in ("freeze.json","summary.json"):files.append((prefix+name,folder+name))
 for family in FAMILIES:
  for role in ("control","fault"):
   name=family+"-"+role+".json";files.append(("v4-completion-reproduction/external/"+name,"external/"+name))
  for arm in ("no-ai","source_only","witness","trace","trace-verified"):
   name=family+"-"+arm+".json";files.append(("v4-completion-context-ablation/"+name,"ablation/"+name))
 secret_names=("GEMINI_API_KEY","GOOGLE_API_KEY","GROQ_API_KEY","OPENROUTER_API_KEY","DASHSCOPE_API_KEY")
 secret_values=[os.getenv(name,"") for name in secret_names]
 if os.name=="nt":
  import winreg
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,"Environment") as key:
   for name in secret_names:
    try:secret_values.append(winreg.QueryValueEx(key,name)[0])
    except FileNotFoundError:pass
 pattern=re.compile(r"(?:gsk_[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|sk-or-v1-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",re.I)
 collected=[]
 for source,name in files:
  raw=(results/source).read_bytes()
  if not name.endswith(".png"):
   text=raw.decode("utf-8-sig")
   if pattern.search(text) or any(type(secret) is str and len(secret)>10 and secret in text for secret in secret_values):raise SystemExit("Credential check failed: "+name)
   if name.endswith(".json"):json.loads(text)
  collected.append((name,raw))
 source_commit=subprocess.check_output(["git","-C",a.checkout,"rev-parse","HEAD"],text=True).strip()
 freeze={"publisher_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"created_at":datetime.now(timezone.utc).isoformat(),"runtime_commit":source_commit,
  "ablation_commit":read(results/"v4-completion-context-ablation/freeze.json")["git_head"],
  "packaging_parent_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
  "tests":223,"browser_checks":len(normal["checks"])+len(negative["checks"]),"browser_split":[len(normal["checks"]),len(negative["checks"])],
  "reproduction_steps":7,"external_faults":[7,7],"external_control_accusations":[0,7],"external_replays":21,
  "ablation_requests":21,"ablation_arms":study["arms"],
  "scope":"Same-machine software evidence and exposed public adaptations. Not independent security validation, unseen student accuracy, human ratings or conference submission. Ablation reuses earlier frozen witnesses; fresh deterministic pilot is separate."}
 collected.append(("SOURCE_FREEZE.json",(json.dumps(freeze,indent=2)+"\n").encode()))
 out.mkdir(parents=True);manifest=[]
 for name,raw in collected:
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
  manifest.append({"path":name,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)})
 (out/"MANIFEST.json").write_text(json.dumps({"scope":"Fixed allowlist of authored synthetic examples, public benchmark adaptations and local-only inference. No private submissions, package stores, credentials, quota databases or reviewer keys.","files":manifest},indent=2)+"\n",encoding="utf-8")
 verify(out)
if __name__=="__main__":main()
