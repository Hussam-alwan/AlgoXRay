"""One local-only synthetic diagnostic probe; not an independent benchmark."""
import json
from pathlib import Path
from algoxray.v4_provider import OllamaProvider,model_health
from algoxray.v4_engine import analyze_package
from verify_mvp_branch_ai_browser import P,SOURCE
if __name__=="__main__":
    health=model_health()
    if "qwen2.5-coder:7b" not in health["models"]:
        report={"status":"local_model_unavailable","scope":"Synthetic development probe only."}
    else:
        r=analyze_package(P,SOURCE,case={"n":0},reduce_calls=0,spectrum=True,
                          provider=OllamaProvider(timeout=90))
        report={"status":r["status"],"ai_status":r.get("ai_status"),"ai_error":r.get("ai_error"),
                "model":r.get("ai_model"),"usage":r.get("ai_usage"),
                "context":r.get("ai_context"),"hypotheses":r.get("hypotheses"),
                "facts":r.get("ai_facts"),"branches":r.get("ai_branches"),
                "scope":"One exposed synthetic local-only development bug, not scientific accuracy or human review.",
                "witness":r.get("witness",{}).get("case"),"localization":r.get("evidence_localization")}
    out=Path("docs/mvp-evidence/branch-ai-local.json");out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=True),encoding="utf-8")
    print(json.dumps({k:report.get(k) for k in ("status","ai_status","ai_error","model","usage","hypotheses","facts","branches")}),flush=True)
