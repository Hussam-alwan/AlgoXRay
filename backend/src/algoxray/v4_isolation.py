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
from .v4_profiling import PROFILE_BOOTSTRAP

IMAGE = "sha256:7594669de3f626d2de612f728140f71915609b310f7f1c16e2ed64d4a5190ade"
MAX_PIPE = 512 * 1024
MAX_SOURCE = 32768
MAX_INPUT = 16384
STARTUP_SECONDS = 8
BENCHMARK_READY = b"ALGOXRAY_BENCHMARK_READY\n"
# A static bootstrap, never interpolated with user source. No host bind mounts.
GUEST = PROFILE_BOOTSTRAP + r'''
import contextlib, hashlib, io, json, sys, time, math, itertools
req = json.loads(sys.stdin.readline())
src = req["source"]
mode = req.get("mode", "trace_profile")
instrumented = mode == "trace_profile"
profiler = ExecutionProfiler(src, instrumented and req["trace_limit"] > 0)
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
def snap(v,depth=0):
    if type(v) is int and v.bit_length() <= 256: return v
    if type(v) is bool or v is None: return v
    if type(v) is float:
        return v if math.isfinite(v) else {"unavailable":True,"kind":"nonfinite_float"}
    if type(v) is str and len(v) <= 160: return v
    if depth<2 and type(v) in (list,tuple):
        if len(v)<=24 and all(type(x) in (int,bool,float,str,type(None),list,tuple) for x in v):
            return [snap(x,depth+1) for x in v]
        return {"kind":"list" if type(v) is list else "tuple","size":len(v),
                "items":[snap(x,depth+1) for x in v[:24]],"truncated":len(v)>24}
    if depth<2 and type(v) is dict:
        return {"kind":"dict","size":len(v),"entries":[{"key":snap(k,depth+1),"value":snap(x,depth+1)}
                for k,x in itertools.islice(v.items(),24)],"truncated":len(v)>24}
    if depth<2 and type(v) in (set,frozenset):
        return {"kind":"set","size":len(v),"items":[snap(x,depth+1) for x in itertools.islice(v,24)],
                "truncated":len(v)>24,"order":"unspecified"}
    return {"unavailable": True}
def trace(f, kind, arg):
    global counter, truncated, trace_bytes
    if f.f_code.co_filename != "submission.py": return None
    entered_wall,entered_cpu=time.perf_counter_ns(),time.process_time_ns()
    profiler.tick(entered_wall,entered_cpu)
    try:
        if time.monotonic() > deadline: raise Deadline()
        if kind not in ("call","line","return","exception"): return trace
        ident = id(f)
        if ident not in frames:
            counter += 1
            frames[ident] = ("F"+str(counter),frames.get(id(f.f_back),(None,None))[0])
        frame,parent = frames[ident]
        profiler.event(f,kind,frame)
        if truncated or len(events) >= req["trace_limit"]:
            truncated = True
            return trace
        ev = {"event_id":"E"+str(len(events)+1),"frame_id":frame,"parent_frame_id":parent,
              "line":f.f_lineno,"kind":kind,"function":f.f_code.co_name,
              "snapshot_timing":"before_line" if kind=="line" else kind,
              "locals":{k:snap(v) for k,v in [(k,v) for k,v in f.f_locals.items() if not k.startswith("__") and type(v) in (int,bool,float,str,list,tuple,dict,set,frozenset,type(None))][:32]}}
        ev["snapshot_meta"]={"captured_locals":len(ev["locals"]),
                             "omitted_locals":sum(not k.startswith("__") for k in f.f_locals)-len(ev["locals"]),
                             "max_collection_items":24,"max_collection_depth":2}
        if f.f_code.co_name!="<module>":
            ev["globals"]={k:snap(f.f_globals[k]) for k in f.f_code.co_names[:24] if k in f.f_globals and type(f.f_globals[k]) in (int,bool,str,type(None))}
        if kind == "exception": ev["exception_type"] = arg[0].__name__
        trace_bytes+=len(json.dumps(ev,ensure_ascii=True))
        if trace_bytes>180000: truncated=True; return trace
        events.append(ev)
        return trace
    finally:
        if kind == "return": frames.pop(id(f),None)
        profiler.resume(entered_wall,entered_cpu)
out,err = Output(),Output()
original = sys.stdin
status, detail = "ok",None
exit_code = 0
failure_location = None
if req.get("announce_benchmark_start"):
    sys.stdout.write("ALGOXRAY_BENCHMARK_READY\n")
    sys.stdout.flush()
execution_start_wall,execution_start_cpu=time.perf_counter_ns(),time.process_time_ns()
try:
    code = compile(src,"submission.py","exec")
    sys.stdin = io.TextIOWrapper(io.BytesIO(req["stdin"].encode("utf-8")), encoding="utf-8", newline=None)
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        if instrumented:
            sys.settrace(trace)
        exec(code,{"__name__":"__main__","__file__":"submission.py"})
except Deadline: status,exit_code = "timeout",None
except Limit: status,exit_code = "output_limit",None
except SystemExit as exc:
    if exc.code not in (None,0):
        status,detail="exception","SystemExit"
        exit_code=exc.code if type(exc.code) is int and -2147483648<=exc.code<=2147483647 else 1
except BaseException as exc:
    status,detail="exception",type(exc).__name__
    exit_code=1
    if isinstance(exc, SyntaxError):
        failure_location={"line":exc.lineno,"column":exc.offset}
    else:
        tb=exc.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_filename=="submission.py":
                failure_location={"line":tb.tb_lineno,"function":tb.tb_frame.f_code.co_name}
            tb=tb.tb_next
finally:
    sys.settrace(None)
    sys.stdin=original
execution_wall_ns=time.perf_counter_ns()-execution_start_wall
execution_cpu_ns=time.process_time_ns()-execution_start_cpu
# The host also enforces a deadline independently of the guest's execution.
basis = None
if not instrumented and status=="ok" and execution_wall_ns>req["seconds"]*1e9:
    status,exit_code="timeout",None
    basis="guest_execution_wall_clock"
profile=profiler.report(status,execution_wall_ns,execution_cpu_ns)
if not instrumented:
    profile.update(method="uninstrumented_execution",scope="Compile and execution inside guest, without trace/profile callbacks. Not judge runtime.")
print(json.dumps({"status":status,"detail":detail,"basis":basis,"exit_code":exit_code,"failure_location":failure_location,
    "stdout":out.getvalue(),"stderr":err.getvalue(),"mode":mode,
    "profile":profile,"events":events,"trace_status":("disabled" if not instrumented else "truncated" if truncated else "complete")},ensure_ascii=True,allow_nan=False))
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

def execute_stdio(source, stdin, *, seconds=1.0, trace_limit=128, image=None, cancel=None, mode="trace_profile"):
    if type(source) is not str or not 0 < len(source.encode("utf-8")) <= MAX_SOURCE:
        raise ValueError("Source size outside supported bounds")
    if type(stdin) is not str or len(stdin.encode("utf-8")) > MAX_INPUT:
        raise ValueError("Input size outside supported bounds")
    if type(seconds) not in (float,int) or not 0.05 <= seconds <= 3 or type(trace_limit) is not int or not 0 <= trace_limit <= 256:
        raise ValueError("Invalid execution budget")
    if mode not in ("trace_profile","benchmark_uninstrumented"):
        raise ValueError("Unsupported execution mode")
    if mode=="benchmark_uninstrumented" and trace_limit!=0:
        raise ValueError("Uninstrumented mode requires trace_limit=0")
    name = "algoxray-v4-" + uuid.uuid4().hex
    try:
        image_id=image or configured_image()
        cmd=docker_command(name,image_id)
    except (OSError,ValueError,KeyError):return {"status":"infrastructure_error","detail":"dedicated_worker_unconfigured","events":[],"trace_trust":"guest_observation_not_authenticated"}
    benchmark = mode == "benchmark_uninstrumented"
    req = json.dumps({"source":source,"stdin":stdin,"seconds":seconds,"trace_limit":trace_limit,
                      "mode":mode,"announce_benchmark_start":benchmark},ensure_ascii=True).encode()+b"\n"
    started=time.monotonic()
    ready_at=None
    result={"status":"infrastructure_error"}
    proc=None
    readers=[]
    buffers=[bytearray(),bytearray()]
    overflow=threading.Event()
    def read(stream, target):
        nonlocal ready_at
        awaiting_ready = benchmark and target is buffers[0]
        try:
            while True:
                chunk=stream.read1(4096)
                if not chunk: break
                if len(target)+len(chunk)>MAX_PIPE:
                    overflow.set(); break
                target.extend(chunk)
                if awaiting_ready and b"\n" in target:
                    awaiting_ready=False
                    if target.startswith(BENCHMARK_READY):
                        del target[:len(BENCHMARK_READY)]
                        ready_at=time.monotonic()
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
            now=time.monotonic()
            benchmark_started=ready_at
            if benchmark and (benchmark_started is None or benchmark_started-started>STARTUP_SECONDS):
                if now-started>STARTUP_SECONDS:
                    result={"status":"infrastructure_error","detail":"benchmark_worker_startup_timeout"}; break
            elif benchmark and now-benchmark_started>seconds:
                result={"status":"timeout","basis":"host_benchmark_wall_clock"}; break
            if now-started>seconds+STARTUP_SECONDS:
                result={"status":"timeout","basis":"host_wall_clock"}; break
            time.sleep(.025)
        else:
            for t in readers: t.join(1)
            if overflow.is_set(): result={"status":"output_limit"}
            elif proc.returncode != 0: result={"status":"infrastructure_error","exit_code":proc.returncode}
            elif benchmark and ready_at is None:
                result={"status":"infrastructure_error","detail":"benchmark_worker_ready_missing"}
            elif benchmark and ready_at-started>STARTUP_SECONDS:
                result={"status":"infrastructure_error","detail":"benchmark_worker_startup_timeout"}
            else:
                try:
                    data=json.loads(buffers[0])
                    if type(data) is not dict or data.get("status") not in ("ok","timeout","output_limit","exception") or type(data.get("stdout")) is not str or type(data.get("events")) is not list:
                        raise ValueError("Invalid guest response")
                    result={k:data[k] for k in ("status","detail","stdout","stderr","events","trace_status","profile","exit_code","failure_location","mode") if k in data}
                    if data.get("basis")=="guest_execution_wall_clock" and benchmark and data["status"]=="timeout":
                        result["basis"]=data["basis"]
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
    result.update(image_id=image_id,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  input_sha256=hashlib.sha256(stdin.encode()).hexdigest(),
                  elapsed_ms=round((time.monotonic()-started)*1000,2), requested_mode=mode, host_wall_limit_seconds=seconds+STARTUP_SECONDS,
                  trace_trust="guest_observation_not_authenticated",cleanup_confirmed=cleanup_ok)
    if benchmark:
        result.update(startup_limit_seconds=STARTUP_SECONDS, benchmark_wall_limit_seconds=seconds,
                      startup_ms=round((ready_at-started)*1000,2) if ready_at is not None else None)
    return result
