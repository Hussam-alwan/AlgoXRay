"""Apply a reviewed source transfer without overwriting unrelated or edited files."""
import base64, gzip, hashlib, json, os, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
if "gzip_base64" in payload:
    payload = json.loads(gzip.decompress(base64.b64decode(payload["gzip_base64"])).decode("utf-8"))
prepared = []
for item in payload["files"]:
    path = (root / item["path"]).resolve()
    if not path.is_relative_to(root):
        raise SystemExit("Invalid destination")
    data = base64.b64decode(item["content"])
    digest = hashlib.sha256(data).hexdigest()
    current = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if current == digest:
        continue
    if current != item.get("previous_sha256"):
        raise SystemExit("Conflicting local change: " + item["path"])
    prepared.append((path, data))
for path, data in prepared:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".transfer-tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)
print(json.dumps({"written":len(prepared),"checked":len(payload["files"])}))
