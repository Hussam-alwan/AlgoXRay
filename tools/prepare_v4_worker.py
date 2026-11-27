"""Build a minimal worker image and pin its local content ID. No host files are included."""
import json,subprocess
from pathlib import Path
def main():
    root=Path(__file__).resolve().parents[1]
    tag="algoxray-v4-worker:local"
    subprocess.run(["docker","build","--pull","-t",tag,str(root/"docker"/"v4-worker")],check=True)
    image=subprocess.check_output(["docker","image","inspect",tag,"--format","{{.Id}}"],text=True).strip()
    report={"image_id":image,"tag":tag,"source":"docker/v4-worker/Dockerfile","scope":"local dedicated worker, public security not certified"}
    path=root/"results"/"v4-runtime.json";path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report),flush=True)
if __name__=="__main__":main()
