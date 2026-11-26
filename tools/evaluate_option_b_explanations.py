"""Matched-witness deterministic evidence ablation and redacted human review packet.

No model API, no human ratings, no invented measured factuality. Synthetic tampering
checks are reported separately from natural candidate claims.
"""
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend/src"))
from algoxray.engine import validate_bundle
from algoxray.hints import build_hints
from algoxray.claim_verifier import abstain_on_unsupported
from algoxray.explanation import explanation_cards

def load(path):
    with gzip.open(path,"rt",encoding="utf-8") as fp: return json.load(fp)

def verify_frozen_source(directory):
    frozen=json.loads((directory/"freeze.json").read_text(encoding="utf-8"))
    for name,expected in frozen["files"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError("Current source differs from measured freeze: "+name)
    return frozen

def evaluate(directory, output):
    freeze=verify_frozen_source(directory)
    output.mkdir(parents=True,exist_ok=False)
    with (directory/"runs.csv").open(encoding="utf-8",newline="") as fp:
        rows=list(csv.DictReader(fp))
    arms={name:Counter() for name in ("source_only","witness_only","witness_trace")}
    review_entries={}
    mapping=[]
    negative=Counter()
    diagnostics=Counter()
    by_problem=defaultdict(Counter)
    errors=[]
    witness_count=0
    for row in rows:
        if row["variant"]!="full" or row["status"]!="witness_found": continue
        bundle=load(directory/row["raw_file"])
        ident=Path(row["raw_file"]).name.removesuffix(".json.gz")
        try: validate_bundle(bundle)
        except Exception as exc:
            errors.append({"run":ident,"error":f"{type(exc).__name__}: {exc}"})
            continue
        witness_count+=1
        problem=by_problem[bundle["problem_id"]]
        for target in (diagnostics,problem):
            target["witnesses"]+=1
            target["specific"]+=bundle["diagnostic_status"]=="supported"
            target["spectrum_available"]+=bool(bundle.get("suspicion_ranking"))
            target["arithmetic_links_available"]+=bool(bundle.get("dynamic_dependencies"))
            target["complete_trace"]+=bundle["trace_status"]=="complete"
            target["specific_return_invariant"]+=any(c.get("adapter_id") in {"graph_relaxation_invariant_v1","subarray_attainability_invariant_v1","max_subarray_zero_negative_v1"} for c in bundle["claims"])
        identity=bundle["submission"]
        sub=SimpleNamespace(source=identity["source"],origin=identity["origin"],adapter=identity.get("adapter_id"))
        contexts={
            "source_only":{**bundle,"status":"inconclusive","case":None,"original_case":None,"observed_output":None,"expected_output":None,"events":[],"trace_status":"not_run"},
            "witness_only":{**bundle,"events":[],"trace_status":"not_run"},
            "witness_trace":bundle
        }
        for arm,context in contexts.items():
            candidate={**context}
            claims,hints=build_hints(context,sub)
            candidate["claims"],candidate["hints"]=deepcopy(claims),deepcopy(hints)
            abstain_on_unsupported(candidate)
            published={c["claim_id"] for c in candidate["claims"]}
            counts=arms[arm]
            counts["witnesses"]+=1
            counts["candidate_claims"]+=len(claims)
            counts["published_claims"]+=len(published)
            counts["rejected_claims"]+=len(claims)-len(published)
            counts["specific_coverage"]+=any(c["kind"]=="source_specific_observation" for c in candidate["claims"])
            counts["no_claims"]+=not bool(published)
            for c in claims:
                key=hashlib.sha256(json.dumps([ident,c["text"],c["event_ids"]],ensure_ascii=False,separators=(",",":")).encode()).hexdigest()[:24]
                review_entries.setdefault(key,{"review_id":key,"source":identity["source"],
                    "problem_id":bundle["problem_id"],"case":bundle["case"],"expected":bundle["expected_output"],"observed":bundle["observed_output"],
                    "trace_status":bundle["trace_status"],"events":bundle["events"],"candidate_text":c["text"],
                    "cited_event_ids":c["event_ids"],"verdict":"","reason":"","reviewer":""})
                mapping.append({"review_id":key,"run":ident,"arm":arm,"claim_id":c["claim_id"],"published":c["claim_id"] in published})
        # Negative controls, not natural claim accuracy: corrupt otherwise valid text or event ID.
        if bundle["claims"]:
            changed=deepcopy(bundle); changed["claims"][0]["text"]="Synthetic invalid explanation; not supported."
            changed["explanation_cards"]=explanation_cards(changed)
            negative["prose_attempts"]+=1
            try: validate_bundle(changed)
            except ValueError: negative["prose_rejected"]+=1
        specific=next((c for c in bundle["claims"] if c["kind"]=="source_specific_observation"),None)
        if specific:
            changed=deepcopy(bundle); target=next(c for c in changed["claims"] if c["claim_id"]==specific["claim_id"])
            target["event_ids"]=["fabricated-event"]
            negative["missing_event_attempts"]+=1
            abstain_on_unsupported(changed)
            negative["missing_event_rejected"]+=specific["claim_id"] in changed["claim_verification"]["rejected_ids"]
    packets=list(review_entries.values())
    random.Random(2026).shuffle(packets)
    with (output/"review_packet.jsonl").open("x",encoding="utf-8") as fp:
        for entry in packets: fp.write(json.dumps(entry,ensure_ascii=False)+"\n")
    with (output/"review_key.csv").open("x",encoding="utf-8",newline="") as fp:
        writer=csv.DictWriter(fp,fieldnames=["review_id","run","arm","claim_id","published"])
        writer.writeheader();writer.writerows(mapping)
    report={"status":"audit_failed" if errors else "measured",
            "input":str(directory),"matched_witnesses":witness_count,"arms":{k:dict(v) for k,v in arms.items()},
            "diagnostics":dict(diagnostics),"by_problem":{k:dict(v) for k,v in by_problem.items()},
            "synthetic_negative_controls":dict(negative),"review_items":len(packets),"human_review":"pending",
            "validation_errors":errors,
            "limitations":["Same conservative deterministic explainer under masked evidence, not an LLM comparison. Source-only cannot assert an execution fact by design.",
                           "Coverage and automatic support are not human factuality, causal localization accuracy, or learning outcomes.",
                           "Review items are deduplicated and shuffled; context may reveal method indirectly. Keep the key private until ratings lock."]}
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    return not errors

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    raise SystemExit(0 if evaluate(a.input,a.out) else 1)
