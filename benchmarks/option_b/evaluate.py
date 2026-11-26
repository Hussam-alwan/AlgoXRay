"""Prospective paired evaluation. Run only on a fresh explicitly frozen directory."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
import subprocess
from collections import Counter
from importlib.metadata import version
from itertools import product

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))
from algoxray.engine import Options, analyze
from algoxray.registry import local_submission
from algoxray.problems import complexity

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def inventory():
    rows = []
    for directory in (ROOT/"benchmarks/core", HERE):
        for row in load(directory/"manifest.json"):
            path = directory/row["file"]
            sha = digest(path)
            if row.get("sha256", sha) != sha:
                raise ValueError("Corpus source differs: "+row["id"])
            rows.append({**row, "file":path.relative_to(ROOT).as_posix(), "sha256":sha})
    if len({r["sha256"] for r in rows}) != len(rows):
        raise ValueError("Duplicate corpus source")
    return rows

def freeze():
    tracked_dirty = subprocess.check_output(["git","status","--porcelain","--untracked-files=no"],cwd=ROOT,text=True).strip()
    if tracked_dirty:
        raise ValueError("Tracked source is not clean")
    paths = {p for directory in (ROOT/"backend/src",ROOT/"backend/tests",ROOT/"contracts",ROOT/"fixtures",ROOT/"web",HERE)
             for p in directory.rglob("*") if p.is_file() and p.suffix in (".py",".json",".html",".js",".css",".txt")}
    paths.update(ROOT/name for name in ("requirements.lock.txt","backend/pyproject.toml","benchmarks/core/manifest.json",
          "tools/verify_option_b_browser.py","tools/verify_core_browser.py"))
    rows = inventory()
    paths.update(ROOT/r["file"] for r in rows)
    return {"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "files":{p.relative_to(ROOT).as_posix():digest(p) for p in sorted(paths)},
            "corpus":rows, "policy":load(HERE/"protocol.json"),
            "environment":{"python":platform.python_version(),"platform":platform.platform(),
                           "hypothesis":version("hypothesis"),"networkx":version("networkx")}}

def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w",encoding="utf-8",newline="") as fp:
        writer=csv.DictWriter(fp,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def run(out, frozen):
    if freeze()!=frozen:
        raise ValueError("Source, corpus, policy or environment changed since freeze")
    raw=out/"raw"
    raw.mkdir(exist_ok=False)
    policy=frozen["policy"]
    rows,review,decisions=[],[],[]
    for item,seed in product(frozen["corpus"],policy["seeds"]):
        variants=policy["variants"]
        offset=policy["seeds"].index(seed)%len(variants)
        for variant in variants[offset:]+variants[:offset]:
            sub=local_submission(item["problem"],ROOT/item["file"])
            ident=f"{item['id']}-{seed}-{variant['id']}"
            row={"program":item["id"],"problem":item["problem"],"label":item["label"],
                 "seed":seed,"variant":variant["id"],"raw_file":"raw/"+ident+".json.gz"}
            try:
                opts=Options(seed=seed,**{k:v for k,v in variant.items() if k!="id"},
                             **{k:v for k,v in policy.items() if k not in ("seeds","variants")})
                bundle=analyze(sub,opts,persist=False)
                row.update(status=bundle["status"],kind=bundle["failure_kind"],
                           **bundle["statistics"],**bundle["verification"])
                if bundle["case"] is not None:
                    row["strictly_reduced"]=complexity(item["problem"],bundle["case"])<complexity(item["problem"],bundle["original_case"])
                    row["specific"]=bundle["diagnostic_status"]=="supported"
                    row["rejected"]=len(bundle.get("claim_verification",{}).get("rejected_ids",[]))
                rejected = bundle.get("claim_verification",{}).get("rejected_candidates",[])
                for claim in bundle["claims"] + rejected:
                    review.append({"run":ident,"claim":claim["claim_id"],"text":claim["text"],
                                   "events":"|".join(claim["event_ids"]),"verdict":"","reviewer":"","reason":""})
                    decisions.append({"run":ident,"claim":claim["claim_id"],
                                      "published":claim.get("verification_status")!="rejected"})
            except Exception as exc:
                row.update(status="internal_error",error=f"{type(exc).__name__}: {exc}")
                bundle={"error":row["error"]}
            with gzip.open(out/row["raw_file"],"wt",encoding="utf-8") as fp:
                json.dump(bundle,fp,ensure_ascii=False,allow_nan=False)
            rows.append(row)
    write_csv(out/"runs.csv",rows)
    write_csv(out/"review.csv",review)
    write_csv(out/"verification_decisions.csv",decisions)
    groups=[]
    for problem,variant in product(sorted({r["problem"] for r in rows}),policy["variants"]):
        group=[r for r in rows if r["problem"]==problem and r["variant"]==variant["id"]]
        faulty=[r for r in group if r["label"]=="buggy"]
        correct=[r for r in group if r["label"]=="correct"]
        groups.append({"problem":problem,"variant":variant["id"],"buggy_runs":len(faulty),
                       "buggy_found":sum(r["status"]=="witness_found" for r in faulty),
                       "control_runs":len(correct),"control_accusations":sum(r["status"]=="witness_found" for r in correct),
                       "statuses":dict(Counter(r["status"] for r in group)),
                       "programs":len({r["program"] for r in group}),
                       "specific":sum(bool(r.get("specific")) for r in group),
                       "reduced":sum(bool(r.get("strictly_reduced")) for r in group)})
    dump(out/"summary.json",{"status":"measured","source_commit":frozen.get("source_commit"),"corpus_count":len(frozen["corpus"]),
                            "run_count":len(rows),"rows":groups,"human_review":"pending"})

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("freeze","run"))
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.action=="freeze":
        args.out.mkdir(parents=True,exist_ok=False)
        dump(args.out/"freeze.json",freeze())
    else:
        run(args.out,load(args.out/"freeze.json"))

if __name__=="__main__":
    main()
