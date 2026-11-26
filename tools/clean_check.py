"""Verify installation into a newly created venv on the same machine."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / (".venv-verify-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    if directory.exists():
        raise SystemExit("Refusing to reuse an existing verification environment")
    venv.EnvBuilder(with_pip=True).create(directory)
    python = directory / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    commands = [
        [str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.lock.txt")],
        [str(python), "-m", "pip", "install", "-e", str(ROOT / "backend") + "[dev]"],
        [str(python), "-m", "pytest", "backend/tests", "-q", "--junitxml=docs/clean-tests.xml"],
        [str(python), "-m", "algoxray.cli", "analyze", "--problem", "dijkstra_v1", "--fixture", "dijkstra_premature_visited",
         "--case", "contracts/dijkstra.example.json", "--no-shrink", "--summary", "--output", "results/clean-check-evidence.json"],
    ]
    evidence = []
    for index, command in enumerate(commands):
        print(f"clean installation step {index + 1}/{len(commands)}", flush=True)
        result = subprocess.run(command, cwd=ROOT)
        evidence.append({"step": index + 1, "exit_code": result.returncode})
        if result.returncode != 0:
            raise SystemExit(result.returncode)
    result = {"status": "passed", "created_at": datetime.now(timezone.utc).isoformat(),
              "method": "Fresh virtual environment on the same Windows machine; not an independent-machine replication",
              "python_environment": directory.name, "checks": evidence}
    (ROOT / "docs/clean-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
