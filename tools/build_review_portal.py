"""Generate a self-contained offline review portal containing only redacted review packets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def rows(path, fields):
    items=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        row=json.loads(line)
        items.append({field:row[field] for field in fields})
    if not items or len({r["review_id"] for r in items})!=len(items):
        raise ValueError("Empty or duplicate review packet")
    return items

def build(run, out):
    out.mkdir(parents=True,exist_ok=False)
    base=["review_id","problem_id","source","case","expected","observed","trace_status","events"]
    claims=rows(run/"explanation-review/review_packet.jsonl",base+["candidate_text","cited_event_ids"])
    locations=rows(run/"human-review/localization-packet.jsonl",base+["failure_kind"])
    payload=json.dumps({"claim":claims,"location":locations},ensure_ascii=False,separators=(",",":")).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    template=(ROOT/"tools/review_portal.html").read_text(encoding="utf-8")
    if template.count("__PACKET__")!=1: raise ValueError("Template marker mismatch")
    html=out/"review.html"
    html.write_text(template.replace("__PACKET__",payload),encoding="utf-8")
    shutil.copy2(ROOT/"docs/option_b/HUMAN_REVIEW_PROTOCOL.md",out/"HUMAN_REVIEW_PROTOCOL.md")
    archive=out/"Independent_Reviewer_Portal.zip"
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as z:
        for name in ("review.html","HUMAN_REVIEW_PROTOCOL.md"): z.write(out/name,name)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None: raise ValueError("Archive integrity failure")
    report={"claims":len(claims),"localization":len(locations),"archive":str(archive),"sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"human_ratings":"pending"}
    (out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();build(a.input.resolve(),a.out.resolve())
