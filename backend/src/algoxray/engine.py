from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import platform
import random
import sys
import time
from uuid import uuid4

from hypothesis import Phase, find, settings
from hypothesis.errors import NoSuchExample

from . import __version__
from .certificate import checked_example
from .generation import random_case, strategy_for
from .reduction import smaller_cases as _smaller_cases
from .hints import build_hints
from .paths import RESULTS
from .problems import (PROBLEMS, OracleDisagreement, check_output, complexity,
                       reference, size, validate_case)
from .runner import InvalidSubmission, Runner


class DiscoveryComplete(BaseException):
    pass


class BudgetStop(BaseException):
    pass


@dataclass
class Options:
    seed: int = 2026
    strategy: str = "hypothesis"
    max_examples: int = 100
    max_seconds: float = 10.0
    per_case_seconds: float = 1.0
    shrink: bool = True
    max_reduction_calls: int = 150
    reduction_seconds: float = 5.0
    include_trace: bool = True
    trace_limit: int = 2000
    replay_count: int = 3

    def __post_init__(self):
        if self.strategy not in ("hypothesis", "random"):
            raise ValueError("Unknown generation strategy")
        for field, lo, hi in (("seed", 0, 2**32 - 1), ("max_examples", 1, 500),
                              ("max_reduction_calls", 1, 500), ("trace_limit", 1, 2000), ("replay_count", 2, 5)):
            val = getattr(self, field)
            if type(val) is not int or not lo <= val <= hi:
                raise ValueError("Invalid option: " + field)
        for field, lo, hi in (("max_seconds", 0.05, 30), ("reduction_seconds", 0.05, 10), ("per_case_seconds", 0.01, 3)):
            val = getattr(self, field)
            if type(val) not in (int, float) or not lo <= val <= hi:
                raise ValueError("Invalid option: " + field)
        if type(self.shrink) is not bool or type(self.include_trace) is not bool:
            raise ValueError("Boolean options required")


def _fingerprint(result, failure):
    return json.dumps({"failure": failure, "output": result.get("output"),
                       "exception": result.get("exception_type"), "exception_line": result.get("exception_line")}, sort_keys=True, allow_nan=False)



def validate_bundle(bundle):
    if bundle["schema_version"] != 1 or len(bundle["submission"]["source_sha256"]) != 64:
        raise ValueError("Invalid source identity")
    if hashlib.sha256(bundle["submission"]["source"].encode("utf-8")).hexdigest() != bundle["submission"]["source_sha256"]:
        raise ValueError("Source text does not match its SHA256")
    events = {e["event_id"] for e in bundle["events"]}
    if len(events) != len(bundle["events"]):
        raise ValueError("Duplicate event identity")
    claims = {c["claim_id"] for c in bundle["claims"]}
    if len(claims) != len(bundle["claims"]):
        raise ValueError("Duplicate claim identity")
    for claim in bundle["claims"]:
        if not set(claim["event_ids"]) <= events:
            raise ValueError("Claim refers to a missing event")
        if any(ref not in bundle for ref in claim["evidence_refs"]):
            raise ValueError("Claim refers to missing evidence")
    for hint in bundle["hints"]:
        if not set(hint["claim_ids"]) <= claims or not set(hint.get("event_ids", [])) <= events:
            raise ValueError("Hint refers to missing evidence")
    if bundle["status"] == "witness_found":
        verify = bundle["verification"]
        if not verify["input_valid"] or verify["replay_matches"] != verify["replay_attempts"] or verify["replay_attempts"] < 2:
            raise ValueError("Unverified witness")
    if bundle["evidence_level"] == "E3" and (bundle["trace_status"] != "complete" or not events):
        raise ValueError("E3 requires recorded execution")
    json.dumps(bundle, allow_nan=False)
    return bundle


def analyze(submission, options=None, case=None, persist=True):
    options = options or Options()
    problem_id = submission.problem_id
    if problem_id not in PROBLEMS:
        raise ValueError("Unknown problem")
    if case is not None:
        case = validate_case(problem_id, case)
    started = time.perf_counter()
    stats = {"discovery_candidates": 0, "post_discovery_candidates": 0, "verification_solver_calls": 0,
             "replay_solver_calls": 0, "trace_solver_calls": 0, "flaky_candidates": 0,
             "discovery_ms": None, "post_discovery_ms": 0.0}
    first = best = manual_check = None
    attempts = []
    stop_reason = "search_exhausted"
    error = None
    status = "inconclusive"
    target_signature = None
    first_at = None
    rng = random.Random(options.seed)
    with Runner(submission, options.per_case_seconds) as runner:
        def evaluate(candidate, phase):
            nonlocal first, best, first_at, target_signature, manual_check
            now = time.perf_counter()
            if first is None:
                if stats["discovery_candidates"] >= options.max_examples or now - started >= options.max_seconds:
                    raise BudgetStop()
                stats["discovery_candidates"] += 1
            else:
                if stats["post_discovery_candidates"] >= options.max_reduction_calls or now - first_at >= options.reduction_seconds:
                    raise BudgetStop()
                stats["post_discovery_candidates"] += 1
            candidate = validate_case(problem_id, candidate)
            expected = reference(problem_id, candidate)
            result = runner.run(candidate)
            failure = result["status"] if result["status"] != "ok" else check_output(problem_id, candidate, result.get("output"), expected)
            attempts.append({"phase": phase, "case": candidate, "status": failure or "pass",
                             "elapsed_ms": result["elapsed_ms"]})
            if phase == "manual":
                manual_check = {"case": deepcopy(candidate), "status": failure or "pass",
                                "observed": result.get("output"), "expected": expected}
            if not failure:
                return False
            signature = (failure, result.get("exception_type") if failure == "exception" else None)
            if target_signature is not None and signature != target_signature:
                return False
            fingerprint = _fingerprint(result, failure)
            for _ in range(options.replay_count - 1):
                repeated = runner.run(candidate)
                stats["verification_solver_calls"] += 1
                repeated_failure = repeated["status"] if repeated["status"] != "ok" else check_output(problem_id, candidate, repeated.get("output"), expected)
                if _fingerprint(repeated, repeated_failure) != fingerprint:
                    stats["flaky_candidates"] += 1
                    return False
            record = {"case": deepcopy(candidate), "result": result, "expected": expected,
                      "failure": failure, "signature": signature, "fingerprint": fingerprint}
            if first is None:
                first = best = record
                first_at = time.perf_counter()
                stats["discovery_ms"] = round((first_at - started) * 1000, 4)
                target_signature = signature
                if not options.shrink and case is None:
                    raise DiscoveryComplete()
            elif complexity(problem_id, candidate) < complexity(problem_id, best["case"]):
                best = record
            return True

        try:
            if case is not None:
                evaluate(case, "manual")
                stop_reason = "manual_case_checked"
            elif options.strategy == "hypothesis":
                phases = [Phase.generate] + ([Phase.shrink] if options.shrink else [])
                try:
                    find(strategy_for(problem_id), lambda c: evaluate(c, "discovery" if first is None else "reduction"),
                         settings=settings(max_examples=options.max_examples, database=None, deadline=None,
                                           phases=phases, report_multiple_bugs=False), random=rng)
                except NoSuchExample:
                    pass
            else:
                while first is None:
                    evaluate(random_case(problem_id, rng), "discovery")
            if first and options.shrink and (options.strategy == "random" or case is not None):
                while True:
                    previous = complexity(problem_id, best["case"])
                    for candidate in _smaller_cases(problem_id, best["case"]):
                        if complexity(problem_id, candidate) < complexity(problem_id, best["case"]):
                            evaluate(candidate, "reduction")
                            if complexity(problem_id, best["case"]) < previous:
                                break
                    if complexity(problem_id, best["case"]) == previous:
                        break
        except DiscoveryComplete:
            stop_reason = "first_verified_witness"
        except BudgetStop:
            stop_reason = "reduction_budget_exhausted" if first else "discovery_budget_exhausted"
        except OracleDisagreement as exc:
            status, error = "oracle_disagreement", str(exc)
            best = None
        except InvalidSubmission as exc:
            status, error = "invalid_submission", str(exc)
            best = None
        if first_at is not None:
            stats["post_discovery_ms"] = round((time.perf_counter() - first_at) * 1000, 4)
        trace = {"events": [], "trace_status": "not_run"}
        replay_matches = 0
        replay_started = time.perf_counter()
        if best:
            for _ in range(options.replay_count):
                repeated = runner.run(best["case"])
                stats["replay_solver_calls"] += 1
                repeated_failure = repeated["status"] if repeated["status"] != "ok" else check_output(problem_id, best["case"], repeated.get("output"), best["expected"])
                replay_matches += _fingerprint(repeated, repeated_failure) == best["fingerprint"]
            stats["replay_ms"] = round((time.perf_counter() - replay_started) * 1000, 4)
            if replay_matches != options.replay_count:
                best = None
                stop_reason = "unstable_replay"
            else:
                status = "witness_found"
                if options.include_trace:
                    trace_started = time.perf_counter()
                    trace = runner.run(best["case"], trace=True, trace_limit=options.trace_limit)
                    stats["trace_solver_calls"] += 1
                    stats["trace_ms"] = round((time.perf_counter() - trace_started) * 1000, 4)
                    traced_failure = trace["status"] if trace["status"] != "ok" else check_output(problem_id, best["case"], trace.get("output"), best["expected"])
                    if _fingerprint(trace, traced_failure) != best["fingerprint"]:
                        trace = {"events": [], "trace_status": "failed"}
        stats.setdefault("replay_ms", 0.0)
        stats.setdefault("trace_ms", 0.0)
        stats.update({"total_solver_calls": runner.calls, "worker_startups": runner.startups,
                      "elapsed_ms": round((time.perf_counter() - started) * 1000, 4)})
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:10]
    bundle = {
        "schema_version": 1, "run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(),
        "problem_id": problem_id, "status": status, "failure_kind": best["failure"] if best else None,
        "execution_mode": "local_trusted", "seed": options.seed,
        "strategy": "manual" if case is not None else options.strategy, "options": asdict(options),
        "submission": {"fixture_id": submission.fixture_id, "source_sha256": submission.sha256,
                       "source": submission.source, "origin": submission.origin, "split": submission.split,
                       "adapter_id": submission.adapter, "filename": submission.path.name},
        "case": best["case"] if best else None, "original_case": first["case"] if first else None,
        "observed_output": best["result"].get("output") if best else None,
        "expected_output": best["expected"] if best else None,
        "exception": {"type": best["result"].get("exception_type"), "message": best["result"].get("message"),
                      "line": best["result"].get("exception_line"), "function": best["result"].get("exception_function")} if best else None,
        "evidence_level": "E2" if best else "E0", "trace_status": trace["trace_status"],
        "events": trace.get("events", []), "claims": [], "hints": [],
        "verification": {"input_valid": best is not None, "oracle_id": "networkx_bellman_ford+independent_floyd" if problem_id == "dijkstra_v1" else "linear_membership_checker",
                         "replay_attempts": stats["replay_solver_calls"], "replay_matches": replay_matches},
        "reduction": {"before": size(problem_id, first["case"]) if first else None,
                      "after": size(problem_id, best["case"]) if best else None,
                      "failure_preserved": best is not None,
                      "method": ("hypothesis" if options.strategy == "hypothesis" and case is None else "greedy_structure") if options.shrink else "disabled"},
        "statistics": stats, "attempts": attempts, "stop_reason": stop_reason, "error": error,
        "versions": {"algoxray": __version__, "python": sys.version.split()[0], "platform": platform.platform(),
                     "hypothesis": version("hypothesis"), "networkx": version("networkx")},
    }
    bundle["manual_check"] = manual_check
    bundle["witness_explanation"] = (checked_example(problem_id, best["case"], best["result"]["output"], best["expected"])
                                     if best and best["failure"] == "wrong_answer" else None)
    bundle["claims"], bundle["hints"] = build_hints(bundle, submission)
    if any(c["kind"] == "source_specific_observation" for c in bundle["claims"]):
        bundle["evidence_level"] = "E3"
    bundle["diagnostic_status"] = "supported" if bundle["evidence_level"] == "E3" else "abstained"
    observation = next((claim for claim in bundle["claims"] if claim["kind"] == "source_specific_observation"), None)
    bundle["diagnosis"] = {"status": "supported" if observation else "witness_only" if best else "unavailable",
                           "text": observation["text"] if observation else None,
                           "event_ids": observation["event_ids"] if observation else [],
                           "source_lines": observation.get("source_lines", []) if observation else [],
                           "trace_roles": observation.get("trace_roles") if observation else None}
    validate_bundle(bundle)
    if persist:
        directory = RESULTS / "runs" / run_id
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "evidence.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        (directory / "submission.py").write_bytes(submission.source.encode("utf-8"))
    return bundle
