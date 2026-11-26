"""Standalone trusted-code worker. Process separation is NOT a security sandbox."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algoxray.tracing import SELECTED, safe_value
from algoxray.output_codec import encode_output, UnsupportedOutput


class ExecutionDeadline(Exception):
    pass


class OutputLimit(Exception):
    pass


class MissingSolve(Exception):
    pass


class LimitedOutput(io.TextIOBase):
    def __init__(self):
        self.text = ""

    def write(self, text):
        if len(self.text) + len(text) > 4096:
            raise OutputLimit("Submission output exceeded 4096 characters")
        self.text += text
        return len(text)


def execute(code, filename, request):
    started = time.perf_counter()
    deadline = started + request.get("timeout", 1.0)
    events, trace_bytes = [], 0
    frames = {}
    next_frame = 0
    truncated = False
    enabled = request.get("trace", False)
    maximum = min(request.get("trace_limit", 2000), 2000)
    output = LimitedOutput()

    def recorder(frame, event, arg):
        nonlocal trace_bytes, truncated, next_frame
        if frame.f_code.co_filename != filename:
            return None
        if time.perf_counter() > deadline:
            raise ExecutionDeadline("Submission exceeded its execution deadline")
        if enabled and not truncated and frame.f_code.co_name != "<module>" and event in ("call", "line", "return", "exception"):
            identity = id(frame)
            if identity not in frames:
                next_frame += 1
                frames[identity] = (f"F{next_frame:05d}", frames.get(id(frame.f_back), (None, None))[0])
            frame_id, parent_frame_id = frames[identity]
            variables = sorted(frame.f_locals.items(), key=lambda pair: (pair[0] not in SELECTED, pair[0]))
            snapshot = {k: safe_value(v) for k, v in variables[:32]
                        if not k.startswith("__") and (k in SELECTED or type(v) in (int, float, bool, str, list, tuple, set, dict, type(None)))}
            entry = {"event_id": f"E{len(events) + 1:05d}", "kind": event, "line": frame.f_lineno,
                     "function": frame.f_code.co_name, "snapshot_timing": "before_line" if event == "line" else event,
                     "locals": snapshot, "frame_id": frame_id, "parent_frame_id": parent_frame_id}
            if event == "return" and frame.f_code.co_name == "solve":
                entry["return_value"] = safe_value(arg)
            if event == "exception":
                entry["exception_type"] = arg[0].__name__
            trace_bytes += len(json.dumps(entry, ensure_ascii=True))
            if len(events) >= maximum or trace_bytes > 1024 * 1024:
                truncated = True
            else:
                events.append(entry)
            if event == "return":
                frames.pop(identity, None)
        return recorder

    previous = sys.gettrace()
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            sys.settrace(recorder)
            namespace = {"__name__": "algoxray_submission", "__file__": filename}
            exec(code, namespace)
            if not callable(namespace.get("solve")):
                raise MissingSolve("Submission must expose solve(payload)")
            value = namespace["solve"](request["case"])
            # Historical Dijkstra contract accepts positive infinity for unreachable vertices.
            if request.get('problem_id') == 'dijkstra_v1' and type(value) is list and len(value) <= 8:
                value = [None if type(v) is float and v == float('inf') else v for v in value]
            normalized = encode_output(value)
        result = {"status": "ok", "output": normalized}
    except UnsupportedOutput as exc:
        result = {"status": "contract_violation", "message": str(exc)}
    except ExecutionDeadline:
        result = {"status": "timeout", "exception_type": "ExecutionDeadline"}
    except MissingSolve as exc:
        result = {"status": "invalid_submission", "message": str(exc)}
    except BaseException as exc:
        location = None
        tb = exc.__traceback__
        while tb:
            if tb.tb_frame.f_code.co_filename == filename:
                location = {"line": tb.tb_lineno, "function": tb.tb_frame.f_code.co_name}
            tb = tb.tb_next
        result = {"status": "exception", "exception_type": type(exc).__name__, "message": str(exc)[:500],
                  "exception_line": location["line"] if location else None,
                  "exception_function": location["function"] if location else None}
    finally:
        sys.settrace(previous)
    result.update({"elapsed_ms": round((time.perf_counter() - started) * 1000, 4),
                   "events": events, "stdout": output.text,
                   "trace_status": ("truncated" if truncated else "complete") if enabled else "not_run"})
    return result


def main():
    raw = Path(sys.argv[1]).read_bytes()
    filename = str(Path(sys.argv[1]).resolve())
    try:
        code = compile(raw.decode("utf-8-sig"), filename, "exec")
    except (SyntaxError, UnicodeError) as exc:
        print(json.dumps({"ready": False, "error": type(exc).__name__, "message": str(exc)[:500]}), flush=True)
        return
    print(json.dumps({"ready": True, "source_sha256": hashlib.sha256(raw).hexdigest()}), flush=True)
    for line in sys.stdin:
        try:
            result = execute(code, filename, json.loads(line))
        except BaseException as exc:
            result = {"status": "worker_error", "exception_type": type(exc).__name__}
        print(json.dumps(result, ensure_ascii=True, allow_nan=False, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
