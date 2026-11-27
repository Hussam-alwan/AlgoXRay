"""Prepare blinded-to-role localization packet and separate private key.
Source may reveal the bug; this is not fully blind or an independent corpus.
"""
import argparse,csv,json,random,hashlib
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    src=Path(a.input);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    packets=[];keys=[]
    for f in sorted(src.glob("*-fault.json")):
        d=json.loads(f.read_text());r=d["result"]
        if r.get("status")!="observed_mismatch":continue
        w=r["witness"];key=hashlib.sha256((f.name+d["package_sha256"]).encode()).hexdigest()[:12]
        packets.append({"id":key,"source":r["student_source"],"stdin":w["stdin"],"expected":w["reference"]["stdout"],"actual":w["student"].get("stdout"),"exception":w["student"].get("detail"),"events":w["student"].get("events",[]),"trace_status":w["student"].get("trace_status")})
        keys.append({"id":key,"family":d["family"],"known_edit_line":d["known_bug_line"],"ranking":r.get("suspiciousness")})
    random.Random(2026).shuffle(packets)
    (out/"review-packet.json").write_text(json.dumps(packets,indent=2))
    (out/"PRIVATE-key.json").write_text(json.dumps(keys,indent=2))
    with (out/"ratings-template.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f);writer.writerow(["id","reviewer_pseudonym","localization_status","line_numbers","event_ids","reason","helpfulness_1_to_5"])
        for p in packets:writer.writerow([p["id"],"","","","","",""])
    (out/"README.md").write_text("# V4 reviewer protocol\nTwo reviewers work independently. Do not share PRIVATE-key.json. For each case inspect source, stdin, expected and actual output and recorded trace. Mark localized, missing_step, ambiguous, or insufficient_evidence. Supply acceptable line numbers and supporting event IDs, explain reasoning, and rate helpfulness separately. Do not treat a known edit line as the only acceptable explanation. Review packets contain external benchmark adaptations, not independent student programs. Guest trace is not authenticated. Collect actual ratings; do not simulate or auto-fill. Rank labels are hidden, but source may reveal the issue.\n",encoding="utf-8")
    print(len(packets),"localization cases; no ratings generated")
if __name__=="__main__":main()
