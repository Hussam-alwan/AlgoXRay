"""Create verified local author and independent-review archives without changing frozen inputs."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def make_zip(dest, entries):
    with zipfile.ZipFile(dest,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path,name in entries:
            if not path.is_file(): raise ValueError("Missing required file: "+str(path))
            z.write(path,name)
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None: raise ValueError("ZIP integrity failed")
        if len(z.namelist())!=len(entries) or len(set(z.namelist()))!=len(entries):
            raise ValueError("Archive entry count mismatch")
    return {"name":dest.name,"entries":len(entries),"sha256":digest(dest),"bytes":dest.stat().st_size}

def tree(path, prefix):
    return [(p,prefix+"/"+p.relative_to(path).as_posix()) for p in sorted(path.rglob("*")) if p.is_file()]

def main(run,out,protocol,conference=None):
    audit=load(run/"audit.json")
    exp=load(run/"explanation-review/report.json")
    freeze=load(run/"freeze.json")
    if audit["audit_errors"] or exp["validation_errors"] or exp["status"]!="measured":
        raise ValueError("Measured run has audit errors")
    raw=sorted((run/"raw").glob("*.json.gz"))
    if len(raw)!=audit["run_count"]: raise ValueError("Incomplete raw evidence")
    conference=conference or run/"conference"
    manifest=load(conference/"SHA256SUMS.json")
    for name,expected in manifest.items():
        if digest(conference/name)!=expected: raise ValueError("Conference file altered: "+name)
    out.mkdir(parents=True,exist_ok=False)
    reviewer=[
        (protocol,"HUMAN_REVIEW_PROTOCOL.md"),
        (run/"explanation-review/review_packet.jsonl","claim-review-packet.jsonl"),
        (run/"human-review/localization-packet.jsonl","localization-review-packet.jsonl"),
        (run/"human-review/claim-ratings-template.csv","claim-ratings-template.csv"),
        (run/"human-review/localization-ratings-template.csv","localization-ratings-template.csv"),
    ]
    # Do not include mapping keys or rankings in independent reviewer archive.
    records=[
        make_zip(out/"AlgoXRay_V2_Conference_Author_Draft.zip",tree(conference,"conference")),
        make_zip(out/"AlgoXRay_V2_Independent_Review.zip",reviewer),
        make_zip(out/"AlgoXRay_V2_Research_Evidence_PRIVATE.zip",
            [(run/name,name) for name in ("freeze.json","summary.json","audit.json","runs.csv","review.csv","verification_decisions.csv")]
            +[(p,"raw/"+p.name) for p in raw]+tree(run/"explanation-review","explanation-review")
            +tree(run/"human-review","human-review")),
    ]
    result={"source_commit":freeze["source_commit"],"archives":records,
            "note":"Local author drafts only. Keep research evidence archive and review keys private until ratings lock; confirm permissions, venue and author approval before sharing."}
    (out/"ARCHIVE_MANIFEST.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    p.add_argument("--protocol",type=Path,default=Path("docs/option_b/HUMAN_REVIEW_PROTOCOL.md"))
    p.add_argument("--conference",type=Path)
    a=p.parse_args()
    main(a.input.resolve(),a.out.resolve(),a.protocol.resolve(),a.conference.resolve() if a.conference else None)
