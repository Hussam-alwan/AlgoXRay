"""Trusted fixture tests for the guest protocol, not a sandbox security proof."""
import json
import subprocess
import sys
import pytest
from algoxray.v4_isolation import GUEST

def guest(source,stdin="",mode="trace_profile",trace_limit=128):
    req={"source":source,"stdin":stdin,"seconds":1,"trace_limit":trace_limit,"mode":mode}
    return json.loads(subprocess.check_output([sys.executable,"-I","-c",GUEST],
        input=(json.dumps(req)+"\n").encode(),timeout=5))

@pytest.mark.parametrize("source",[
    "print(int(input())+int(input()))",
    "import sys; print(sum(map(int,sys.stdin.read().split())))",
    "import sys; print(int(sys.stdin.readline())+int(sys.stdin.readline()))",
    "import sys; print(sum(map(int,sys.stdin.buffer.read().split())))",
    "import sys; print(int(sys.stdin.buffer.readline())+int(sys.stdin.buffer.readline()))",
    "class Solver:\n def solve(self,n): return n if n<=1 else n+self.solve(n-1)\nif __name__=='__main__': print(Solver().solve(int(input())))"
])
def test_complete_program_io(source):
    # The recursion fixture consumes a single 3; all others consume 2 and 4.
    stdin="3\n" if source.startswith("class") else "2\n4\n"
    result=guest(source,stdin)
    assert result["status"]=="ok" and result["stdout"].strip()=="6"
    assert result["exit_code"]==0

def test_no_instrumentation_and_equal_output():
    source="import sys; print(sys.gettrace() is None, sys.getprofile() is None)"
    plain=guest(source,mode="benchmark_uninstrumented",trace_limit=0)
    assert plain["status"]=="ok" and plain["stdout"].strip()=="True True"
    assert plain["events"]==[] and plain["trace_status"]=="disabled"
    assert plain["profile"]["method"]=="uninstrumented_execution"
    src="print(sum(range(100)))"
    assert guest(src)["stdout"]==guest(src,mode="benchmark_uninstrumented",trace_limit=0)["stdout"]

def test_failure_location_and_exit_code():
    syntax=guest("if")
    assert syntax["status"]=="exception" and syntax["detail"]=="SyntaxError"
    assert syntax["failure_location"]["line"]==1 and syntax["exit_code"]==1
    error=guest("def f():\n raise IndexError()\nf()")
    assert error["failure_location"]=={"line":2,"function":"f"}
    assert guest("import sys; sys.exit(7)")["exit_code"]==7
