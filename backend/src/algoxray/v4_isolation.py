"""Bounded local Docker execution. Defense in depth, not a hostile-code security proof.

Only Docker receives executable text. The guest's trace/result is observational
and must not be treated as authenticated evidence from adversarial code.
"""
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import uuid
from .paths import ROOT

IMAGE = "sha256:7594669de3f626d2de612f728140f71915609b310f7f1c16e2ed64d4a5190ade"
MAX_PIPE = 512 * 1024
MAX_SOURCE = 32768
MAX_INPUT = 16384
# A static bootstrap, never interpolated with user source. No host bind mounts.
GUEST = r'''
import contextlib, hashlib, io, json, sys, time
req = json.loads(sys.stdin.readline())
src = req["source"]
events = []
frames = {}
counter = 0
truncated = False
trace_bytes = 0
deadline = time.monotonic() + req["seconds"]
class Deadline(Exception): pass
class Limit(Exception): pass
class Output(io.StringIO):
    def write(self, s):
        if self.tell() + len(s) > 8192: raise Limit("output limit")
        return super().write(s)
def snap(v):
    if type(v) is int and v.bit_length() <= 256: return v
    if type(v) is bool or v is None: return v
    if type(v) is str and len(v) <= 160: return v
    if type(v) in (list, tuple) and len(v) <= 24 and all(type(x) in (int,bool,str,type(None)) for x in v):
        return [snap(x) for x in v]
    return {"unavailable": True}
def trace(f, kind, arg):
    global counter, truncated, trace_bytes
    if f.f_code.co_filename != "submission.py": return None
    if time.monotonic() > deadline: raise Deadline()
    if kind not in ("call","line","return","exception"): return trace
    if truncated or len(events) >= req["trace_limit"]: truncated = True; return trace
    ident = id(f)
    if ident not in frames:
        counter += 1
        frames[ident] = ("F"+str(counter),frames.get(id(f.f_back),(None,None))[0])
    frame,parent = frames[ident]
    ev = {"event_id":"E"+str(len(events)+1),"frame_id":frame,"parent_frame_id":parent,
          "line":f.f_lineno,"kind":kind,"function":f.f_code.co_name,
          "snapshot_timing":"before_line" if kind=="line" else kind,
          "locals":{k:snap(v) for k,v in [(k,v) for k,v in f.f_locals.items() if not k.startswith("__") and type(v) in (int,bool,str,list,tuple,type(None))][:32]}}
    # Only scalar globals referenced by the function, distinguished from locals.
    if f.f_code.co_name!="<module>":
        ev["globals"]={k:snap(f.f_globals[k]) for k in f.f_code.co_names[:24] if k in f.f_globals and type(f.f_globals[k]) in (int,bool,str,type(None))}
    if kind == "exception": ev["exception_type"] = arg[0].__name__
    trace_bytes+=len(json.dumps(ev,ensure_ascii=True))
    if trace_bytes>180000: truncated=True; return trace
    events.append(ev)
    if kind == "return": frames.pop(ident,None)
    return trace
out,err = Output(),Output()
original = sys.stdin
status, detail = "ok",None
try:
    code = compile(src,"submission.py","exec")
    sys.stdin = io.StringIO(req["stdin"])
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        sys.settrace(trace)
        exec(code,{"__name__":"__main__","__file__":"submission.py"})
except Deadline: status = "timeout"
except Limit: status = "output_limit"
except SystemExit as exc:
    if exc.code not in (None,0): status,detail="exception","SystemExit"
except BaseException as exc: status,detail="exception",type(exc).__name__
finally:
    sys.settrace(None)
    sys.stdin=original
print(json.dumps({"status":status,"detail":detail,"stdout":out.getvalue(),"stderr":err.getvalue(),
    "events":events,"trace_status":"truncated" if truncated else "complete"},ensure_ascii=True,allow_nan=False))
'''
def configured_image():
    value=os.getenv("ALGOXRAY_V4_IMAGE")
    if value:return value
    path=ROOT/"results"/"v4-runtime.json"
    if path.is_file():
        data=json.loads(path.read_text(encoding="utf-8"))
        return data["image_id"]
    raise ValueError("Dedicated V4 worker missing; run tools/prepare_v4_worker.py")

def docker_command(name, image):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("Use an explicitly pinned local image ID")
    return ["docker","run","--rm","-i","--name",name,"--pull=never",
            "--network","none","--read-only","--cap-drop","ALL",
            "--security-opt","no-new-privileges","--user","10001:10001",
            "--memory","128m","--memory-swap","128m","--cpus","0.5","--pids-limit","32",
            "--tmpfs","/tmp:rw,noexec,nosuid,nodev,size=8m","--log-driver","none",
            "--no-healthcheck","--workdir","/tmp","--entrypoint","python",image,"-I","-B","-c",GUEST]

def execute_stdio(source, stdin, *, seconds=1.0, trace_limit=128, image=None, cancel=None):
    if type(source) is not str or not 0 < len(source.encode("utf-8")) <= MAX_SOURCE:
        raise ValueError("Source size outside supported bounds")
    if type(stdin) is not str or len(stdin.encode("utf-8")) > MAX_INPUT:
        raise ValueError("Input size outside supported bounds")
    if type(seconds) not in (float,int) or not 0.05 <= seconds <= 3 or type(trace_limit) is not int or not 0 <= trace_limit <= 256:
        raise ValueError("Invalid execution budget")
    name = "algoxray-v4-" + uuid.uuid4().hex
    try:cmd = docker_command(name,image or configured_image())
    except (OSError,ValueError,KeyError):return {"status":"infrastructure_error","detail":"dedicated_worker_unconfigured","events":[],"trace_trust":"guest_observation_not_authenticated"}
    req = json.dumps({"source":source,"stdin":stdin,"seconds":seconds,"trace_limit":trace_limit},ensure_ascii=True).encode()+b"\n"
    started=time.monotonic()
    result={"status":"infrastructure_error"}
    proc=None
    readers=[]
    buffers=[bytearray(),bytearray()]
    overflow=threading.Event()
    def read(stream, target):
        try:
            while True:
                chunk=stream.read(4096)
                if not chunk: break
                if len(target)+len(chunk)>MAX_PIPE:
                    overflow.set(); break
                target.extend(chunk)
        except OSError: pass
    def write():
        try: proc.stdin.write(req); proc.stdin.close()
        except (OSError,ValueError): pass
    cleanup_ok=True
    try:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for stream,target in zip((proc.stdout,proc.stderr),buffers):
            t=threading.Thread(target=read,args=(stream,target),daemon=True); t.start(); readers.append(t)
        threading.Thread(target=write,daemon=True).start()
        while proc.poll() is None:
            if cancel is not None and cancel.is_set(): result={"status":"cancelled"}; break
            if overflow.is_set(): result={"status":"output_limit"}; break
            if time.monotonic()-started > seconds+8: result={"status":"timeout","basis":"host_wall_clock"}; break
            time.sleep(.025)
        else:
            for t in readers: t.join(1)
            if overflow.is_set(): result={"status":"output_limit"}
            elif proc.returncode != 0: result={"status":"infrastructure_error","exit_code":proc.returncode}
            else:
                try:
                    data=json.loads(buffers[0])
                    if type(data) is not dict or data.get("status") not in ("ok","timeout","output_limit","exception") or type(data.get("stdout")) is not str or type(data.get("events")) is not list:
                        raise ValueError("Invalid guest response")
                    result={k:data[k] for k in ("status","detail","stdout","stderr","events","trace_status") if k in data}
                except (ValueError,UnicodeError): result={"status":"infrastructure_error","detail":"invalid_guest_protocol"}
    except OSError: result={"status":"infrastructure_error","detail":"docker_unavailable"}
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: cleanup_ok=False
        # --rm normally cleans successful containers; verify no named container remains.
        if proc is not None:
            try:
                subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=5)
                check=subprocess.run(["docker","ps","-aq","--filter","name=^/"+name+"$"],capture_output=True,timeout=5)
                cleanup_ok=cleanup_ok and check.returncode==0 and not check.stdout.strip()
            except (OSError,subprocess.TimeoutExpired): cleanup_ok=False
        for t in readers: t.join(.2)
    if not cleanup_ok: result={"status":"infrastructure_error","detail":"container_cleanup_unconfirmed"}
    result.update(image_id=cmd[cmd.index("--entrypoint")+2],source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  input_sha256=hashlib.sha256(stdin.encode()).hexdigest(),
                  elapsed_ms=round((time.monotonic()-started)*1000,2),
                  trace_trust="guest_observation_not_authenticated",cleanup_confirmed=cleanup_ok)
    return result
