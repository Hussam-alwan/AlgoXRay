"""Automated evidence-predicate checks, not an independent human hint study."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))
from algoxray.engine import Options, analyze, validate_bundle
from algoxray.problems import check_output
from algoxray.registry import get_submission


def audit_claim(claim, bundle):
    if claim["kind"] == "wrong_answer":
        return check_output(bundle["problem_id"], bundle["case"], bundle["observed_output"], bundle["expected_output"]) == "wrong_answer"
    if claim["kind"] != "source_specific_observation":
        return False
    if bundle["submission"]["adapter_id"] != claim["adapter_id"]:
        return False
    for event in bundle["events"]:
        if event["event_id"] not in claim["event_ids"]:
            continue
        loc = event["locals"]
        if claim["adapter_id"] == "dijkstra_seen_v1":
            return (loc["v"] in loc["seen"] and loc["d"] + loc["w"] < loc["dist"][loc["v"]]
                    and bundle["submission"]["source"].splitlines()[event["line"] - 1].strip() == "continue")
        if claim["adapter_id"] == "binary_last_v1":
            return (loc["lo"] == loc["hi"] and 0 <= loc["lo"] < len(loc["arr"])
                    and loc["arr"][loc["lo"]] == loc["target"] and bundle["observed_output"] == -1
                    and bundle["submission"]["source"].splitlines()[event["line"] - 1].strip() == "return -1")
    return False


def run():
    directory = ROOT / "results/evidence-audit"
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for fixture_id in ("dijkstra_premature_visited", "binary_missing_last"):
        for seed in range(2026, 2036):
            bundle = analyze(get_submission(fixture_id), Options(seed=seed), persist=False)
            validate_bundle(bundle)
            path = directory / f"{fixture_id}_{seed}.json"
            path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
            checks = [{"claim_id": c["claim_id"], "supported_by_predicate": audit_claim(c, bundle)} for c in bundle["claims"]]
            records.append({"fixture_id": fixture_id, "seed": seed, "status": bundle["status"],
                            "trace_status": bundle["trace_status"], "diagnostic_status": bundle["diagnostic_status"],
                            "before": bundle["reduction"]["before"], "after": bundle["reduction"]["after"],
                            "replay_matches": bundle["verification"]["replay_matches"],
                            "replay_attempts": bundle["verification"]["replay_attempts"], "checks": checks,
                            "raw_file": str(path.relative_to(ROOT))})
            print(f"audit {len(records)}/20", flush=True)
    claims = [check for record in records for check in record["checks"]]
    found = [r for r in records if r["status"] == "witness_found"]
    summary = {"created_at": datetime.now(timezone.utc).isoformat(), "runs": len(records),
               "witnesses": len(found), "claims_checked": len(claims),
               "claims_supported": sum(c["supported_by_predicate"] for c in claims),
               "diagnostic_runs": sum(r["diagnostic_status"] == "supported" for r in found),
               "complete_traces": sum(r["trace_status"] == "complete" for r in found),
               "replay_matches": sum(r["replay_matches"] for r in found),
               "replay_attempts": sum(r["replay_attempts"] for r in found),
               "method": "Automated consistency and arithmetic/source-predicate checks on two supported authored fixtures",
               "not_established": "Independent human factuality, general diagnosis accuracy, causality, or learning benefit",
               "records": records}
    (ROOT / "results/evidence-audit.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if summary["claims_supported"] != summary["claims_checked"]:
        raise AssertionError("An emitted claim failed its evidence predicate")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}))
    return summary


if __name__ == "__main__":
    run()
