"""Synthetic live checks: reference proposal, discriminating input, matched ablation."""
import argparse,json,ast,time
from pathlib import Path
from algoxray.v4_authoring import draft_reference,import_problem
from algoxray.v4_gemini import provider_for
from algoxray.v4_engine import analyze_package,review
from algoxray.v4_provider import ProviderError,check_facts
from algoxray.v4_guidance import suggestions
from algoxray.v4_contracts import serialize

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);p.add_argument("--allow-cloud-synthetic",action="store_true");a=p.parse_args()
    if not a.allow_cloud_synthetic:raise SystemExit("Explicit synthetic cloud test consent required")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    provider=provider_for("openai/gpt-oss-120b",True)
    m={"id":"twice","title":"Twice","statement":"Read one integer n between 1 and 9. Print twice n.","fields":[{"name":"n","kind":"int","min":1,"max":9}],"lines":[["n"]],"output":"tokens"}
    correct="n=int(input())\nprint(2*n)\n"
    bad="n=int(input())\nif n==3:\n    print(n)\nelse:\n    print(2*n)\n"
    pkg={"manifest":m,"reference":correct,"controls":[{"case":{"n":1},"expected":"2"},{"case":{"n":9},"expected":"18"}]}
    report={}
    def record(k,v):
        report[k]=v
        (out/(k+".json")).write_text(json.dumps(v,indent=2))
        print(k, str({x:y for x,y in v.items() if x not in ("result","proposal","raw")})[:1200],flush=True)
    try:
        imported=import_problem("https://codeforces.com/problemset/problem/371/C")
        record("codeforces",{"status":imported["status"],"sample_count":len(imported["samples"]),"characters":len(imported["statement"])})
    except ValueError as e:record("codeforces",{"status":"unavailable","error":str(e)})
    try:
        ref=draft_reference(provider,m)
        same=ast.dump(ast.parse(ref["reference"]))==ast.dump(ast.parse(correct))
        record("reference_draft",{"status":ref["status"],"proposal":ref,"ast_matches_known_reference":same,"controls_passed":review(pkg)["passed"] if same else None})
    except (ProviderError,ValueError,SyntaxError) as e:record("reference_draft",{"status":"unavailable_or_invalid","error":str(e)})
    base=analyze_package(pkg,bad,count=2,reduce_calls=0)
    record("deterministic_baseline",{"status":base["status"]})
    guided=analyze_package(pkg,bad,count=2,reduce_calls=0,provider=provider,guided=True,spectrum=True)
    record("guided",{"status":guided["status"],"case":guided.get("witness",{}).get("case"),"guidance_status":guided.get("guidance",{}).get("status"),"probe_statuses":[x["status"] for x in guided.get("guidance",{}).get("probes",[])],"ai_status":guided.get("ai_status"),"result":guided})
    witness=analyze_package(pkg,bad,case={"n":3},reduce_calls=0)
    schema={"type":"object","properties":{"suspected_lines":{"type":"array","items":{"type":"integer"},"maxItems":3},"facts":{"type":"array","items":{"type":"object","properties":{"event_id":{"type":"string"},"variable":{"type":"string"},"value":{"type":["integer","boolean","string","null"]}},"required":["event_id","variable","value"],"additionalProperties":False},"maxItems":6}},"required":["suspected_lines","facts"],"additionalProperties":False}
    for arm in ("source_only","witness","trace"):
        data={"statement":m["statement"],"source":bad,"instruction":"Rank up to three suspected source lines, 1-based. Facts only about scalar local values in supplied events; return empty facts when no trace supplied."}
        if arm!="source_only":data.update(stdin=witness["witness"]["stdin"],expected=witness["witness"]["reference"]["stdout"],actual=witness["witness"]["student"]["stdout"])
        events=witness["witness"]["student"]["events"] if arm=="trace" else []
        if events:data["events"]=events
        try:
            t=time.monotonic();raw=provider.propose("diagnosis",data,schema);lines=raw.get("suspected_lines")
            if type(lines) is not list or len(lines)>3 or any(type(n) is not int or not 1<=n<=len(bad.splitlines()) for n in lines):raise ProviderError("invalid_ranking")
            facts=check_facts({"facts":raw.get("facts",[])},events)
            record(arm,{"status":"ok","lines":lines,"top1_known_line":bool(lines and lines[0]==3),"top3_known_line":3 in lines,"facts":facts,"supported_fact_count":sum(x["status"]=="matches_recorded_snapshot" for x in facts),"usage":provider.usage,"seconds":round(time.monotonic()-t,2),"raw":raw})
        except (ProviderError,ValueError,TypeError) as e:record(arm,{"status":"unavailable_or_invalid","error":str(e)})
    (out/"summary.json").write_text(json.dumps(report,indent=2))
if __name__=="__main__":main()
