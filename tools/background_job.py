"""Run an explicit local development job and retain its exit status and log."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def main():
    action, name, *command = sys.argv[1:]
    if not re.fullmatch(r"[a-z0-9_-]{1,40}", name) or not command:
        raise SystemExit("Provide a simple job name and an explicit command")
    directory = ROOT / "results/jobs"
    directory.mkdir(parents=True, exist_ok=True)
    state_path = directory / (name + ".json")
    log_path = directory / (name + ".log")
    if action == "start":
        if state_path.exists():
            previous = json.loads(state_path.read_text(encoding="utf-8"))
            if previous.get("status") == "running":
                raise SystemExit("This job name is already running; inspect its log first")
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "execute", name, *command],
                                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, **options)
        print(json.dumps({"pid": process.pid, "log": str(log_path), "state": str(state_path)}))
    elif action == "execute":
        state = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(), "command": command}
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        try:
            completed = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONUTF8": "1"})
            state.update(status="passed" if completed.returncode == 0 else "failed", exit_code=completed.returncode)
        except Exception as exc:
            state.update(status="failed", error=str(exc))
            raise
        finally:
            state["finished_at"] = datetime.now(timezone.utc).isoformat()
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    else:
        raise SystemExit("Unknown action")


if __name__ == "__main__":
    main()
