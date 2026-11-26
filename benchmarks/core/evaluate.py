"""Frozen, paired discovery and separate end-to-end audit on uncatalogued sources."""
import argparse
import csv
import gzip
import hashlib
import json
import platform
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))
from algoxray import __version__
from algoxray.engine import Options, analyze, validate_bundle
from algoxray.problems import validate_case
from algoxray.registry import local_submission


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def code_identity():
    patterns = ["backend/src/algoxray/*.py", "backend/pyproject.toml", "requirements.lock.txt",
                "web/*.html", "web/static/**/*.js", "web/static/**/*.css", "contracts/*.json",
                "fixtures/catalog.json", "fixtures/**/*.py", "benchmarks/core/protocol.json", "benchmarks/core/evaluate.py"]
    files = {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for pattern in patterns for p in ROOT.glob(pattern)}
    return files, digest(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())


def csv_write(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = dict.fromkeys(k for row in rows for k in row)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(keys))
        writer.writeheader()
        writer.writerows(rows)


def independent_truth(problem, case):
    if problem == "binary_search_v1":
        return [i for i, value in enumerate(case["array"]) if value == case["target"]]
    # Enumerate simple paths. Independent of both distance routines and the certificate constructor.
    best = [None] * case["n"]
    todo = [(case["source"], 0, {case["source"]})]
    while todo:
        u, cost, used = todo.pop()
        if best[u] is None or cost < best[u]:
            best[u] = cost
        for a, b, weight in case["edges"]:
            if a == u and b not in used:
                todo.append((b, cost + weight, used | {b}))
    return best


def audit(bundle):
    problem, case = bundle["problem_id"], bundle["case"]
    truth = independent_truth(problem, case)
    actual, kind = bundle["observed_output"], bundle["failure_kind"]
    binary = problem == "binary_search_v1"
    lines = bundle["submission"]["source"].splitlines()
    events = {e["event_id"]: e for e in bundle["events"]}
    check = validate_case(problem, case) == case and digest(bundle["submission"]["source"].encode()) == bundle["submission"]["source_sha256"]
    check &= all(1 <= event["line"] <= len(lines) for event in events.values())
    check &= (bundle["expected_output"] == (truth[0] if truth else -1)) if binary else (bundle["expected_output"] == truth)
    proof = bundle["witness_explanation"]
    proof_ok = True
    if kind == "wrong_answer":
        if binary:
            proof_ok = (proof["matching_indices"] == truth and proof["target"] == case["target"]
                        and proof["returned"] == actual and actual not in (truth or [-1])
                        and proof["returned_value"] == (case["array"][actual] if 0 <= actual < len(case["array"]) else None))
        elif proof["kind"] == "shortest_path":
            vertices, weights = proof["vertices"], proof["weights"]
            edges = {(u, v): w for u, v, w in case["edges"]}
            proof_ok = (vertices[0] == case["source"] and vertices[-1] == proof["target"]
                        and [edges.get((u,v)) for u,v in zip(vertices,vertices[1:])] == weights
                        and sum(weights) == truth[proof["target"]] == proof["cost"] and proof["returned"] != proof["cost"])
        else:
            proof_ok = (truth[proof["target"]] is None and actual[proof["target"]] is not None
                        and proof["reachable_vertices"] == [i for i,v in enumerate(truth) if v is not None])
    rows = []
    for claim in bundle["claims"]:
        linked = [events[i] for i in claim["event_ids"]]
        rule = claim.get("adapter_id")
        ok, reason = check, "source identity, legal input, independent answer and replayed failure kind"
        if not rule:
            ok &= (proof_ok if kind == "wrong_answer" else bool(bundle["verification"]["replay_matches"] == 3))
        elif rule == "python_exception_location_v1":
            error = bundle["exception"]
            ok &= len(linked) == 1 and (linked[0]["kind"], linked[0]["line"], linked[0]["function"], linked[0].get("exception_type")) == ("exception", error["line"], error["function"], error["type"])
            reason = "escaping exception type, traceback function and line match the traced event"
        elif rule == "python_returned_index_v1":
            e = linked[-1]
            ok &= proof_ok and e["kind"] == "return" and e["return_value"] == actual and actual not in (truth or [-1]) and e["line"] in claim["source_lines"]
            reason = "actual solve return event and external membership test disagree on the returned index"
        elif rule == "python_closed_interval_ast_v1":
            a, b = linked
            roles = claim["trace_roles"]
            lo, hi = (b["locals"][roles[k]] for k in ["lower", "upper"])
            ok &= (a["locals"][roles["lower"]] == lo == hi == a["locals"][roles["upper"]] and lo in truth
                   and actual == -1 and [a["line"], b["line"]] == claim["source_lines"]
                   and events[list(events)[-1]].get("return_value") == -1)
            reason = "consecutive recorded condition/return, equal bounds, independently enumerated match, actual -1"
        else:
            ok, reason = None, "unmapped diagnostic rule"
        rows.append({"run_id": bundle["run_id"], "source_sha256": bundle["submission"]["source_sha256"],
                     "claim": claim["claim_id"], "rule": rule or kind, "text": claim["text"],
                     "events": "|".join(claim["event_ids"]), "source_lines": str(claim.get("source_lines",[])),
                     "verdict": "verified" if ok else "unclear" if ok is None else "unsupported", "reason": reason})
    return rows, bool(check), bool(proof_ok)


def distribution(values):
    if not values:
        return None
    values = sorted(values)
    quartiles = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 1 else values * 3
    return {"n": len(values), "p25": quartiles[0], "median": statistics.median(values), "p75": quartiles[2],
            "min": values[0], "max": values[-1]}


def run(out, policy, frozen):
    if (out/"runs.csv").exists() or (out/"raw").exists():
        raise SystemExit("Choose a fresh output directory and freeze it first")
    manifest = json.loads((HERE/"manifest.json").read_text(encoding="utf-8"))
    write(out/"corpus.json",manifest)
    for item in manifest:
        if digest((HERE/item["file"]).read_bytes()) != item["sha256"]:
            raise ValueError("Source changed: "+item["id"])
    (out/"raw").mkdir()
    records, claims = [], []
    eligible = [i for i in manifest if i["label"] in {"buggy","correct"}]
    for phase in ["discovery", "audit"]:
        seeds = policy["seeds"] if phase == "discovery" else policy["audit_seeds"]
        for item in eligible:
            sub = local_submission(item["problem"], HERE/item["file"])
            for index, seed in enumerate(seeds):
                strategies = policy["strategies"][::1 if index % 2 == 0 else -1]
                for strategy in strategies:
                    full = phase == "audit"
                    opts = Options(strategy=strategy, seed=seed, max_examples=policy["max_examples"],
                                   max_seconds=policy["max_seconds"], per_case_seconds=policy["per_case_seconds"],
                                   replay_count=policy["replay_count"], shrink=full, include_trace=full,
                                   reduction_seconds=policy["reduction_seconds"], max_reduction_calls=policy["max_reduction_calls"])
                    name = f"{phase}-{item['id']}-{seed}-{strategy}.json.gz"
                    row = dict(phase=phase, program=item["id"], problem_id=item["problem"], label=item["label"],
                               source_sha256=sub.sha256, strategy=strategy, seed=seed, raw_file="raw/"+name)
                    try:
                        b = analyze(sub, opts, persist=False)
                        validate_bundle(b)
                        st = b["statistics"]
                        row.update(run_id=b["run_id"], status=b["status"], kind=b["failure_kind"], trace=b["trace_status"],
                                   specific=b["diagnostic_status"]=="supported", before=json.dumps(b["reduction"]["before"]),
                                   after=json.dumps(b["reduction"]["after"]), **st, **b["verification"])
                        if full and b["status"] == "witness_found":
                            checks, trace_ok, proof_ok = audit(b)
                            claims.extend(dict(program=item["id"], **c) for c in checks)
                            row.update(trace_ok=trace_ok, proof_ok=proof_ok, has_proof=bool(b["witness_explanation"]),
                                       abstention="" if row["specific"] else ("trace_"+b["trace_status"] if b["trace_status"]!="complete" else "no_supported_pattern"))
                    except Exception as exc:
                        row.update(status="internal_error",error=f"{type(exc).__name__}: {exc}")
                        b={"error":row["error"],"record":row}
                    with gzip.open(out/"raw"/name,"wt",encoding="utf-8") as fp:
                        json.dump(b,fp,ensure_ascii=False,separators=(",",":"),allow_nan=False)
                    records.append(row)
            print(f"{phase} {item['id']} {len(records)}",flush=True)
    csv_write(out/"runs.csv",records)
    csv_write(out/"claims.csv",claims)
    discoveries = [r for r in records if r["phase"]=="discovery"]
    audits = [r for r in records if r["phase"]=="audit"]
    witnesses = [r for r in audits if r["status"]=="witness_found"]
    groups = []
    for prob in sorted({r["problem_id"] for r in records}):
        for strat in policy["strategies"]:
            group = [r for r in discoveries if (r["problem_id"],r["strategy"])==(prob,strat)]
            buggy = [r for r in group if r["label"]=="buggy"]
            control = [r for r in group if r["label"]=="correct"]
            found = [r for r in buggy if r["status"]=="witness_found"]
            times = distribution([r["discovery_ms"] for r in found])
            groups.append(dict(problem_id=prob,strategy=strat,buggy_found=len(found),buggy_runs=len(buggy),
                               control_accusations=sum(r["status"]=="witness_found" for r in control),control_runs=len(control),
                               median_discovery_ms=times["median"] if times else None,discovery_ms=times,
                               statuses=dict(Counter(r["status"] for r in group)),kinds=dict(Counter(r["kind"] for r in found))))
    prs=[]
    for item in eligible:
        group=[r for r in discoveries if r["program"]==item["id"]]
        w=[r for r in witnesses if r["program"]==item["id"]]
        prs.append(dict(id=item["id"],label=item["label"],trials=len(group),found=sum(r["status"]=="witness_found" for r in group),
                        audit_witnesses=len(w),specific=sum(r["specific"] for r in w)))
    summary=dict(release=__version__,status="measured",created_at=datetime.now(timezone.utc).isoformat(),
                 total_runs=len(discoveries),fixture_count=len(eligible),codebase_sha256=frozen["sha256"],
                 environment=frozen["environment"], rows=groups,programs=prs,errors=sum(r["status"]=="internal_error" for r in records),
                 audit=dict(runs=len(audits),witnesses=len(witnesses),specific=sum(r["specific"] for r in witnesses),
                            abstained=sum(not r["specific"] for r in witnesses),reason_counts=dict(Counter(r["abstention"] for r in witnesses if r["abstention"])),
                            replay_matches=sum(r["replay_matches"] for r in witnesses),replay_attempts=sum(r["replay_attempts"] for r in witnesses),
                            sizes_reduced=sum(r["before"]!=r["after"] for r in witnesses),
                            trace_valid=sum(r["trace_ok"] for r in witnesses),certificates=sum(r["has_proof"] for r in witnesses),
                            certificates_verified=sum(r["has_proof"] and r["proof_ok"] for r in witnesses),
                            claims=dict(Counter(c["verdict"] for c in claims)),rules=dict(Counter(c["rule"] for c in claims if c["claim"]!="C1")),
                            trace_status=dict(Counter(r["trace"] for r in witnesses))))
    write(out/"summary.json",summary)


def main():
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument("action",choices=["freeze","run"])
    args.add_argument("--out",type=Path,required=True)
    a=args.parse_args()
    p=HERE/"protocol.json"
    files,sha=code_identity()
    if a.action=="freeze":
        a.out.mkdir(parents=True,exist_ok=False)
        write(a.out/"freeze.json",{"timestamp":datetime.now(timezone.utc).isoformat(),"sha256":sha,"files":files,
              "environment":{"python":platform.python_version(),"platform":platform.platform(),"processor":platform.processor(),
                             "hypothesis":version("hypothesis"),"networkx":version("networkx")},"protocol_sha256":digest(p.read_bytes())})
        (a.out/"protocol.json").write_bytes(p.read_bytes())
        print(sha)
        return
    frozen=json.loads((a.out/"freeze.json").read_text(encoding="utf-8"))
    if frozen["sha256"]!=sha or frozen["protocol_sha256"]!=digest(p.read_bytes()):
        raise SystemExit("Measured source/protocol differs from freeze")
    run(a.out,json.loads(p.read_text(encoding="utf-8")),frozen)

if __name__=="__main__":
    main()
