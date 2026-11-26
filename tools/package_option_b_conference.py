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

    by_problem=explanation["by_problem"]
    problem_table="| Contract | Full witnesses | Specific observations | Spectrum available | Arithmetic links |\n|---|---:|---:|---:|---:|\n"+"\n".join(
        f"| {k} | {v.get('witnesses',0)} | {v.get('specific',0)} | {v.get('spectrum_available',0)} | {v.get('arithmetic_links_available',0)} |" for k,v in by_problem.items())
    ablation_table="| Context | Witnesses | Candidate claims | Published | Rejected | Specific coverage |\n|---|---:|---:|---:|---:|---:|\n"+"\n".join(
        f"| {k} | {v.get('witnesses',0)} | {v.get('candidate_claims',0)} | {v.get('published_claims',0)} | {v.get('rejected_claims',0)} | {v.get('specific_coverage',0)} |" for k,v in explanation["arms"].items())
    manuscript=f"""# AlgoX-Ray: Counterexample-Driven Visual Debugging and Evidence-Grounded Hints for Algorithmic Problem Solving
**Measured v2 author-review draft — not venue-approved camera-ready.**

## Abstract
Algorithmic judges can show a wrong output without explaining why it occurs. AlgoX-Ray combines bounded legal input generation, reference comparison, replay, structural reduction, recorded Python execution and verified educational observations. Three problem contracts cover directed shortest paths, binary-search membership and maximum nonempty subarray. {summary_text} The full arm strictly reduced {reduction} witnesses and provided {specific} source-specific observations. The study establishes bounded technical feasibility on a reused, partly assistant-authored corpus, not general diagnostic accuracy or learning benefit.

## 1. Motivation and research questions
The question is whether an inspectable record connects a reproducible contract violation to execution-level observations that can be checked independently of a language model. RQ1 examines bounded witness discovery and control accusations. RQ2 examines reduction and replay consistency. RQ3 examines availability of source-specific evidence, abstention, and robustness against designed claim tampering. Human factuality and instructional value require separate evaluation and remain open.

## 2. Related work
Code Hunt uses generated counterexamples as clues [1]; Python Tutor visualizes execution [2]; ITAP generates hints from solution spaces [3]. CodeHelp [4] and CodeAid [5] investigate guarded programming assistance. Hypothesis incorporates structure-preserving reduction via generation [6]. Whyline explains output using execution information [7]. Spectrum-based ranking, including Ochiai, is established fault-localization work [8]. Counterexample-guided repair and MENTOR combine fault localization and LLM repair [9,10]. The contribution here is the integration of bounded witness search and inspectable narrow evidence checks with educational abstention; neither counterexample generation, spectrum scoring nor general tracing is claimed as new. Repair success rates and witness-discovery rates measure different outcomes.

## 3. System
Each registered problem declares legal inputs, a generator, a reducer, reference and acceptance checker. Directed graphs have 2–8 vertices with positive weights; Bellman–Ford is checked against Floyd–Warshall. Sorted arrays have up to 32 entries, and any index matching the target is legal. Maximum subarray requires a nonempty contiguous segment, with bounded exhaustive enumeration cross-checked by Kadane. Oracle disagreement and worker failures do not accuse a submission.

A local trusted-code child worker runs candidates with deadlines and records wrong answers, contract violations, exceptions and timeouts distinctly. A persistent worker starts a fresh namespace per case; optional fresh process per case also discards imported module state. Neither constitutes a hostile-code sandbox. Cancellation stops the server-side worker. A candidate must reproduce the same failure fingerprint; best-effort reduction preserves the failure signature. Final replay and traced replay must agree before evidence is promoted.

An evidence bundle binds source SHA-256, original and reduced input, observed and expected outputs, replay counts, frame and event identifiers, trace snapshots and claims. A verifier checks source-bound adapter predicates or narrow mathematical symptoms. Examples include a violated graph edge relaxation inequality and a returned zero when every admissible nonempty segment is negative. These observations identify symptoms, not necessarily the faulty statement. Arithmetic dependencies are restricted to observed consecutive same-frame integer assignments; no general dynamic slicing claim is made. Ochiai-style ranks use bounded passing/failing samples and represent suspicion only. Unsupported specific observations are withheld. Deterministic explanation text is regenerated from checked facts; no external AI provider is necessary.

## 4. Evaluation protocol
The frozen revision is {commit}. The corpus consists of {summary['corpus_count']} distinct program files, including historical fixtures and 18 additional assistant-authored implementations. The labels have not been independently reviewed. Five seeds are paired across random discovery, Hypothesis discovery and the full Hypothesis/reduction/trace arm. The first two disable reduction and tracing. V2 was developed after inspecting v1, so repeating the corpus is exploratory regression, not held-out confirmation. All runs are counted; discovery latency is conditional on successful discovery, and total latency includes all outcomes. Raw evidence, exact file hashes, environment and protocol are retained.

## 5. Results
{table}

{summary_text}
The full arm strictly reduced {reduction} witnesses and produced {specific} specific observations. V1 on the same corpus had 59/75 strict reductions and 20/75 specific observations; differences are descriptive, not an independent validation of generalization.

{problem_table}

The same conservative deterministic explainer was evaluated on matched witnesses under three evidence masks. Source-only abstains from execution claims by design; witness-only has no trace-specific evidence.

{ablation_table}

Designed negative controls rejected {neg.get('prose_rejected',0)}/{neg.get('prose_attempts',0)} fabricated prose attempts and {neg.get('missing_event_rejected',0)}/{neg.get('missing_event_attempts',0)} missing-event claims. These are artificial integrity probes, not estimates of natural claim factuality. The review packet contains {explanation['review_items']} unique items; independent ratings have not been collected.

## 6. Live demonstration and reproducibility
The browser recorded a maximum-subarray witness [-5,-2,-7]: the empty-segment bug returns 0, but the legal optimum is -2. The interface displays the recorded trace, expected output, optimal segment and downloadable bundle. Another journey shows the graph path certificate, and a binary-search journey repairs a solution against a pinned witness. Browser verification also covers source hash round-trip, server-side cancellation, package review and mobile layout. The accepted gate records {tests} passing tests and {journeys} browser journeys.

![Recorded maximum-subarray interface](screenshots/max-subarray-desktop.png)

![Recorded graph analysis](screenshots/core-graph-trace.jpg)

The artifact is available at https://github.com/Hussam-alwan/AlgoXRay/tree/option-b. Checkout the exact measured revision above and use the pinned requirements, benchmark protocol, frozen manifest, raw run directory and separate audit. The published branch may advance; the commit, rather than the branch tip, identifies the evaluation.

## 7. Threats to validity and conclusion
The 30 files are not independent student submissions, and 450 executions are not 450 participants. Timeouts depend on execution environment. Detection is bounded and inconclusive is not correctness. Reduction is not guaranteed globally minimal. Specific observations include output symptoms, not validated root causes. The ablation is not a comparison against a general-purpose LLM. No human factuality, educational improvement, superiority, security isolation or first-of-kind claim is established. The results support technical feasibility of a reproducible local evidence workflow. Author review, independent annotation and final venue formatting remain pending.

## References
[1] Tillmann et al. Code Hunt: Searching for Secret Code for Fun (2014). https://www.microsoft.com/en-us/research/publication/code-hunt-searching-for-secret-code-for-fun/
[2] Guo. Online Python Tutor (SIGCSE 2013). https://research.google/pubs/online-python-tutor-embeddable-web-based-program-visualization-for-cs-education/
[3] Rivers and Koedinger. Data-Driven Hint Generation in Vast Solution Spaces (2017). https://www.krivers.net/research.html
[4] Liffiton et al. CodeHelp (2023). https://arxiv.org/abs/2308.06921
[5] CodeAid (CHI 2024). https://doi.org/10.1145/3613904.3642773
[6] MacIver and Donaldson. Test-case Reduction via Test-case Generation (ECOOP 2020). https://doi.org/10.4230/LIPIcs.ECOOP.2020.13
[7] Ko and Myers. Debugging Reinvented (ICSE 2008). https://doi.org/10.1145/1368088.1368130
[8] Abreu, Zoeteweij and van Gemund. On the Accuracy of Spectrum-based Fault Localization (2007). https://doi.org/10.1109/TAICPART.2007.4344104
[9] Orvalho et al. Counterexample Guided Program Repair Using Zero-Shot Learning and MaxSAT-based Fault Localization (AAAI 2025). https://doi.org/10.1609/AAAI.V39I1.32046
[10] Orvalho, Janota and Manquinho. MENTOR (JSS 2026). https://doi.org/10.1016/j.jss.2025.112690
"""
    write(output/"manuscript-v2.md",manuscript)
    reviewer=f"""# Paper 20 — measured response draft
For author approval only; not sent.

Reviewer 1: thank you for the poster recommendation. The artifact now has a verified live demonstration and measured poster draft.

Reviewer 3:
- **Single problem and authored bug:** three bounded problem contracts and {summary['corpus_count']} files evaluated. {summary_text} The corpus remains partly assistant-authored; an independent student corpus has not been collected.
- **Generator tailored to bug:** legal general-purpose random and Hypothesis generation are separate paired arms; the full arm enables reduction and trace. Both successful and unsuccessful outcomes are retained.
- **Actual execution trace:** recorded Python frames, line/call/return/exception events, source hashes, replay, and evidence export. Added narrow invariant observations, arithmetic read/write links and spectrum ranking; no arbitrary causal diagnosis claim.
- **Screenshots and artifact:** {tests} tests and {journeys} browser journeys passed on {commit}. Actual captures and exports are included. Confirm anonymization and artifact permissions before sharing.
- **Missing literature / uncited references:** the draft explicitly cites Code Hunt, Python Tutor, ITAP, CodeHelp, CodeAid, Hypothesis, Whyline, spectrum localization, AAAI 2025 repair and MENTOR. Bibliographic formatting still requires author review.
- **Length and future-work focus:** concise implemented-system manuscript and measured poster prepared. Verify poster-specific page and camera-ready requirements before submission.

Replace unsupported legacy claims rather than retroactively attributing these new results to the original submission. No independent human review or learner study is claimed.
"""
    write(output/"reviewer-response-v2.md",reviewer)
    demo=f"""# عرض AlgoX-Ray (خمس دقائق)
0:00–0:40: اشرح الفرق بين كشف خطأ وتحديد سببه.
0:40–1:50: اعرض شاهد Dijkstra، الكلفة المتوقعة والمرصودة والأحداث الفعلية.
1:50–2:40: افتح Binary Search، اختر ملاحظة مرتبطة بحدث، وعدّل الحل وافحص الشاهد نفسه.
2:40–3:35: Maximum Subarray بالمدخل [-5,-2,-7]؛ المتوقع -2 والمرصود 0 في رحلة المتصفح المحفوظة.
3:35–4:20: اعرض إلغاء التنفيذ، تصدير الدليل، ومراجعة عقد مسألة.
4:20–5:00: {summary['run_count']} تشغيل على {summary['corpus_count']} ملفاً، كشف {total['buggy_found']}/{total['buggy_runs']}، اتهامات الصحيح {total['control_accusations']}/{total['control_runs']}، الملاحظات المحددة {specific} في المسار الكامل. لا تدّع دقة السبب الجذري أو وجود تقييم بشري.
الإصدار المقاس: {commit}.
"""
    write(output/"demo-v2-ar.md",demo)

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
