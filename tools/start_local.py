"""Start only this loopback service, leaving unrelated occupied ports alone."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8000"


def health():
    try:
        with urllib.request.urlopen(URL + "/api/health", timeout=1) as response:
            result = json.load(response)
        return result if result.get("execution_mode") == "local_trusted" and result.get("problems") == 2 else None
    except Exception:
        return None


def main():
    status = health()
    if status:
        print(json.dumps({"url": URL, "status": "already_ready", "health": status}))
        return
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", 8000))
        except OSError:
            raise SystemExit("Port 8000 is occupied by another service; use start.bat with a different port manually")
    directory = ROOT / "results/jobs"
    directory.mkdir(parents=True, exist_ok=True)
    flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    with (directory / "local-server.log").open("a", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-m", "algoxray.cli", "serve"], cwd=ROOT,
                                   stdout=log, stderr=subprocess.STDOUT, **flags)
    for _ in range(40):
        status = health()
        if status:
            record = {"url": URL, "status": "ready", "pid": process.pid, "health": status}
            (directory / "local-server.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
            print(json.dumps(record))
            return
        if process.poll() is not None:
            break
        time.sleep(0.25)
    raise SystemExit("Server did not become ready; inspect results/jobs/local-server.log")


if __name__ == "__main__":
    main()
