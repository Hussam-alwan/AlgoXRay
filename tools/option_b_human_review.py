"""Prepare blinded localization review and score human factuality/localization ratings.

No ratings are synthesized. Reviewers receive only the packet, not the mapping key.
"""
import argparse
import csv
import gzip
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, fields, rows):
    with path.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def prepare(run,out):
    audit=read_json(run/"audit.json")
    if audit["audit_errors"]:
        raise ValueError("Audit not passed")
    out.mkdir(parents=True,exist_ok=False)
    packet=[]
    key=[]
    for row in read_csv(run/"runs.csv"):
        if row["variant"]!="full" or row["status"]!="witness_found":
            continue
        with gzip.open(run/row["raw_file"],"rt",encoding="utf-8") as f:
            b=json.load(f)
        ident=hashlib.sha256(("location-review:"+row["raw_file"]).encode()).hexdigest()[:24]
        packet.append({"review_id":ident,"problem_id":b["problem_id"],"source":b["submission"]["source"],
                       "case":b["case"],"expected":b["expected_output"],"observed":b["observed_output"],
                       "failure_kind":b["failure_kind"],"trace_status":b["trace_status"],"events":b["events"]})
        ranking=b.get("suspicion_ranking",[])
        key.append({"review_id":ident,"raw_file":row["raw_file"],"lines":[x["line"] for x in ranking]})
    random.Random(2026).shuffle(packet)
    (out/"localization-packet.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in packet),encoding="utf-8")
    (out/"localization-key.json").write_text(json.dumps(key,indent=2),encoding="utf-8")
    write_csv(out/"localization-ratings-template.csv",["reviewer","review_id","verdict","acceptable_lines","reason"],
              [{"review_id":x["review_id"],"reviewer":"","verdict":"","acceptable_lines":"","reason":""} for x in packet])
    claims=[json.loads(line) for line in (run/"explanation-review/review_packet.jsonl").read_text(encoding="utf-8").splitlines()]
    write_csv(out/"claim-ratings-template.csv",["reviewer","review_id","verdict","reason"],
              [{"review_id":x["review_id"],"reviewer":"","verdict":"","reason":""} for x in claims])
    print(json.dumps({"localization_items":len(packet),"claim_items":len(claims),"ratings":"pending"},indent=2))

def cohen(a,b):
    paired=[(a[k],b[k]) for k in a.keys() & b.keys()]
    if not paired: return {"paired":0,"agreement":None,"kappa":None}
    n=len(paired); x=Counter(v for v,_ in paired); y=Counter(v for _,v in paired)
    po=sum(u==v for u,v in paired)/n
    pe=sum(x[v]*y[v] for v in x.keys()|y.keys())/n**2
    return {"paired":n,"agreement":po,"kappa":None if pe==1 else (po-pe)/(1-pe)}

def load_ratings(paths,valid_ids,verdicts):
    all_ratings={}
    for path in paths:
        for row in read_csv(path):
            reviewer=row["reviewer"].strip()
            ident=row["review_id"]
            if not reviewer or ident not in valid_ids or row["verdict"] not in verdicts or not row["reason"].strip():
                raise ValueError(f"Incomplete or invalid rating: {path} {ident}")
            entries=all_ratings.setdefault(reviewer,{})
            if ident in entries: raise ValueError("Duplicate reviewer/item")
            entries[ident]=row
    return all_ratings

def score(run,prepared,claims,locations,out):
    mapping=read_csv(run/"explanation-review/review_key.csv")
    valid={r["review_id"] for r in mapping}
    cr=load_ratings(claims,valid,{"supported","contradicted","uncheckable"})
    loc_key={r["review_id"]:r for r in read_json(prepared/"localization-key.json")}
    lr=load_ratings(locations,set(loc_key),{"located","missing_step","ambiguous"})
    packet={x["review_id"]:x for x in map(json.loads,(prepared/"localization-packet.jsonl").read_text(encoding="utf-8").splitlines())}
    result={"claim_item_count":len(valid),"localization_item_count":len(loc_key),"claim_reviewers":{},"localization_reviewers":{},"agreement":[]}
    for reviewer,ratings in cr.items():
        arms={}
        for r in mapping:
            rating=ratings.get(r["review_id"])
            if not rating: continue
            arm=arms.setdefault(r["arm"],{"before":Counter(),"after":Counter()})
            arm["before"][rating["verdict"]]+=1
            if r["published"]=="True": arm["after"][rating["verdict"]]+=1
        result["claim_reviewers"][reviewer]={"rated_items":len(ratings),"verdicts":dict(Counter(r["verdict"] for r in ratings.values())),"arms":arms}
    names=sorted(cr)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            result["agreement"].append({"reviewers":[a,b],**cohen({k:r["verdict"] for k,r in cr[a].items()},{k:r["verdict"] for k,r in cr[b].items()})})
    for reviewer,ratings in lr.items():
        counts=Counter()
        for ident,rating in ratings.items():
            counts[rating["verdict"]]+=1
            lines=loc_key[ident]["lines"]
            if lines: counts["ranking_available"]+=1
            if rating["verdict"]!="located": continue
            acceptable={int(x.strip()) for x in rating["acceptable_lines"].split(";") if x.strip()}
            n=len(packet[ident]["source"].splitlines())
            if not acceptable or any(not 1<=x<=n for x in acceptable):
                raise ValueError("Invalid acceptable line set")
            counts["located_with_ranking"]+=bool(lines)
            for k in (1,3,5):
                counts[f"top_{k}_hit"]+=bool(acceptable.intersection(lines[:k]))
        result["localization_reviewers"][reviewer]={"rated_items":len(ratings),"counts":dict(counts)}
    result["limitations"]="External human identity and independence must be documented separately. Missing and ambiguous locations are reported, not forced into line accuracy; top-k counts use all located labels, including no-rank cases."
    with out.open("x",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    sp=p.add_subparsers(dest="command",required=True)
    a=sp.add_parser("prepare");a.add_argument("--input",type=Path,required=True);a.add_argument("--out",type=Path,required=True)
    a=sp.add_parser("score");a.add_argument("--input",type=Path,required=True);a.add_argument("--prepared",type=Path,required=True);a.add_argument("--claims",type=Path,nargs="+",required=True);a.add_argument("--locations",type=Path,nargs="+",required=True);a.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if args.command=="prepare": prepare(args.input,args.out)
    else: score(args.input,args.prepared,args.claims,args.locations,args.out)
