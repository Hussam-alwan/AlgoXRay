"""Read-only post-run audit of the frozen Option B output. Writes a separate report."""
import argparse
import csv
import gzip
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def truth(problem, case):
    if problem == "binary_search_v1":
        matches=[i for i,v in enumerate(case["array"]) if v==case["target"]]
        return matches
    if problem == "max_subarray_v1":
        a=case["array"]
        return max(sum(a[i:j]) for i in range(len(a)) for j in range(i+1,len(a)+1))
    if problem != "dijkstra_v1":
        raise ValueError("Unknown problem")
    best=[None]*case["n"]
    stack=[(case["source"],0,{case["source"]})]
    while stack:
        u,cost,used=stack.pop()
        if best[u] is None or cost<best[u]:
            best[u]=cost
        for a,b,w in case["edges"]:
            if a==u and b not in used:
                stack.append((b,cost+w,used|{b}))
    return best

def case_valid(problem,case):
    if type(case) is not dict: return False
    if problem=="dijkstra_v1":
        if set(case)!={"n","source","edges"}: return False
        n,s,e=case["n"],case["source"],case["edges"]
        if type(n) is not int or not 2<=n<=8 or type(s) is not int or not 0<=s<n or type(e) is not list or len(e)>20: return False
        pairs=set()
        for edge in e:
            if type(edge) is not list or len(edge)!=3 or any(type(v) is not int for v in edge): return False
            u,v,w=edge
            if not 0<=u<n or not 0<=v<n or u==v or not 1<=w<=20 or (u,v) in pairs: return False
            pairs.add((u,v))
        return True
    if problem not in ("binary_search_v1","max_subarray_v1"): return False
    a=case.get("array")
    if type(a) is not list or any(type(v) is not int or not -20<=v<=20 for v in a): return False
    if problem=="max_subarray_v1": return set(case)=={"array"} and 1<=len(a)<=24
    return set(case)=={"array","target"} and len(a)<=32 and a==sorted(a) and type(case["target"]) is int and -20<=case["target"]<=20

def oracle_ok(bundle):
    problem,case=bundle["problem_id"],bundle["case"]
    if not case_valid(problem,case): return False
    t=truth(problem,case)
    expected=(t[0] if t else -1) if problem=="binary_search_v1" else t
    if expected!=bundle["expected_output"]: return False
    actual=bundle["observed_output"]
    if bundle["failure_kind"]=="wrong_answer":
        if problem=="binary_search_v1": return type(actual) is int and actual not in (t or [-1])
        return actual!=expected
    return bundle["failure_kind"] in {"contract_violation","exception","timeout"}

def audit(out):
    frozen=load(out/"freeze.json")
    summary=load(out/"summary.json")
    with (out/"runs.csv").open(encoding="utf-8",newline="") as fp: rows=list(csv.DictReader(fp))
    expected={(i["id"],str(s),v["id"]) for i in frozen["corpus"] for s in frozen["policy"]["seeds"] for v in frozen["policy"]["variants"]}
    actual={(r["program"],r["seed"],r["variant"]) for r in rows}
    if actual!=expected or len(rows)!=len(expected) or summary["run_count"]!=len(rows):
        raise ValueError("Missing, duplicate or inconsistent runs")
    manifest={r["id"]:r for r in frozen["corpus"]}
    failures=[]; replay=[0,0]; witnesses=0; specific=0; certificates=0; rejected=0; reductions=0
    raw_dir=out/"raw"
    expected_files={Path(r["raw_file"]).name for r in rows}
    if {p.name for p in raw_dir.glob("*.json.gz")}!=expected_files: raise ValueError("Raw file set differs from run table")
    per_program=defaultdict(list)
    for row in rows:
        ident=(row["program"],row["seed"],row["variant"])
        item=manifest[row["program"]]
        if row["label"]!=item["label"] or row["problem"]!=item["problem"]: failures.append([ident,"manifest label/problem mismatch"])
        per_program[(row["variant"],row["program"])].append(row)
        with gzip.open(raw_dir/Path(row["raw_file"]).name,"rt",encoding="utf-8") as fp: bundle=json.load(fp)
        if row["status"]=="internal_error":
            if "error" not in bundle: failures.append([ident,"internal error missing raw evidence"])
            continue
        identity=bundle["submission"]
        source_hash=hashlib.sha256(identity["source"].encode("utf-8")).hexdigest()
        if source_hash!=identity["source_sha256"] or source_hash!=item["sha256"] or bundle["status"]!=row["status"] or bundle["problem_id"]!=item["problem"] or str(bundle["seed"])!=row["seed"]:
            failures.append([ident,"source/status/problem/seed mismatch"])
        if bundle["status"]!="witness_found": continue
        witnesses+=1
        verification=bundle["verification"]
        replay[0]+=verification["replay_matches"]; replay[1]+=verification["replay_attempts"]
        specific+=bundle.get("diagnostic_status")=="supported"
        rejected+=len(bundle.get("claim_verification",{}).get("rejected_ids",[]))
        reductions+=row.get("strictly_reduced")=="True"
        if not oracle_ok(bundle) or verification["replay_matches"]!=verification["replay_attempts"] or verification["replay_attempts"]<2:
            failures.append([ident,"invalid witness/oracle/replay record"])
        events={e["event_id"]:e for e in bundle["events"]}
        for claim in bundle["claims"]:
            if any(i not in events for i in claim["event_ids"]): failures.append([ident,"missing claim event"])
        proof=bundle.get("witness_explanation")
        if proof:
            certificates+=1
            if proof["kind"]=="max_subarray":
                a=bundle["case"]["array"]; i,j=proof["start"],proof["end_exclusive"]
                if not 0<=i<j<=len(a) or a[i:j]!=proof["segment"] or sum(a[i:j])!=proof["sum"] or proof["sum"]!=bundle["expected_output"]:
                    failures.append([ident,"invalid subarray certificate"])
            elif proof["kind"]=="membership":
                if proof["matching_indices"]!=truth(bundle["problem_id"],bundle["case"]): failures.append([ident,"invalid membership certificate"])
            elif proof["kind"]=="shortest_path":
                vs=proof["vertices"]; es={(u,v):w for u,v,w in bundle["case"]["edges"]}
                if not vs or vs[0]!=bundle["case"]["source"] or vs[-1]!=proof["target"] or [es.get((u,v)) for u,v in zip(vs,vs[1:])]!=proof["weights"] or sum(proof["weights"])!=proof["cost"] or proof["cost"]!=bundle["expected_output"][proof["target"]]: failures.append([ident,"invalid shortest path certificate"])
            elif proof["kind"]=="unreachable":
                if proof["reachable_vertices"]!=[i for i,v in enumerate(bundle["expected_output"]) if v is not None] or bundle["expected_output"][proof["target"]] is not None: failures.append([ident,"invalid unreachable certificate"])
            else: failures.append([ident,"unknown certificate"])
    groups=[]
    for variant in frozen["policy"]["variants"]:
        name=variant["id"]
        buggy=[g for (v,p),g in per_program.items() if v==name and g[0]["label"]=="buggy"]
        correct=[g for (v,p),g in per_program.items() if v==name and g[0]["label"]=="correct"]
        rng=random.Random(2026)
        rates=[sum(r["status"]=="witness_found" for r in g)/len(g) for g in buggy]
        boots=sorted(statistics.mean(rng.choices(rates,k=len(rates))) for _ in range(2000)) if rates else []
        all_rows=[r for r in rows if r["variant"]==name]
        elapsed=[float(r["elapsed_ms"]) for r in all_rows if r.get("elapsed_ms")]
        discovery=[float(r["discovery_ms"]) for r in all_rows if r.get("discovery_ms") and r["status"]=="witness_found"]
        groups.append({"variant":name,"buggy_programs_found":sum(any(r["status"]=="witness_found" for r in g) for g in buggy),"buggy_programs":len(buggy),
                       "correct_programs_accused":sum(any(r["status"]=="witness_found" for r in g) for g in correct),"correct_programs":len(correct),
                       "program_cluster_bootstrap_detection_95pct":[boots[49],boots[1949]] if boots else None,
                       "median_total_ms":statistics.median(elapsed) if elapsed else None,"median_total_ms_n":len(elapsed),
                       "median_success_discovery_ms":statistics.median(discovery) if discovery else None,"success_discovery_n":len(discovery),
                       "statuses":dict(Counter(r["status"] for r in all_rows))})
    return {"run_count":len(rows),"witnesses":witnesses,"replay_matches":replay[0],"replay_attempts":replay[1],
            "specific_observations":specific,"rejected_candidates":rejected,"strict_reductions":reductions,"certificate_count":certificates,
            "failure_kinds":dict(Counter(r["kind"] for r in rows if r["status"]=="witness_found")),
            "audit_errors":failures,"groups":groups,"human_review":"pending",
            "limitation":"Independent reference recomputation and structural audit, not an independent human or machine replication; authored files may be correlated."}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.input)
    with args.report.open("x",encoding="utf-8") as fp: json.dump(result,fp,ensure_ascii=False,indent=2)
    print(json.dumps(result,indent=2))
    raise SystemExit(bool(result["audit_errors"]))
