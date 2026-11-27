"""Bounded extra checks for pinned V4 worker; no hostile-code certification."""
import argparse,json
from pathlib import Path
from algoxray.v4_isolation import execute_stdio
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
    probes={
        "no_provider_credentials":("import os\nprint('clean' if not any(os.getenv(k) for k in ('GEMINI_API_KEY','GOOGLE_API_KEY','GROQ_API_KEY','OPENROUTER_API_KEY')) else 'unexpected')",lambda s:s.strip()=="clean"),
        "root_mount_readonly":("m=open('/proc/mounts').read().splitlines()\nprint('readonly' if any(x.split()[1]=='/' and 'ro' in x.split()[3].split(',') for x in m) else 'unexpected')",lambda s:s.strip()=="readonly"),
        "bounded_pid_limit":("import os,time,errno\npids=[];blocked=False\ntry:\n    for _ in range(36):\n        try:\n            pid=os.fork()\n            if pid==0:\n                time.sleep(0.6)\n                os._exit(0)\n            pids.append(pid)\n        except OSError as e:\n            blocked=e.errno==errno.EAGAIN\n            break\nfinally:\n    for pid in pids:\n        os.waitpid(pid,0)\nprint(len(pids),blocked)",lambda s:len(s.split())==2 and s.split()[1]=="True" and 0<int(s.split()[0])<=31)
    }
    report={}
    for name,(source,check) in probes.items():
        r=execute_stdio(source,"",seconds=2,trace_limit=0)
        report[name]={"passed":r["status"]=="ok" and r.get("cleanup_confirmed") and check(r.get("stdout","")),"status":r["status"],"stdout":r.get("stdout"),"cleanup":r.get("cleanup_confirmed")}
        print(name,report[name],flush=True)
    with Path(a.out).open("x",encoding="utf-8") as f:json.dump(report,f,indent=2)
    return 0 if all(x["passed"] for x in report.values()) else 1
if __name__=="__main__":raise SystemExit(main())
