"""Exercise the paired evaluation on the public development catalog."""

import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys

from algoxray.v4_contracts import complexity, equal, serialize
from algoxray.v4_engine import analyze_package
from algoxray.v4_isolation import configured_image
from check_inventory import ROOT, check_inventory


BASELINE = "333cf3d1b4c1015f836a14b4304a3a4aedae1abb"
SEED = 2026
REDUCTION_CALLS = 6
CATALOG = "web/static/v4-demos.json"
AUTHORED_DEFECTS = {
    "sum": "sum(a[:-1])",
    "count": "s.count('B')",
    "matrix": "sum(row[:-1])",
    "reachability": "range(n-1)",
}

# A separate interpreter loads the pinned baseline package before any newer module.
BASELINE_RUNNER = """
import json, sys
sys.path.insert(0, sys.argv[1])
from algoxray.v4_engine import analyze_package
from algoxray.v4_isolation import execute_stdio
payload = json.loads(sys.stdin.buffer.read())
worker_calls = 0
def run(*args, **kwargs):
    global worker_calls
    worker_calls += 1
    return execute_stdio(*args, **kwargs)
result = analyze_package(**payload, run=run)
result["executions"] = worker_calls
sys.stdout.buffer.write(json.dumps(result, ensure_ascii=True).encode("utf-8"))
"""


def verify_baseline(checkout):
    head = subprocess.check_output(["git", "-C", checkout, "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(
        ["git", "-C", checkout, "status", "--porcelain", "--untracked-files=all", "--", "backend/src"],
        text=True,
    )
    if head != BASELINE or status.strip():
        raise ValueError("Use the pinned V4 baseline with an unchanged backend source tree")


def run_baseline(checkout, payload):
    worker = subprocess.run(
        [sys.executable, "-I", "-c", BASELINE_RUNNER, str(checkout / "backend/src")],
        input=json.dumps(payload).encode("utf-8"), capture_output=True, timeout=240, check=True,
    )
    return json.loads(worker.stdout)


def reduction_result(manifest, result):
    witness = result.get("witness")
    common = {key: result.get(key) for key in ("status", "kind", "replay_count", "elapsed_ms", "attempts", "executions")}
    report = result.get("run_report", {})
    workers = report.get("workers")
    common["reduction_pipeline_worker_calls"] = (
        sum(row["stage"] in {"search", "shrink", "replay"} for row in workers)
        if workers is not None else result["executions"]
    )
    if witness is None:
        return common
    case = witness["case"]
    if serialize(manifest, case) != witness["stdin"]:
        raise AssertionError("Returned witness does not match its legal serialization")
    return {**common, "case": case, "complexity": complexity(manifest, case),
            "expected": witness["reference"]["stdout"], "actual": witness["student"].get("stdout"),
            "stop_reason": result.get("reduction", {}).get("stop_reason")}


def localization_result(ranked, target):
    lines = [candidate["line"] for candidate in ranked]
    return {"status": "ranked" if lines else "abstained", "lines": lines,
            "top_1": target in lines[:1], "top_3": target in lines[:3]}


def pilot(checkout):
    verify_baseline(checkout)
    inventory = json.loads(Path(__file__).with_name("development-inventory.json").read_text(encoding="utf-8"))
    check_inventory(inventory)
    catalog = json.loads((ROOT / CATALOG).read_text(encoding="utf-8"))
    cases = []
    for demo_id, marker in AUTHORED_DEFECTS.items():
        demo = catalog[demo_id]
        package = demo["package"]
        manifest = package["manifest"]
        source = demo["mutant"]
        control = package["controls"][0]
        payload = {"p": package, "source": source, "case": control["case"], "seed": SEED}
        # Freeze the starting witness. Both ranking methods see the same MVP spectrum.
        original = analyze_package(**payload, reduce_calls=0, spectrum=True)
        if original["status"] != "observed_mismatch" or original["kind"] != "wrong_answer":
            raise RuntimeError(f"Expected a replayed wrong answer on the authored development witness: {demo_id}")
        if not equal(manifest, original["witness"]["reference"]["stdout"], control["expected"]):
            raise RuntimeError(f"Authored control output disagrees with the reference: {demo_id}")

        target, = [line for line, text in enumerate(source.splitlines(), 1) if marker in text]
        v4 = run_baseline(checkout, {**payload, "reduce_calls": REDUCTION_CALLS})
        candidate = analyze_package(**payload, reduce_calls=REDUCTION_CALLS)
        cases.append({
            "id": demo_id, "problem_id": manifest["id"], "authored_defect_line": target,
            "reduction": {name: reduction_result(manifest, record) for name, record in
                          (("no_reduction", original), ("v4", v4), ("mvp", candidate))},
            "localization": {
                "spectrum_status": original["suspiciousness"]["status"],
                "passing_traces": original["suspiciousness"].get("passing_count", 0),
                "failing_traces": original["suspiciousness"].get("failing_count", 0),
                "additional_worker_calls": sum(row["stage"] == "spectrum" for row in original["run_report"]["workers"]),
                "ochiai": localization_result(original["suspiciousness"]["ranked"], target),
                "with_structural_evidence": localization_result(original["evidence_localization"]["ranked"], target),
            },
        })
    return {
        "scope": "Public authored development cases only. Not a blinded evaluation or a user study.",
        "catalog_release_commit": inventory["release_commit"], "v4_baseline_commit": BASELINE,
        "host_python": platform.python_version(), "host_platform": platform.platform(),
        "worker_image": configured_image(), "seed": SEED, "reduction_budget_per_arm": REDUCTION_CALLS,
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = pilot(args.baseline.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(report["cases"]), "output": str(args.out), "scope": report["scope"]}))


if __name__ == "__main__":
    main()
