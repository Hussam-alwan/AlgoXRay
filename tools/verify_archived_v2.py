"""Check old saved evidence on the new validator; no rerun or modification."""
import argparse,gzip,json
from pathlib import Path
from algoxray.engine import validate_bundle
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("directories",nargs="+",type=Path)
    a=p.parse_args()
    checked=0
    for directory in a.directories:
        count=0
        for file in sorted((directory/"raw").glob("*.json.gz")):
            with gzip.open(file,"rt",encoding="utf-8") as f: bundle=json.load(f)
            if bundle.get("evidence_revision")!="option-b.2": raise ValueError("Expected archived v2: "+str(file))
            validate_bundle(bundle)
            count+=1
        if not count: raise ValueError("No bundles: "+str(directory))
        checked+=count
        print(directory, count, "validated")
    print("Total archived v2 bundles validated:",checked)
if __name__=="__main__":main()
