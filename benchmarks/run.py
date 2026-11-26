"""Reproducible, finite fixture evaluation. No fabricated or imputed successes."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))
from algoxray.engine import Options, analyze, validate_bundle
from algoxray.registry import catalog, get_submission


def codebase_digest():
    sha = hashlib.sha256()
    files = list((ROOT / "backend/src").rglob("*.py")) + list((ROOT / "fixtures").rglob("*.py"))
    files += [ROOT / "fixtures/catalog.json", ROOT / "backend/pyproject.toml", Path(__file__),
              ROOT / "benchmarks/config.json", ROOT / "contracts/evidence.schema.json", ROOT / "requirements.lock.txt"]
    for file in sorted(files):
        sha.update(file.relative_to(ROOT).as_posix().encode())
        sha.update(file.read_bytes())
    return sha.hexdigest()


def run(config_path, output=None):
    config = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
    created = datetime.now(timezone.utc)
    run_name = created.strftime("%Y%m%dT%H%M%SZ")
    output = Path(output) if output else ROOT / "results/benchmarks" / run_name
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    meta = {x["id"]: x for x in catalog()}
    digest = codebase_digest()
    raw_rows = []
    total = len(config["fixtures"]) * len(config["seeds"]) * len(config["strategies"])
    for fixture_id in config["fixtures"]:
        sub = get_submission(fixture_id)
        for index, seed in enumerate(config["seeds"]):
            strategies = config["strategies"] if index % 2 == 0 else list(reversed(config["strategies"]))
            for strategy in strategies:
                options = Options(seed=seed, strategy=strategy, max_examples=config["max_examples"],
                                  max_seconds=config["max_seconds"], shrink=False, include_trace=False,
                                  replay_count=config["replay_count"])
                result = analyze(sub, options, persist=False)
                validate_bundle(result)
                filename = f"{fixture_id}_{seed}_{strategy}.json"
                (output / filename).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
                raw_rows.append({"fixture_id": fixture_id, "problem_id": sub.problem_id, "label": sub.label,
                                 "split": sub.split, "source_sha256": sub.sha256, "strategy": strategy, "seed": seed,
                                 "status": result["status"], "failure_kind": result["failure_kind"],
                                 "discovery_candidates": result["statistics"]["discovery_candidates"],
                                 "discovery_ms": result["statistics"]["discovery_ms"],
                                 "total_solver_calls": result["statistics"]["total_solver_calls"],
                                 "raw_file": filename})
                if len(raw_rows) % 20 == 0 or len(raw_rows) == total:
                    print(f"completed {len(raw_rows)}/{total}", flush=True)
    with (output / "runs.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(raw_rows[0]))
        writer.writeheader(); writer.writerows(raw_rows)
    groups = defaultdict(list)
    for row in raw_rows:
        groups[(row["problem_id"], row["strategy"])].append(row)
    rows = []
    for (problem_id, strategy), runs in sorted(groups.items()):
        eligible = [r for r in runs if r["status"] in ("witness_found", "inconclusive")]
        buggy = [r for r in eligible if r["label"] == "buggy"]
        control = [r for r in eligible if r["label"] == "control"]
        found = [r for r in buggy if r["status"] == "witness_found"]
        rows.append({"problem_id": problem_id, "strategy": strategy, "buggy_runs": len(buggy),
                     "buggy_found": len(found), "control_runs": len(control),
                     "control_accusations": sum(r["status"] == "witness_found" for r in control),
                     "censored_buggy_runs": len(buggy) - len(found), "excluded_runs": len(runs) - len(eligible),
                     "failure_kinds": dict(Counter(r["failure_kind"] for r in found)),
                     "median_discovery_ms": statistics.median(r["discovery_ms"] for r in found) if found else None,
                     "median_discovery_candidates": statistics.median(r["discovery_candidates"] for r in found) if found else None})
    summary = {"status": "completed", "created_at": created.isoformat(), "protocol_version": 1,
               "codebase_sha256": digest, "total_runs": len(raw_rows), "fixture_count": len(config["fixtures"]),
               "unique_source_files": len(config["fixtures"]), "seeds": config["seeds"],
               "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
               "fixture_manifest": [meta[i] for i in config["fixtures"]], "rows": rows,
               "scope": "Limited curated/authored fixtures; no blinded generalization or student-learning claim",
               "raw_directory": output.name, "discovery_only": True,
               "notes": config["notes"]}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "results/summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report = ["# AlgoX-Ray measured technical evaluation", "", f"Codebase SHA256: `{digest}`", "",
              f"{len(raw_rows)} actual runs; {len(config['fixtures'])} programs; {len(config['seeds'])} seeds per strategy.", "",
              "| Problem | Strategy | Buggy witnesses | False control accusations | Median discovered time (ms) |",
              "|---|---|---|---|---|"]
    for r in rows:
        median = f"{r['median_discovery_ms']:.2f}" if r["median_discovery_ms"] is not None else "Not discovered"
        report.append(f"| {r['problem_id']} | {r['strategy']} | {r['buggy_found']}/{r['buggy_runs']} | {r['control_accusations']}/{r['control_runs']} | {median} |")
    report += ["", "Timings include verification before the first confirmed witness. Medians exclude censored trials, which are counted separately in summary.json.",
               "No shrinking or tracing in this comparison. Random and Hypothesis use the same legal domain and budgets, but have different input distributions.",
               "Repeated seeds are not independent programs. All sources were reviewed; development/evaluation splits are bookkeeping, not a blinded holdout claim.",
               "These data do not establish educational benefit, general diagnosis accuracy, or a new test-generation algorithm.", ""]
    (ROOT / "docs/MEASURED_RESULTS.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"output": str(output), "total_runs": len(raw_rows), "rows": rows}), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "benchmarks/config.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run(args.config, args.output)
