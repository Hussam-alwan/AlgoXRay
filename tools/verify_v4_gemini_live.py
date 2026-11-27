"""Live paid-or-quota-consuming checks. Run only with owner consent. Synthetic data only."""
import argparse,json,time,urllib.request,urllib.error
from pathlib import Path
from algoxray.v4_gemini import MODELS
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",required=True);args=parser.parse_args()
    base="http://127.0.0.1:8002"
    def call(path,body=None):
        req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers={"Content-Type":"application/json","X-AlgoXRay-Token":token if body is not None else ""})
        try:
            with urllib.request.urlopen(req,timeout=115) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    token=""
    _,session=call("/api/session");token=session["custom_code_token"]
    statement="Read one integer n (1 <= n <= 9) on one line and print twice n as one integer."
    checks={}
    code,result=call("/api/v4/packages/draft",{"statement":statement,"model":MODELS[0],"cloud_consent":False})
    checks["consent_denied"]={"passed":code==403,"http":code}
    for model in MODELS:
        t=time.monotonic()
        code,result=call("/api/v4/packages/draft",{"statement":statement,"model":model,"cloud_consent":True})
        manifest=result.get("manifest",{})
        fields=manifest.get("fields",[])
        valid=len(fields)==1 and fields[0].get("kind")=="int" and fields[0].get("min")==1 and fields[0].get("max")==9
        checks[model]={"passed":code==200 and result.get("status")=="draft_unreviewed" and valid,"http":code,"status":result.get("status"),"detail":result.get("detail"),"model":result.get("model"),"manifest":manifest,"usage":result.get("usage"),"elapsed_s":round(time.monotonic()-t,2)}
        print(model,checks[model],flush=True)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x",encoding="utf-8") as f:json.dump(checks,f,indent=2)
    return 0 if all(c["passed"] for c in checks.values()) else 1
if __name__=="__main__":raise SystemExit(main())
