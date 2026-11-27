"""Local-only timeout reproduction, corrected control and one optional real Ollama diagnosis."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from algoxray.v4_contracts import serialize,digest
from algoxray.v4_isolation import execute_stdio
from algoxray.v4_execution_diagnostics import execution_diagnostics
from algoxray.v4_diagnostic_context import diagnose_execution
from algoxray.v4_provider import model_inventory
from algoxray.v4_gemini import provider_for

BAD="n=int(input())\na=list(map(int,input().split()))\nx=int(input())\na.sort()\nl=0\nr=n\nwhile l<r:\n    mid=(l+r)//2\n    if a[mid]<=x:\n        l=mid\n    else:\n        r=mid\nprint(l)\n"
REFERENCE="n=int(input())\na=list(map(int,input().split()))\nx=int(input())\nprint(sum(1 for v in a if v<=x))\n"
def main():
 p=argparse.ArgumentParser();p.add_argument("--out",required=True);p.add_argument("--local-ai",action="store_true");a=p.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 package={"manifest":{"id":"timeout_count_fixture","title":"Authored bounded count fixture","statement":"Read n integers and x; print the number of values at most x. n is 1 to 8, array values are 0 to 9, x is 0 to 10.","fields":[{"name":"n","kind":"int","min":1,"max":8},{"name":"a","kind":"ints","min":0,"max":9,"length_from":"n"},{"name":"x","kind":"int","min":0,"max":10}],"lines":[["n"],["a"],["x"]],"output":"tokens"},"reference":REFERENCE,
 "controls":[{"case":{"n":4,"a":[5,1,5,2],"x":2},"expected":"2\n"},{"case":{"n":1,"a":[0],"x":0},"expected":"1\n"}]}
 case=package["controls"][0]["case"];stdin=serialize(package["manifest"],case)
 reference=execute_stdio(REFERENCE,stdin,trace_limit=256)
 bad=execute_stdio(BAD,stdin,trace_limit=256)
 fixed_source=BAD.replace("l=mid\n","l=mid+1\n")
 fixed=execute_stdio(fixed_source,stdin,trace_limit=256)
 report={"scope":"Authored bounded fixture, same machine. One input, no replay/search/causal-accuracy claim. No cloud calls.","git_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "package":package,"package_sha256":digest(package),"source":BAD,"fixed_source":fixed_source,"stdin":stdin,"reference":reference,"student":bad,"fixed":fixed}
 report["observations"]=execution_diagnostics(BAD,bad)
 assert reference["status"]=="ok" and reference["stdout"]=="2\n"
 assert bad["status"]=="timeout" and report["observations"]["findings"]
 assert report["observations"]["findings"][0]["assignments"][0]["line"]==10
 assert fixed["status"]=="ok" and fixed["stdout"]==reference["stdout"]
 if a.local_ai:
  report["local_model"]={k:v for k,v in next((m for m in model_inventory() if m.get("name")=="qwen2.5-coder:7b"),{}).items() if k in ("name","digest")}
  report["diagnosis"]=diagnose_execution(package,BAD,{"stdin":stdin,"student":bad,"reference":reference},provider_for("qwen2.5-coder:7b",False))
 else:report["diagnosis"]={"ai_status":"not_requested"}
 report["source_files"]={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in ("backend/src/algoxray/v4_execution_diagnostics.py","backend/src/algoxray/v4_diagnostic_context.py","backend/src/algoxray/v4_api.py","backend/src/algoxray/v4_engine.py")}
 (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
 print(json.dumps({"status":"passed","timeout_findings":len(report["observations"]["findings"]),"unchanged_update_lines":[x["line"] for f in report["observations"]["findings"] for x in f["assignments"]],"fixed_status":fixed["status"],"ai_status":report["diagnosis"]["ai_status"],"ai_error":report["diagnosis"].get("ai_error")}),flush=True)
if __name__=="__main__":main()
