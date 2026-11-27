"""Run actual Docker smoke probes. Not a certification of hostile-code security."""
import json
from pathlib import Path
import sys
from algoxray.v4_isolation import execute_stdio
from algoxray.v4_graph import observed_graph

def main():
    probes={
      "stdio":("a=int(input())\nprint(a+1)","4\n","ok","5"),
      "module_trace":("x=1\nx+=2\nprint(x)","","ok","3"),
      "readonly":("try:\n open('/app/probe','w')\nexcept OSError:\n print('blocked')","","ok","blocked"),
      "network":("import socket\ntry:\n socket.create_connection(('1.1.1.1',80),.2)\nexcept OSError:\n print('blocked')","","ok","blocked"),
      "uid":("import os\nprint(os.getuid())","","ok","10001"),
      "timeout":("while True: pass","","timeout",None),
      "output_limit":("print('a'*9000)","","output_limit",None),
    }
    report={}
    for name,(source,stdin,status,stdout) in probes.items():
        run=execute_stdio(source,stdin,seconds=.7)
        passed=run["status"]==status and run["cleanup_confirmed"] and (stdout is None or run.get("stdout","").strip()==stdout)
        if name=="module_trace": passed=passed and bool(observed_graph(run.get("events",[]))["changes"])
        report[name]={"passed":passed,"status":run["status"],"elapsed_ms":run["elapsed_ms"],"cleanup_confirmed":run["cleanup_confirmed"]}
        print(name,report[name],flush=True)
    path=Path("results/v4-isolation-smoke.json");path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(report,indent=2))
    return 0 if all(x["passed"] for x in report.values()) else 1
if __name__=="__main__": raise SystemExit(main())
