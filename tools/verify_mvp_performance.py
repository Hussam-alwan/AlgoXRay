"""Repeat the public development measurements on fixed, trusted fixtures."""

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from algoxray.v4_isolation import GUEST, execute_stdio
from algoxray.v4_observation import benchmark_source, generated_size_inputs


MANIFEST = {
    "id": "performance_pilot",
    "title": "Repeated sum",
    "statement": "Read n and m. Print the sum of n by n copies of m.",
    "fields": [
        {"name": "n", "kind": "int", "min": 1, "max": 2048},
        {"name": "m", "kind": "int", "min": 7, "max": 7},
    ],
    "lines": [["n", "m"]],
    "output": "tokens",
}
READ = "n, m = map(int, input().split())\n"
REFERENCE = READ + "print(n ** 2 * m)\n"
LINEAR = READ + "total = 0\nfor _ in range(n):\n    total += n * m\nprint(total)\n"
QUADRATIC = READ + "total = 0\nfor _ in range(n):\n    for _ in range(n):\n        total += m\nprint(total)\n"
PACKAGE = {
    "manifest": MANIFEST,
    "reference": REFERENCE,
    "controls": [
        {"case": {"n": 1, "m": 7}, "expected": "7"},
        {"case": {"n": 2, "m": 7}, "expected": "28"},
    ],
}
SIZES = [128, 256, 512, 1024, 2048]


def trusted_fixture_worker(source, stdin, *, seconds, trace_limit, mode, cancel=None):
    if source not in (REFERENCE, LINEAR, QUADRATIC):
        raise ValueError("The subprocess runner accepts only the built-in fixture programs")
    request = {"source": source, "stdin": stdin, "seconds": seconds, "trace_limit": trace_limit, "mode": mode}
    started = time.monotonic()
    output = subprocess.check_output(
        [sys.executable, "-I", "-B", "-c", GUEST],
        input=(json.dumps(request) + "\n").encode(),
        timeout=seconds + 8,
    )
    return {**json.loads(output), "elapsed_ms": (time.monotonic() - started) * 1000}


def measure(run, environment):
    inputs = generated_size_inputs(MANIFEST, "n", SIZES, seed=2026)
    curves = {}
    for name, source in (("linear", LINEAR), ("quadratic", QUADRATIC)):
        result = benchmark_source(source, inputs, repeats=5, seconds=2, package=PACKAGE, size_field="n", run=run)
        ledger = result.pop("run_report")
        result["worker_images"] = ledger["image_ids"]
        result["engine_source_files_sha256"] = ledger["engine_source_files_sha256"]
        curves[name] = result
    profile_input = inputs[0]["stdin"]
    plain = run(QUADRATIC, profile_input, seconds=2, trace_limit=0, mode="benchmark_uninstrumented")
    traced = run(QUADRATIC, profile_input, seconds=2, trace_limit=128, mode="trace_profile")
    output_matches = plain["status"] == traced["status"] == "ok" and plain["stdout"] == traced["stdout"]
    for observation in (plain, traced):
        observation["event_count"] = len(observation.pop("events", ()))
    return {
        "environment": environment,
        "host_python": platform.python_version(),
        "host_platform": platform.platform(),
        "protocol": "Fresh worker each call, n varies, m=7, 5 repetitions per point, wall and CPU inside the worker.",
        "scope": "Public development fixture, finite-range timing, no research or platform-runtime claim.",
        "curves": curves,
        "profiling_comparison": {"same_stdout": output_matches, "plain": plain, "traced": traced},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--trusted-fixture-subprocess", action="store_true")
    args = parser.parse_args()
    run = trusted_fixture_worker if args.trusted_fixture_subprocess else execute_stdio
    environment = "trusted_fixtures_cpython_subprocess" if args.trusted_fixture_subprocess else "docker"
    report = measure(run, environment)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name, curve in report["curves"].items():
        print(name, [(p["size"], p["summary"]["completed"], p["summary"]["wall_ns"]) for p in curve["points"]], curve["growth"])
    print("Profile/stdout agreement:", report["profiling_comparison"]["same_stdout"])
    if not report["profiling_comparison"]["same_stdout"] or any(
        len(curve["points"]) != len(SIZES) or any(
            p["summary"]["completed"] != 5 or p["correctness"] != "recorded_match" for p in curve["points"]
        ) for curve in report["curves"].values()
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
