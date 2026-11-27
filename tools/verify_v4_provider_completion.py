"""Live local-only cache and open-ended grammar probes. No cloud or generated code execution."""
import argparse,json,time
from pathlib import Path
from fastapi.testclient import TestClient
from algoxray.api import app
from algoxray.v4_cache import CACHE,CachedLocalProvider
from algoxray.v4_provider import OllamaProvider,DIAGNOSIS_SCHEMA
from algoxray.v4_contracts import serialize

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",required=True);args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    report={"scope":"Synthetic local model probes only; no cloud requests, human ratings or generated code execution.","checks":[]}
    def write(): (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    CACHE.clear();provider=CachedLocalProvider(OllamaProvider(timeout=120))
    data={"statement":"No source or events are available. Abstain with empty hypotheses and facts.","events":[]}
    first=provider.propose("diagnosis",data,DIAGNOSIS_SCHEMA);u1=dict(provider.usage)
    second=provider.propose("diagnosis",data,DIAGNOSIS_SCHEMA);u2=dict(provider.usage)
    assert first==second and u1["cache"]=="miss" and u2["cache"]=="hit" and u2["eval_count"]==0
    report["cache"]={"first_usage":u1,"second_usage":u2,"same_result":first==second}
    report["checks"].append("real_local_cache_hit");write();print("real_local_cache_hit",flush=True)
    CACHE.clear();provider.propose("diagnosis",data,DIAGNOSIS_SCHEMA)
    assert provider.usage["cache"]=="miss"
    report["checks"].append("clear_invalidates_cache");write();print("clear_invalidates_cache",flush=True)
    # No const schema or candidate manifest is supplied in this authoring test.
    statement="Read integer n on the first line, where 1 <= n <= 8. Read exactly n integers on the second line, each between -9 and 9 inclusive. Print the sum of those integers."
    start=time.monotonic()
    with TestClient(app) as client:
        token=client.get("/api/session").json()["custom_code_token"]
        response=client.post("/api/v4/packages/draft",headers={"X-AlgoXRay-Token":token},
            json={"statement":statement,"model":"qwen2.5-coder:7b","use_cache":False})
    report["draft"]={"status_code":response.status_code,"result":response.json(),"seconds":round(time.monotonic()-start,3)}
    write()
    assert response.status_code==200, response.json()
    manifest=response.json()["manifest"];fields=manifest["fields"]
    assert len(fields)==2 and fields[0]["kind"]=="int" and fields[0]["min"]==1 and fields[0]["max"]==8
    assert fields[1]["kind"]=="ints" and fields[1]["min"]==-9 and fields[1]["max"]==9 and fields[1].get("length_from")==fields[0]["name"]
    assert manifest["statement"]==statement and serialize(manifest,{fields[0]["name"]:3,fields[1]["name"]:[1,2,3]})=="3\n1 2 3\n"
    report["checks"].append("open_ended_bounded_grammar_matches_known_constraints")
    report["status"]="passed";write();print("open_ended_bounded_grammar_matches_known_constraints",flush=True)

if __name__=="__main__":main()
