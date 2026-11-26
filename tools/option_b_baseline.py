"""Inventory WP0; optionally verify without overwriting historical release evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPLAY_PATH = "results/core-checks/clean-ui/binary-evidence.json"
REVIEWED_SOURCE_SHA = "1da5ed7513a01510b7e58ff2fba0d0ff1081d97ffaad0493ce026f273afe4ac2"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def compare_bytes(raw: bytes, expected: str) -> dict:
    actual = digest(raw)
    normalized = digest(raw.replace(b"\r\n", b"\n"))
    return {
        "expected_sha256": expected,
        "raw_sha256": actual,
        "lf_sha256": normalized,
        "status": "exact" if actual == expected else (
            "lf_only" if normalized == expected else "different"
        ),
    }


def compare_file(path: Path, expected: str) -> dict:
    if not path.is_file():
        return {"expected_sha256": expected, "status": "missing"}
    return compare_bytes(path.read_bytes(), expected)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def installed_pins() -> dict:
    result = {}
    for line in (ROOT / "requirements.lock.txt").read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, expected = line.partition("==")
        if not sep or not name or not expected:
            raise ValueError(f"Unsupported lock entry: {line}")
        try:
            actual = metadata.version(name)
        except metadata.PackageNotFoundError:
            actual = None
        result[name] = {"expected": expected, "actual": actual, "matches": expected == actual}
    return result


def replay_source_is_reviewed(path: Path) -> bool:
    identity = json.loads(path.read_text(encoding="utf-8-sig"))["submission"]
    return (identity["source_sha256"] == REVIEWED_SOURCE_SHA
            and digest(identity["source"].encode("utf-8")) == REVIEWED_SOURCE_SHA)


def check(name: str, args: list[str], directory: Path) -> dict:
    log = directory / f"{name}.log"
    print(f"Running {name}", flush=True)
    with log.open("xb") as output:
        try:
            process = subprocess.run(args, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                     timeout=300, check=False)
            code = process.returncode
            status = "passed" if code == 0 else "failed"
        except (OSError, subprocess.TimeoutExpired) as exc:
            output.write(str(exc).encode("utf-8", errors="replace"))
            code, status = None, "failed"
    return {"name": name, "status": status, "exit_code": code, "log": log.name}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Run tests and reviewed witness replay")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    directory = ROOT / "results/jobs/option-b-baseline" / now.strftime("%Y%m%dT%H%M%S%fZ")
    directory.mkdir(parents=True, exist_ok=False)
    freeze_path = ROOT / "results/core-release/freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8-sig"))
    catalog = json.loads((ROOT / "fixtures/catalog.json").read_text(encoding="utf-8-sig"))
    fixture_results = {
        entry["id"]: compare_file(ROOT / "fixtures" / entry["path"], entry["sha256"])
        for entry in catalog
    }
    historic = {name: compare_file(ROOT / name, expected) for name, expected in freeze["files"].items()}
    pins = installed_pins()
    dirty = git("status", "--porcelain", "--untracked-files=normal")
    blockers = []
    if sys.version_info[:2] != (3, 12):
        blockers.append("CPython 3.12 is required by the current project")
    if sys.implementation.name != "cpython":
        blockers.append("Expected CPython")
    if any(not entry["matches"] for entry in pins.values()):
        blockers.append("Installed dependencies differ from requirements.lock.txt")
    if any(entry["status"] != "exact" for entry in fixture_results.values()):
        blockers.append("At least one catalog source has a raw-byte hash mismatch")
    if dirty:
        blockers.append("Working tree is not clean; commit or use a clean checkout before verification")
    report = {
        "created_at": now.isoformat(),
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(dirty),
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "implementation": sys.implementation.name},
        "dependency_pins": pins,
        "historical_freeze_sha256": digest(freeze_path.read_bytes()),
        "historical_comparison": historic,
        "catalog_comparison": fixture_results,
        "blockers": blockers,
        "checks": [],
        "browser_verification": "not_run",
        "status": "blocked" if blockers else "inventory_only",
    }
    if args.verify and not blockers:
        py = sys.executable
        commands = [
            ("pip-check", [py, "-m", "pip", "check"]),
            ("pytest", [py, "-m", "pytest", "backend/tests", "-q",
                        "--junitxml=" + str(directory / "tests.xml")]),
        ]
        try:
            reviewed = replay_source_is_reviewed(ROOT / REPLAY_PATH)
        except (OSError, ValueError, KeyError, TypeError):
            reviewed = False
        if reviewed:
            commands.append(("reviewed-replay", [py, "-m", "algoxray.cli", "replay", REPLAY_PATH,
                                                 "--trusted-local-file"]))
        else:
            report["blockers"].append("Saved replay source does not match the reviewed bytes")
        for name, command in commands:
            report["checks"].append(check(name, command, directory))
        report["status"] = ("automated_checks_passed" if not report["blockers"]
                            and all(c["status"] == "passed" for c in report["checks"]) else "failed")
    with (directory / "report.json").open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(directory / "report.json")
    print(report["status"])
    return 0 if report["status"] in {"inventory_only", "automated_checks_passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
