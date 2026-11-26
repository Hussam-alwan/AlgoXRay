"""Build a local conference draft from a completed, audited frozen v2 run."""
import argparse
from collections import Counter
import csv
import hashlib
from html import escape
import json
from pathlib import Path
import shutil
import sys
from xml.etree import ElementTree
from playwright.sync_api import sync_playwright
from verify_browser import available_browser

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(value, encoding="utf-8")

def build(run, job, output):
    progress=load(job/"progress.json")
    if progress["status"]!="passed" or any(s["status"]!="passed" for s in progress["stages"]):
        raise ValueError("Release gates have not all passed")
    freeze=load(run/"freeze.json")
    summary=load(run/"summary.json")
    audit=load(run/"audit.json")
    explanation=load(run/"explanation-review/report.json")
    commit=freeze["source_commit"]
    if commit!=progress["source_commit"] or commit!=summary["source_commit"]:
        raise ValueError("Release identity mismatch")
    if audit["audit_errors"] or explanation["validation_errors"] or explanation["status"]!="measured":
        raise ValueError("Audit has unresolved errors")
    if summary["run_count"]!=audit["run_count"]:
        raise ValueError("Run count mismatch")
    for name, expected in freeze["files"].items():
        if sha(ROOT/name)!=expected:
            raise ValueError("Frozen file changed: "+name)
    browser=load(job/"browser/browser.json")
    core=load(job/"browser/core/browser.json")
    if browser["status"]!="passed" or core["page_errors"] or core["external_requests"]:
        raise ValueError("Browser verification failed")
    journeys=len(browser["journeys"])+len(core["journeys"])
    tests=None
    for reportpath in sorted((ROOT/"results/jobs/option-b-baseline").glob("*/report.json"),reverse=True):
        report=load(reportpath)
        if report["commit"]==commit and report["status"]=="automated_checks_passed":
            suite=ElementTree.parse(reportpath.parent/"tests.xml").getroot()
            test_suites=[suite] if suite.tag=="testsuite" else list(suite.findall("testsuite"))
            tests=sum(int(s.attrib.get("tests",0)) for s in test_suites)
            if any(int(s.attrib.get("failures",0))+int(s.attrib.get("errors",0)) for s in test_suites):
                raise ValueError("Unexpected test failure")
            break
    if tests is None:
        raise ValueError("No matching passing baseline test report")
    variants={}
    for row in summary["rows"]:
        item=variants.setdefault(row["variant"],Counter())
        for key in ("buggy_runs","buggy_found","control_runs","control_accusations","specific","reduced"):
            item[key]+=row[key]
    full=variants["full"]
    total=Counter()
    for value in variants.values(): total.update(value)
    neg=explanation["synthetic_negative_controls"]
    diag=explanation["diagnostics"]
    timing={g["variant"]:g for g in audit["groups"]}
    rows=[]
    for name, row in variants.items():
        g=timing[name]
        rows.append((name,f"{row['buggy_found']}/{row['buggy_runs']}",f"{row['control_accusations']}/{row['control_runs']}",f"{g['median_success_discovery_ms']:.2f}" if g["median_success_discovery_ms"] is not None else "N/A",f"{g['median_total_ms']:.2f}" if g["median_total_ms"] is not None else "N/A"))
    output.mkdir(parents=True,exist_ok=False)
    images=output/"screenshots"
    images.mkdir()
    for name in ("max-subarray-desktop.png","mobile.png","max-subarray-evidence.json"):
        shutil.copy2(job/"browser"/name,images/name)
    for source in sorted((job/"browser/core").glob("*")):
        if source.is_file() and source.suffix.lower() in (".jpg",".png",".json"):
            shutil.copy2(source,images/("core-"+source.name))
    summary_text=(f"Frozen revision {commit[:12]} · {summary['corpus_count']} program files · "
                  f"{summary['run_count']} executions. {total['buggy_found']}/{total['buggy_runs']} faulty trials "
                  f"produced a witness; {total['control_accusations']}/{total['control_runs']} control trials were accused. "
                  f"{audit['replay_matches']}/{audit['replay_attempts']} recorded replays matched. "
                  f"{audit['certificate_count']} certificates audited; no audit errors.")
    specific=f"{full['specific']}/{full['buggy_found']}"
    reduction=f"{full['reduced']}/{full['buggy_found']}"
    table="| Variant | Faulty witnesses | Control accusations | Median successful discovery (ms) | Median total (ms) |\n|---|---:|---:|---:|---:|\n"+"\n".join("| "+" | ".join(row)+" |" for row in rows)
    md=f"""# Option B v2 — frozen measured evidence

{summary_text}

{table}

Full arm: {reduction} strict reductions, {specific} specific observations.
Spectrum ranking available for {diag.get('spectrum_available',0)}/{diag.get('witnesses',0)} matched full-arm witnesses; arithmetic read/write links for {diag.get('arithmetic_links_available',0)}/{diag.get('witnesses',0)}.
Synthetic tampering: prose {neg.get('prose_rejected',0)}/{neg.get('prose_attempts',0)} rejected; missing events {neg.get('missing_event_rejected',0)}/{neg.get('missing_event_attempts',0)} rejected. These are designed negative controls, not human factuality.
Automated gates: {tests} tests; {journeys} browser journeys; no release-stage failures in the accepted attempt.

## Limits
The v2 corpus is reused after inspecting v1; this is exploratory regression, not a new held-out evaluation. The 30 files include assistant-authored code, not independent student submissions. Repeated seeds are not participants. Specific source observations may be output symptoms; spectrum ranks are suspicions, not causes. No human annotation, learner outcomes, security sandbox, general root-cause accuracy or cross-tool superiority is claimed. The matched deterministic explainer ablation is not a general LLM comparison. Preserve earlier failed gate logs separately. Author approval and final venue requirements remain open.
"""
    write(output/"MEASURED_V2.md",md)
    htmlrows="".join("<tr>"+"".join(f"<td>{escape(c)}</td>" for c in row)+"</tr>" for row in rows)
    html=f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>AlgoX-Ray v2</title>
<style>
@page{{size:A3 landscape;margin:12mm}}*{{box-sizing:border-box}}body{{font:16px/1.4 Arial,sans-serif;color:#173247;margin:0;background:white}}header{{background:#12354c;color:white;padding:20px 25px}}h1{{font-size:44px;line-height:1;margin:0 0 8px}}h2{{font-size:22px;margin:0 0 7px}}p{{margin:6px 0}}.subtitle{{font-size:22px}}.grid{{display:grid;grid-template-columns:1fr 1fr 1.2fr;gap:13px;margin-top:13px;align-items:start}}section{{border-top:5px solid #277f82;background:#f3f6f7;padding:13px;break-inside:avoid}}.wide{{grid-column:1/3}}.flow{{font-weight:bold;color:#17666b}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #b5c7cb;text-align:right;padding:5px}}td:first-child,th:first-child{{text-align:left}}img{{width:100%;max-height:475px;object-fit:contain;object-position:top}}.small{{font-size:13px}}footer{{margin-top:13px;border-top:1px solid #b5c7cb;padding-top:8px}}@media print{{*{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}}}
</style><header><h1>AlgoX-Ray</h1><p class="subtitle">Counterexample-driven debugging with checkable evidence</p><p>ICIPS 2026 · Measured research prototype · {escape(commit[:12])} · Author review draft</p></header>
<div class="grid">
<section><h2>Problem & contribution</h2><p>A wrong answer does not identify the cause. Link a legal, replayed counterexample to actual Python events, checkable observations and abstention.</p><p class="flow">Generate → compare → replay → reduce → trace → verify</p></section>
<section><h2>Three contracts</h2><p>Directed shortest paths · binary-search membership · maximum nonempty subarray.</p><p>Two oracles for graph and subarray; any matching index accepted for search. Persistent or fresh local worker. Cancellation and infrastructure failures are explicit.</p></section>
<section style="grid-row:1/4;grid-column:3"><h2>Live browser capture</h2><img src="screenshots/max-subarray-desktop.png" alt="Actual maximum-subarray analysis"><p class="small">Browser-tested witness: [-5, −2, −7], expected −2, observed 0; exported evidence included.</p></section>
<section class="wide"><h2>Measured v2 results</h2><p>{escape(summary_text)}</p><table><thead><tr><th>Variant</th><th>Faulty</th><th>Control accusations</th><th>Discovery ms*</th><th>Total ms</th></tr></thead><tbody>{htmlrows}</tbody></table><p class="small">*Median over successful witness discoveries. Total median over all trials in that arm. Full arm: {reduction} strict reductions; {specific} specific observations. {tests} tests, {journeys} browser journeys passed.</p></section>
<section><h2>Evidence, not guesses</h2><p>Frame/event IDs, checked mathematical symptoms, bounded arithmetic dependencies, spectrum suspicion ranking. Unsupported specific statements withheld.</p><p>Designed tampering checks: prose {neg.get('prose_rejected',0)}/{neg.get('prose_attempts',0)}; missing event {neg.get('missing_event_rejected',0)}/{neg.get('missing_event_attempts',0)} rejected.</p></section>
<section><h2>Limitations</h2><p>Reused partly assistant-authored corpus. No independent learner study, human factuality rating, causal-localization guarantee, hostile-code sandbox, or new held-out test.</p><p class="small">Code Hunt, Python Tutor, ITAP, CodeHelp, Hypothesis and repair research are prior work; integration is not a priority claim.</p></section>
</div><footer class="small">Artifact: github.com/Hussam-alwan/AlgoXRay/tree/option-b · Frozen manifest, audit, raw runs and browser evidence preserved locally. Confirm venue format and anonymization before submission.</footer></html>"""
    write(output/"poster-v2.html",html)
    with sync_playwright() as p:
        instance=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=instance.new_page(viewport={"width":1536,"height":1080})
        page.goto((output/"poster-v2.html").resolve().as_uri(),wait_until="load")
        assert page.locator("img").evaluate("(img) => img.complete && img.naturalWidth > 0")
        page.pdf(path=str(output/"poster-v2.pdf"),prefer_css_page_size=True,print_background=True)
        page.screenshot(path=str(output/"poster-preview.png"),full_page=True)
        instance.close()
    for name in ("freeze.json","summary.json","audit.json","runs.csv"):
        shutil.copy2(run/name,output/name)
    shutil.copy2(run/"explanation-review/report.json",output/"explanation-report.json")
    shutil.copy2(job/"progress.json",output/"release-progress.json")
    manifest={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    write(output/"SHA256SUMS.json",json.dumps(manifest,indent=2))
    print(json.dumps({"status":"built","source_commit":commit,"tests":tests,"browser_journeys":journeys,"output":str(output)},indent=2))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--job",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    a=parser.parse_args()
    build(a.input.resolve(),a.job.resolve(),a.out.resolve())
