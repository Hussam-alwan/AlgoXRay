"""Package reviewed project files and latest actual results; exclude local environments."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    summary = json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8"))
    selected = [ROOT / p for p in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", ".gitignore",
                                  "requirements.lock.txt", "setup.bat", "start.bat")]
    for directory in ("backend", "fixtures", "contracts", "web", "benchmarks", "tools", "docs"):
        selected.extend((ROOT / directory).rglob("*"))
    for directory in ("results/evidence-audit", "results/benchmarks/" + summary["raw_directory"]):
        selected.extend((ROOT / directory).rglob("*"))
    selected.extend(ROOT / p for p in ("results/summary.json", "results/evidence-audit.json", "results/clean-check-evidence.json"))
    files = sorted({p for p in selected if p.is_file()
                    and not any(part in {"__pycache__", ".pytest_cache", ".hypothesis"} or part.endswith(".egg-info") for part in p.parts)
                    and p.suffix not in {".pyc", ".log"}
                    and not p.name.startswith("_transfer_") and p.name != "apply_source_transfer.py"})
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "kind": "local prototype source and measured-results snapshot",
                "benchmark_source_sha256": summary["codebase_sha256"], "benchmark_trials": summary["total_runs"],
                "files": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                "limits": "Known finite fixture evaluation; author review and conference submission remain separate"}
    output = ROOT / "dist/AlgoXRay_Prototype_2026-11-26.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for p in files:
            archive.write(p, "algoxray/" + p.relative_to(ROOT).as_posix())
        archive.writestr("algoxray/ARTIFACT_MANIFEST.json", json.dumps(manifest, indent=2))
    result = {"path": str(output), "bytes": output.stat().st_size,
              "base64_characters": ((output.stat().st_size + 2) // 3) * 4,
              "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "files": len(files)}
    (ROOT / "dist/package.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
