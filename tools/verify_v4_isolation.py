"""Run actual Docker smoke probes. Not a certification of hostile-code security."""
import json
from pathlib import Path
import sys
import argparse
from algoxray.v4_isolation import execute_stdio
from algoxray.v4_graph import observed_graph

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",default="results/v4-isolation-smoke-expanded.json");args=parser.parse_args()
    probes={
      "stdio":("a=int(input())\nprint(a+1)","4\n","ok","5"),
      "module_trace":("x=1\nx+=2\nprint(x)","","ok","3"),
      "readonly":("try:\n open('/app/probe','w')\nexcept OSError:\n print('blocked')","","ok","blocked"),
      "network":("import socket\ntry:\n socket.create_connection(('1.1.1.1',80),.2)\nexcept OSError:\n print('blocked')","","ok","blocked"),
      "uid":("import os\nprint(os.getuid())","","ok","10001"),
      "timeout":("while True: pass","","timeout",None),
      "output_limit":("print('a'*9000)","","output_limit",None),
      "memory":("try:\n x=bytearray(256*1024*1024)\n print('unexpected')\nexcept MemoryError:\n print('blocked')","","ok","blocked"),
      "host_wall_clock":("import time\ntime.sleep(25)","","timeout",None),
      "dedicated_image":("import os\nprint('clean' if not os.path.exists('/app/fixtures') else 'unexpected')","","ok","clean"),
      "capabilities":("p=open('/proc/self/status').read()\ncap=next(x.split()[1] for x in p.splitlines() if x.startswith('CapEff:'))\npriv=next(x.split()[1] for x in p.splitlines() if x.startswith('NoNewPrivs:'))\nprint(int(cap,16),priv)","","ok","0 1"),
    }
    report={}
    for name,(source,stdin,status,stdout) in probes.items():
        run=execute_stdio(source,stdin,seconds=.7)
        passed=run["status"]==status and run["cleanup_confirmed"] and (stdout is None or run.get("stdout","").strip()==stdout)
        if name=="module_trace": passed=passed and bool(observed_graph(run.get("events",[]))["changes"])
        if name=="memory" and run["status"]=="infrastructure_error" and run.get("exit_code")==137: passed=run["cleanup_confirmed"] # Exit 137 is consistent with cgroup OOM, not a proof of cause.
        report[name]={"passed":passed,"status":run["status"],"elapsed_ms":run["elapsed_ms"],"cleanup_confirmed":run["cleanup_confirmed"]}
        print(name,report[name],flush=True)
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise SystemExit("Choose a new output file to preserve earlier measurements")
    path.write_text(json.dumps(report,indent=2))
    return 0 if all(x["passed"] for x in report.values()) else 1
if __name__=="__main__": raise SystemExit(main())
