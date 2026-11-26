"""Re-run the exact checked input and reviewed source saved in a witness bundle."""
from pathlib import Path
from tempfile import TemporaryDirectory

from .engine import Options, analyze, validate_bundle
from .registry import get_submission, local_submission


def replay_witness(bundle):
    validate_bundle(bundle)
    if bundle["status"] != "witness_found":
        raise ValueError("This bundle has no verified witness to replay")
    identity = bundle["submission"]
    options = Options(seed=bundle["seed"], per_case_seconds=bundle["options"]["per_case_seconds"],
                      replay_count=bundle["options"]["replay_count"], shrink=False, include_trace=True,
                      fresh_process=bundle["options"].get("fresh_process",False))
    with TemporaryDirectory(prefix="algoxray_replay_") as temp:
        candidate = None
        if identity["origin"] != "reviewed_local_file":
            try:
                candidate = get_submission(identity["fixture_id"])
            except ValueError:
                pass
        if candidate is None or candidate.sha256 != identity["source_sha256"]:
            path = Path(temp) / "submission.py"
            path.write_bytes(identity["source"].encode("utf-8"))
            candidate = local_submission(bundle["problem_id"], path)
        if candidate.problem_id != bundle["problem_id"]:
            raise ValueError("Fixture/problem mismatch")
        rerun = analyze(candidate, options, case=bundle["case"], persist=False)
    fields = ("status", "failure_kind", "case", "observed_output", "expected_output")
    same = all(bundle[key] == rerun[key] for key in fields)
    for key in ("type", "line", "function"):
        same = same and (bundle.get("exception") or {}).get(key) == (rerun.get("exception") or {}).get(key)
    return {"matched": same, "original_run": bundle["run_id"], "replay_run": rerun["run_id"],
            "source_sha256": candidate.sha256, "case": rerun["case"], "verification": rerun["verification"]}
