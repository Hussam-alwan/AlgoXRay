"""Live Playwright integration against a temporary local server and isolated package store."""
import argparse,json,os,re,subprocess,sys,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",required=True);parser.add_argument("--port",type=int,default=8798);args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}"
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    env={**os.environ,"ALGOXRAY_V4_PACKAGE_STORE":str(out/"test-only-packages")}
    with (out/"server.log").open("wb") as log:
        server=subprocess.Popen([sys.executable,"-m","uvicorn","algoxray.api:app","--host","127.0.0.1","--port",str(args.port)],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                try:
                    with urllib.request.urlopen(url+"/api/health",timeout=1) as r:
                        if r.status==200:break
                except OSError:time.sleep(.1)
            else:raise RuntimeError("Server not ready")
            return test(url,out)
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill()
def test(url,out):
    errors=[];external=[];checks=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1400,"height":1000},accept_downloads=True)
        page.on("pageerror",lambda e:errors.append(str(e)))
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route)
        page.goto(url+"/v4")
        expect(page.locator("#package")).to_have_value(re.compile("hamburgers"),timeout=15000)
        page.locator("#problem-url").fill("https://example.com/problem")
        with page.expect_response(lambda r:r.url.endswith("/packages/intake"),timeout=10000) as response:
            page.locator("#import-problem").click()
        assert response.value.status==422
        checks.append("external_import_allowlist")
        page.locator("#model").select_option("openai/gpt-oss-120b")
        with page.expect_response(lambda r:r.url.endswith("/packages/draft"),timeout=10000) as response:
            page.locator("#draft").click()
        assert response.value.status==403
        page.locator("#model").select_option("qwen2.5-coder:7b")
        checks.append("explicit_cloud_consent")
        page.locator("#model").select_option("qwen-cloud")
        with page.expect_response(lambda r:r.url.endswith("/packages/draft"),timeout=10000) as response:
            page.locator("#draft").click()
        assert response.value.status==403
        page.locator("#model").select_option("qwen2.5-coder:7b")
        checks.append("qwen_cloud_requires_explicit_consent")
        with page.expect_response(lambda r:r.url.endswith("/cache/clear"),timeout=10000) as response:
            page.locator("#clear-cache").click()
        assert response.value.json()["entries"]==0
        page.locator("#use-cache").check()
        assert page.locator("#use-cache").is_checked()
        page.locator("#use-cache").uncheck()
        checks.append("local_memory_cache_controls")

        page.locator("#demo").select_option("sum")
        page.locator("#load").click()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=10000) as response:
            page.locator("#approve").click()
        assert response.value.status==403
        checks.append("review_required")
        with page.expect_response(lambda r:r.url.endswith("/packages/audit"),timeout=10000) as response:
            page.locator("#audit-reference").click()
        assert response.value.status==403
        checks.append("reference_audit_review_required")
        original_package=page.locator("#package").input_value()
        audit_package=json.loads(original_package)
        audit_package["reference_alt"]="import sys\nvalues=list(map(int,sys.stdin.read().split()))\nprint(sum(values[1:]))"
        page.locator("#package").fill(json.dumps(audit_package))
        page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/audit"),timeout=60000) as response:
            page.locator("#audit-reference").click()
        audited=response.value.json()
        assert audited["status"]=="bounded_reference_agreement",audited
        assert all(x["agreed"] for x in audited["checks"])
        checks.append("distinct_reference_audit")
        page.locator("#package").fill(original_package)

        page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=35000) as response:
            page.locator("#approve").click()
        assert response.value.ok and response.value.json()["status"]=="approved_by_owner",response.value.json()
        expect(page.locator("#packages")).to_have_value(re.compile(r"^[a-f0-9]{64}$"),timeout=15000)
        checks.append("synthetic_author_approval")
        page.locator("#trusted").check()
        page.locator("#count").fill("2")
        with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:
            page.locator("#run").click()
        data=response.value.json();assert data["status"]=="observed_mismatch",data.get("status")
        page.locator("#results").wait_for()
        assert page.locator("#graph .node").count()>0
        assert data["replay_count"]==3
        checks.append("replay_witness_and_graph")
        assert page.locator("#matrix-view td").count()>0
        assert page.locator("#cmp-student-code .active").count()==1
        assert page.locator("#cmp-reference-code .active").count()==1
        student_step=page.locator("#cmp-student").input_value()
        page.locator("#cmp-reference").fill(str(int(page.locator("#cmp-reference").get_attribute("max"))))
        assert page.locator("#cmp-student").input_value()==student_step
        checks.append("independent_side_by_side_trace_and_array")
        assert "restricted_syntactic_cfg" in page.locator("#static-cfg").inner_text()
        checks.append("static_cfg_separate")
        page.locator("#graph .node").last.click()
        assert page.locator("#code .active").count()==1
        page.locator("#reference").click()
        assert page.locator("#graph .node").count()>0
        assert "print(sum(a))" in page.locator("#code").inner_text()
        checks.append("student_reference_navigation")
        with page.expect_download() as dl:page.locator("#export").click()
        dl.value.save_as(str(out/"evidence.json"))
        assert json.loads((out/"evidence.json").read_text())["package_sha256"]==data["package_sha256"]
        checks.append("export")
        original=page.locator("#source").input_value()
        page.locator("#candidate").fill("n=int(input())\na=list(map(int,input().split()))\nprint(sum(a))")
        with page.expect_response(lambda r:r.url.endswith("/repair/verify"),timeout=10000) as response:
            page.locator("#verify-patch").click()
        assert response.value.status==403
        checks.append("patch_review_required")
        page.locator("#patch-reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/repair/verify"),timeout=90000) as response:
            page.locator("#verify-patch").click()
        assert response.value.json()["status"]=="passed_named_tests",response.value.json()
        assert page.locator("#source").input_value()==original
        checks.append("manual_patch_verification_original_unchanged")
        expect(page.locator("#repair-history")).to_have_value(re.compile(r"^[a-f0-9]{64}$"),timeout=15000)
        page.locator("#load-repair").click()
        expect(page.locator("#repair-history-view")).to_contain_text("passed_named_tests")
        checks.append("immutable_repair_history")
        # Timings must be present for both sides and survive evidence export.
        assert data["student_graph"]["profile"]["status"]=="complete"
        assert data["reference_graph"]["profile"]["status"]=="complete"
        assert page.locator("#profile-table tbody tr").count()>0
        page.locator("#student").click()
        page.locator("#profile-clock").select_option("cpu")
        page.locator("#profile-cost").select_option("self")
        page.locator("#profile-table tbody button").first.click()
        assert page.locator("#code .profile-range").count()>0
        checks.append("block_timing_source_link_and_clocks")
        page.locator("#profile-case").fill(json.dumps({"n":3,"a":[1,2,3]}))
        page.locator("#source").fill("n=int(input())\ndef f(n):\n    if n==0:\n        return 1\n    return n*f(n-1)\nprint(f(n))\n")
        page.locator("#trusted").check()
        with page.expect_response(lambda r:r.url.endswith("/v4/profile"),timeout=35000) as response:
            page.locator("#profile-run").click()
        profiled=response.value.json()
        assert profiled["status"]=="profiled_execution" and profiled["kind"]=="match",profiled.get("status")
        expect(page.locator("#repair-panel")).to_be_hidden()
        expect(page.locator("#profile-summary")).to_contain_text("complete")
        events=profiled["witness"]["student"]["events"]
        pos=next(i for i,e in enumerate(events) if e["function"]=="f" and e["kind"]=="line")
        page.locator("#slider").fill(str(pos))
        assert "f" in page.locator("#stack").inner_text()
        checks.append("correct_code_profile_recursion_and_call_stack")
        frame_id=events[pos]["frame_id"]
        page.locator("#graph-frame").select_option(frame_id)
        page.locator("#graph-kind").select_option("line")
        assert page.locator("#graph .node").count()>0
        assert all(frame_id in x for x in page.locator("#graph .node").all_text_contents())
        page.locator("#graph-layout").select_option("compact")
        assert page.locator("#graph svg").get_attribute("viewBox").split()[2]=="680"
        assert page.locator("#previous-locals").inner_text()
        page.locator("#graph .node").last.click()
        assert page.locator("#code .active").count()==1
        page.locator("#graph-frame").select_option("all")
        page.locator("#graph-kind").select_option("all")
        page.locator("#graph-layout").select_option("timeline")
        checks.append("graph_frame_event_layout_and_snapshot_controls")

        page.locator("#profiling").screenshot(path=str(out/"profile-table.png"))
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.body.scrollWidth")<=390
        page.locator("#profiling").screenshot(path=str(out/"profile-mobile.png"))
        page.set_viewport_size({"width":1400,"height":1000})
        with page.expect_download() as dl:page.locator("#profile-csv").click()
        dl.value.save_as(str(out/"timing.csv"))
        assert "inclusive_cpu_ns" in (out/"timing.csv").read_text(encoding="utf-8-sig")
        checks.append("profile_csv_export")
        page.locator("#source").fill("s=0\nfor i in range(200):\n    s+=i\nprint(s)\n")
        with page.expect_response(lambda r:r.url.endswith("/v4/profile"),timeout=35000) as response:
            page.locator("#profile-run").click()
        partial=response.value.json()
        assert partial["witness"]["student"]["trace_status"]=="truncated"
        assert partial["witness"]["student"]["profile"]["status"]=="complete"
        loops=partial["student_graph"]["loop_summary"]["loops"]
        assert any(x.get("observed_body_entries",0)>0 and x["status"]=="observed_partial_trace" for x in loops)
        assert page.locator("#loops").inner_text()
        checks.append("loop_observations_disclose_partial_counts")

        checks.append("complete_timing_with_truncated_visual_trace")
        page.locator("#ai").uncheck()
        page.locator("#source").fill("l=1\nr=2\nwhile l<r:\n    mid=(l+r)//2\n    l=mid\n")
        with page.expect_response(lambda r:r.url.endswith("/v4/profile"),timeout=35000) as response:
            page.locator("#profile-run").click()
        timeout_diagnosis=response.value.json()
        assert timeout_diagnosis["kind"]=="timeout" and timeout_diagnosis["ai_status"]=="disabled"
        finding=timeout_diagnosis["execution_diagnostics"]["findings"][0]
        assert finding["condition_values"]=={"l":1,"r":2} and finding["assignments"][0]["line"]==5
        expect(page.locator("#execution-findings")).to_contain_text("l = 1")
        page.get_by_role("button",name="L5 · l=mid",exact=True).click()
        assert page.locator("#code .profile-range").count()==1
        expect(page.locator("#code .active")).to_contain_text("l=mid")
        checks.append("timeout_progress_findings_and_assignment_source_link")
        expect(page.locator("#ai-state")).to_contain_text("لم يُطلب")
        expect(page.locator("#facts")).to_contain_text("لم يُطلب")
        expect(page.locator("#probes")).to_contain_text("مدخل واحد")
        checks.append("disabled_ai_panels_explain_unrequested_diagnosis")
        page.locator("#execution-diagnostics").screenshot(path=str(out/"timeout-finding.png"))

        page.locator("#source").fill("while True: pass")
        with page.expect_response(lambda r:r.url.endswith("/v4/profile"),timeout=35000) as response:
            page.locator("#profile-run").click()
        timed=response.value.json()
        assert timed["witness"]["student"]["status"]=="timeout"
        assert timed["witness"]["student"]["profile"]["status"]=="partial"
        expect(page.locator("#profile-summary")).to_contain_text("partial")
        checks.append("timeout_profile_is_explicitly_partial")
        page.screenshot(path=str(out/"desktop.png"),full_page=True)
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.body.scrollWidth")<=390
        checks.append("mobile")
        page.screenshot(path=str(out/"mobile.png"),full_page=True)
        page.set_viewport_size({"width":1400,"height":1000})
        page.locator("#source").fill("while True: pass")
        page.locator("#trusted").check()
        with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=30000) as response:
            page.locator("#run").click()
            page.locator("#cancel").click()
        assert response.value.json()["status"]=="cancelled",response.value.json()
        checks.append("server_cancellation")
        assert not errors,errors
        assert not external,external
        browser.close()
    report={"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,"scope":"Synthetic approval and repair tests; no human research rating"}
    (out/"report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
if __name__=="__main__":main()
