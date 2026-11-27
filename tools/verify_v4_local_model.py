"""Three bounded local-only model probes. No cloud calls or generated-code execution."""
import argparse
import hashlib
import json
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from algoxray.v4_provider import OllamaProvider, DIAGNOSIS_SCHEMA, ProviderError, check_facts, check_hypotheses
from algoxray.v4_isolation import execute_stdio
from algoxray.v4_contracts import validate_manifest


def local_get(path):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):raise OSError("redirect blocked")
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open("http://127.0.0.1:11434/api/"+path,timeout=3) as response:
        return json.loads(response.read(65536))


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",required=True);args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    provider=OllamaProvider(timeout=120)
    report=dict(scope="Three synthetic local-only smoke tasks, not comparative accuracy or human review.",
        model=provider.model,context=provider.context,commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        tasks=[],gpu_samples=[])
    report["model_tags"]=local_get("tags")
    stop=threading.Event()
    def sample():
        while not stop.is_set():
            try:
                r=subprocess.run(["nvidia-smi","--query-gpu=memory.used,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=3)
                if r.returncode==0:
                    memory,load=map(int,r.stdout.strip().splitlines()[0].split(","))
                    report["gpu_samples"].append(dict(board_memory_mib=memory,board_utilization_percent=load))
            except (OSError,ValueError,subprocess.TimeoutExpired):pass
            stop.wait(1)
    thread=threading.Thread(target=sample,daemon=True);thread.start()
    def save():
        (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    manifest=dict(id="twice",title="Twice",statement="Read n from 1 to 9, print 2*n.",fields=[dict(name="n",kind="int",min=1,max=9)],lines=[["n"]],output="tokens")
    draft_schema={"type":"object","properties":{"manifest":{"const":manifest}},"required":["manifest"],"additionalProperties":False}
    # The const probe verifies transport/schema adherence only; it is not open-ended authoring quality.
    observed=execute_stdio("n=3\nprint(n)\n","",trace_limit=128)
    events=observed.get("events",[])
    tasks=[("contract_draft",dict(statement=manifest["statement"],candidate_manifest=manifest),draft_schema),
        ("diagnosis",dict(statement=manifest["statement"],source="n=3\nprint(n)\n",expected="6",actual=observed.get("stdout"),events=events),DIAGNOSIS_SCHEMA),
        ("diagnosis",dict(statement="No source, trace or outputs are available. Abstain with empty hypotheses and facts.",events=[]),DIAGNOSIS_SCHEMA)]
    try:
        for i,(task,data,schema) in enumerate(tasks):
            row=dict(name=["schema_draft_transport","diagnosis","abstention"][i]);start=time.monotonic()
            try:
                result=provider.propose(task,data,schema)
                row.update(status="schema_valid",response=result,usage=dict(provider.usage))
                if i==0:validate_manifest(result["manifest"])
                else:
                    supplied=events if i==1 else []
                    row.update(hypotheses=check_hypotheses(result,supplied),facts=check_facts(result,supplied))
                    if i==2:row["abstained"]=result=={"hypotheses":[],"facts":[]}
            except (ProviderError,ValueError) as exc:row.update(status="unavailable_or_invalid",error=str(exc),usage=dict(provider.usage))
            row["seconds"]=round(time.monotonic()-start,3);report["tasks"].append(row);save()
            print(row["name"],row["status"],row["seconds"],flush=True)
        report["model_ps"]=local_get("ps")
    finally:
        stop.set();thread.join(4)
        report["peak_board_memory_mib"]=max((x["board_memory_mib"] for x in report["gpu_samples"]),default=None)
        report["memory_scope"]="Observed whole GPU board samples, not isolated model peak allocation. ps records model residency at end."
        save()
    return 0 if len(report["tasks"])==3 and all(x["status"]=="schema_valid" for x in report["tasks"]) and report["tasks"][-1].get("abstained") else 1


if __name__=="__main__":raise SystemExit(main())
