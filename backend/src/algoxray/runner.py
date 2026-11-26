import json
import math
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time


class InvalidSubmission(ValueError):
    pass


class WorkerFailure(InvalidSubmission):
    """Execution infrastructure failure, not evidence about a solution."""
    pass


class AnalysisCancelled(BaseException):
    pass


class Runner:
    """Persistent worker, fresh submission namespace per case, hard parent timeout."""
    def __init__(self, submission, timeout=1.0, cancel=None, fresh_process=False):
        self.submission = submission
        self.timeout = timeout
        self.process = None
        self.messages = None
        self.calls = 0
        self.startups = 0
        self.cancel = cancel
        self.fresh_process = fresh_process

    def check_cancel(self):
        if self.cancel is not None and self.cancel.is_set():
            self.close()
            raise AnalysisCancelled()

    def _receive(self, seconds):
        deadline = time.monotonic() + seconds
        while True:
            self.check_cancel()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise queue.Empty()
            try:
                return self.messages.get(timeout=min(remaining, 0.05))
            except queue.Empty:
                continue

    def _start(self):
        allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL"}
        env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
        self.messages = messages = queue.Queue()
        self.process = process = subprocess.Popen(
            [sys.executable, "-I", str(Path(__file__).with_name("worker.py")), str(self.submission.path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1, env=env, **options)
        self.startups += 1

        def reader():
            try:
                while True:
                    line = process.stdout.readline(3 * 1024 * 1024 + 1)
                    if not line:
                        break
                    if len(line) > 3 * 1024 * 1024:
                        messages.put({"protocol_error": "Worker output too large"})
                        return
                    decoded = json.loads(line)
                    if type(decoded) is not dict:
                        messages.put({'protocol_error': 'Worker response is not an object'})
                        return
                    messages.put(decoded)
            except (ValueError, OSError) as exc:
                messages.put({"protocol_error": str(exc)})
            finally:
                messages.put({"worker_exited": True})

        threading.Thread(target=reader, daemon=True).start()
        try:
            hello = self._receive(5)
        except queue.Empty:
            self.close()
            raise WorkerFailure("Worker startup timed out")
        if hello.get("ready") is False:
            self.close()
            raise InvalidSubmission(hello.get("message", "Source could not be compiled"))
        if hello.get("ready") is not True or hello.get("source_sha256") != self.submission.sha256:
            self.close()
            raise WorkerFailure("Source identity mismatch or worker handshake failed")

    def run(self, case, trace=False, trace_limit=2000):
        self.check_cancel()
        if self.fresh_process or self.process is None or self.process.poll() is not None:
            self.close()
            try:
                self._start()
            except OSError as exc:
                self.close()
                raise WorkerFailure('Worker startup failed') from exc
        self.calls += 1
        start = time.perf_counter()
        try:
            self.process.stdin.write(json.dumps({"case": case, "problem_id": self.submission.problem_id, "trace": trace, "trace_limit": trace_limit, "timeout": self.timeout}) + "\n")
            self.process.stdin.flush()
            result = self._receive(self.timeout + 0.15)
            if result.get("status") == "invalid_submission":
                raise InvalidSubmission(result.get("message", "Invalid submission"))
            if "worker_exited" in result or "protocol_error" in result or result.get("status") == "worker_error":
                self.close()
                raise WorkerFailure("Worker protocol failed")
            elapsed = result.get("elapsed_ms")
            if (result.get("status") not in {"ok","contract_violation","timeout","exception"}
                    or type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed < 0
                    or type(result.get("events")) is not list
                    or result.get("trace_status") not in {"complete","truncated","not_run","failed"}
                    or (result["status"] == "ok" and "output" not in result)):
                self.close()
                raise WorkerFailure("Invalid worker response")
            self.check_cancel()
            if self.fresh_process:
                self.close()
            return result
        except queue.Empty:
            self.close()
            return {"status": "timeout", "exception_type": "ParentDeadline", "events": [],
                    "trace_status": "failed" if trace else "not_run",
                    "elapsed_ms": round((time.perf_counter() - start) * 1000, 4)}
        except (BrokenPipeError, OSError) as exc:
            self.close()
            raise WorkerFailure(str(exc)) from exc

    def close(self):
        process, self.process = self.process, None
        if process is None:
            return
        if process.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    os.killpg(process.pid, signal.SIGKILL)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
        for stream in (process.stdin, process.stdout):
            if stream:
                stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
