"""Real local guided comprehensive acceptance; no model/cloud requests."""
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser

def test(url,folder):
    checks=[];errors=[];external=[];posts=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1000},accept_downloads=True)
        page.on("pageerror",lambda e:errors.append(str(e)))
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route)
        page.on("request",lambda req:posts.append(req.url.removeprefix(url)) if req.method=="POST" else None)
        page.goto(url+"/v4")
        expect(page.locator("body")).to_have_class("guided-workspace")
        expect(page.locator("#package")).not_to_be_empty(timeout=15000)
        expect(page.locator('[data-mode="full"]')).to_have_attribute("aria-pressed","true")
        expect(page.locator("#import-problem")).to_be_visible()
        expect(page.locator("#trusted")).to_be_hidden()
        expect(page.locator("#reviewed")).to_be_hidden()
        expect(page.locator("#ux-separate-modes")).not_to_have_attribute("open","")
        assert not posts
        expect(page.locator("#ux-tab-input")).to_have_attribute("aria-selected","true")
        assert page.locator("[role=tab]:visible").count()==2
        expect(page.locator("#ux-tab-summary")).to_be_hidden()
        page.screenshot(path=str(folder/"comprehensive-initial.jpg"),type="jpeg",quality=70)
        checks.append("default_comprehensive_no_automatic_execution")
        page.locator("#ux-manual-problem > summary").click()
        page.locator("#ux-problem-library > summary").click()
        page.locator("#load").click()
        page.locator("#ux-problem-library > summary").click()
        # Keep a small deterministic fixture, and minimize test execution time.
        page.locator("#ux-tab-advanced").click()
        page.locator("#ux-tools > summary").click()
        page.locator("#ux-analysis-options > summary").click()
        page.locator("#analysis-case").fill('{"n":3,"a":[1,2,3]}')
        page.locator("#reduce-count").fill("0")
        page.locator("#ux-analysis-options > summary").click()
        page.locator("#ux-timing-options > summary").click()
        page.locator("#timing-repetitions").fill("1")
        page.locator("#ux-timing-options > summary").click()
        page.locator("#ux-tools > summary").click()
        page.locator("#ux-tab-input").click()
        # First action on a new draft may validate structure only.
        before=len(posts)
        page.locator("#ux-run-full").click()
        expect(page.locator("#ux-run-full")).to_be_enabled(timeout=30000)
        expect(page.locator("#ux-preview-reference")).to_have_attribute("open","")
        expect(page.locator("#ux-preview-controls")).to_have_attribute("open","")
        expect(page.locator("#package")).to_be_hidden()
        assert posts[before:]==["/api/v4/packages/preflight"],posts[before:]
        expect(page.locator("#ux-tab-input")).to_have_attribute("aria-selected","true")
        expect(page.locator("#ux-tab-summary")).to_be_hidden()
        expect(page.locator("#ux-full-progress")).to_be_visible()
        checks.append("new_draft_preflight_requires_visible_review_no_worker")
        page.screenshot(path=str(folder/"comprehensive-review.jpg"),type="jpeg",quality=70)
        def tab(name):page.locator("#ux-tab-"+name).click()
        def run():
            tab("input")
            start=len(posts)
            page.locator("#ux-run-full").click()
            expect(page.locator("#ux-run-full")).to_be_enabled(timeout=150000)
            expect(page.locator("#ux-tab-summary")).to_have_attribute("aria-selected","true",timeout=150000)
            assert page.locator("[role=tabpanel]:visible").count()==1
            assert page.locator("[role=tab]:visible").count()==6
            tab("advanced")
            expect(page.locator("#ux-full-export")).to_be_visible()
            with page.expect_download(timeout=15000) as dl:page.locator("#ux-full-export").click()
            path=folder/"report.json";dl.value.save_as(path)
            tab("summary")
            return json.loads(path.read_text(encoding="utf-8")),posts[start:]
        wrong,requests=run()
        assert wrong["status"]=="completed",wrong.get("error")
        assert requests==["/api/v4/packages/preflight","/api/v4/packages/approve","/api/v4/analyze","/api/v4/benchmark"],requests
        assert [v["name"] for v in wrong["phases"]]==["analysis","benchmark"]
        a,b=[v["data"] for v in wrong["phases"]]
        assert a["status"]=="observed_mismatch"
        assert a["witness"]["case"]==b["points"][0]["case"]
        assert a["witness"]["stdin"]==b["points"][0]["stdin"]
        assert b["points"][0]["correctness"]=="recorded_mismatch"
        assert a["run_report"]["source_sha256"]==b["run_report"]["source_sha256"]
        assert a["package_sha256"]==b["package_sha256"]
        assert all(w["requested_mode"]=="benchmark_uninstrumented" for w in b["run_report"]["workers"])
        expect(page.locator("#results")).to_be_visible()
        expect(page.locator("#benchmark-results")).to_be_hidden()
        expect(page.locator("#actual")).to_have_text("3\n")
        expect(page.locator("#expected")).to_have_text("6\n")
        expect(page.locator("#ux-full-trace")).to_contain_text("\u0625\u0639\u0627\u062f\u0629")
        page.locator("#ux-full-result").scroll_into_view_if_needed()
        page.screenshot(path=str(folder/"comprehensive-result.jpg"),type="jpeg",quality=70)
        checks.append("wrong_solution_single_action_shared_witness_and_uninstrumented_measurement")
        expect(page.locator("#ux-story-details")).not_to_have_attribute("open","")
        expect(page.locator("#story-timeline")).to_be_hidden()
        expect(page.locator("#story-findings")).to_be_hidden()
        expect(page.locator("#ux-summary-trace")).to_be_visible()
        page.locator("#ux-summary-trace").click()
        expect(page.locator("#ux-tab-execution")).to_have_attribute("aria-selected","true")
        expect(page.locator("#story-timeline")).to_be_visible()
        expect(page.locator("#story-rail button")).to_have_count(len(a["witness"]["student"]["events"]))
        events=a["witness"]["student"]["events"]
        chosen=next(i for i,e in enumerate(events) if isinstance(e.get("locals",{}).get("a"),list))
        page.locator("#story-rail button").nth(chosen).click()
        expect(page.locator("#story-step")).to_have_text(f"{chosen+1} / {len(events)}")
        expect(page.locator('[data-variable="a"] .story-cell strong')).to_have_text(["1","2","3"])
        n=len(posts)
        step=page.locator("#story-step").text_content()
        tab("fault")
        expect(page.locator("#story-findings")).to_be_visible()
        expect(page.locator("#story-shrink-bars .story-bar-row")).to_have_count(1+len(a["reduction"]["accepted"]))
        page.screenshot(path=str(folder/"tabs-fault.jpg"),type="jpeg",quality=75)
        tab("performance")
        expect(page.locator("#story-performance")).to_be_visible()
        expect(page.locator("#story-performance-bars .story-bar-row")).to_have_count(len(b["points"][0]["runs"]))
        page.screenshot(path=str(folder/"tabs-performance.jpg"),type="jpeg",quality=75)
        tab("execution")
        expect(page.locator("#story-step")).to_have_text(step)
        page.locator("#story-next").click()
        assert len(posts)==n
        page.screenshot(path=str(folder/"story-timeline.jpg"),type="jpeg",quality=75)
        # RTL keyboard navigation, one selected panel, no new run.
        page.locator("#ux-tab-execution").focus()
        page.keyboard.press("Home")
        expect(page.locator("#ux-tab-input")).to_have_attribute("aria-selected","true")
        page.keyboard.press("End")
        expect(page.locator("#ux-tab-advanced")).to_have_attribute("aria-selected","true")
        assert page.locator("[role=tabpanel]:visible").count()==1
        assert len(posts)==n
        checks.append("tab_keyboard_state_preservation_and_no_post")
        checks.append("visual_trace_array_cells_shrink_and_timing_from_report")

        # Changing code discards old comprehensive result. Same approved package
        # is reused, and the passing trace comes from the first search pair.
        tab("input")
        page.locator("#ux-problem-library > summary").click()
        page.locator("#correct").click()
        expect(page.locator("#ux-tab-summary")).to_be_hidden()
        expect(page.locator("#ux-full-result")).to_be_hidden()
        expect(page.locator("#results")).to_be_hidden()
        good,requests=run()
        assert requests==["/api/v4/analyze","/api/v4/benchmark"],requests
        assert good["status"]=="completed"
        a2,b2=[v["data"] for v in good["phases"]]
        assert a2["status"]=="no_witness_found"
        example=a2["example_observation"]
        assert example["reused_search_trace"] and example["kind"]=="match"
        assert a2["run_report"]["physical_executions"]==2
        assert example["witness"]["case"]==b2["points"][0]["case"]
        assert b2["points"][0]["correctness"]=="recorded_match"
        expect(page.locator("#results")).to_be_visible()
        tab("performance")
        expect(page.locator("#benchmark-results")).to_be_visible()
        checks.append("passing_solution_reuses_search_pair_no_extra_profile_or_approval")
        tab("fault")
        expect(page.locator("#story-findings")).to_have_count(0)
        expect(page.locator("#ux-tab-panel-fault .ux-tab-empty")).to_be_visible()
        tab("execution")
        expect(page.locator("#story-timeline")).to_be_visible()
        checks.append("passing_trace_not_labeled_as_fault")

        # Exact already-approved draft can be reused without another approval.
        tab("input")
        page.locator("#ux-full-target").select_option("draft")
        page.locator("#ux-package-review").evaluate("(el)=>el.open=false")
        repeated,requests=run()
        assert repeated["preflight"]["already_approved"] is True
        assert requests==["/api/v4/packages/preflight","/api/v4/analyze","/api/v4/benchmark"],requests
        checks.append("matching_approved_draft_reused_without_review_repetition")
        # A stale or malformed draft must never trigger approval/worker requests.
        tab("input")
        page.locator("#ux-full-target").select_option("draft")
        page.locator("#ux-package-review").evaluate("(el)=>el.open=true")
        page.locator("#ux-package-json").evaluate("(el)=>el.open=true")
        old=page.locator("#package").input_value()
        draft=json.loads(old);draft["reference"]=""
        page.locator("#package").fill(json.dumps(draft))
        start=len(posts)
        page.locator("#ux-run-full").click()
        expect(page.locator("#ux-run-full")).to_be_enabled(timeout=30000)
        assert posts[start:]==["/api/v4/packages/preflight"],posts[start:]
        expect(page.locator("#results")).to_be_hidden()
        page.locator("#package").fill(old)
        page.locator("#ux-new-problem").evaluate("(el)=>el.open=true")
        page.locator("#statement").fill("Different problem text")
        start=len(posts)
        page.locator("#ux-run-full").click()
        assert posts[start:]==[],posts[start:]
        checks.append("invalid_and_stale_draft_blocked_before_execution")
        # Reference/controls form validation is non-executing and does not grant approval.
        page.locator("#statement").fill(json.loads(old)["manifest"]["statement"])
        page.locator("#package").fill(old)
        page.locator("#ux-package-review").evaluate("(el)=>el.open=true")
        page.locator("#ux-human-review").evaluate("(el)=>el.open=true")
        expect(page.locator("#ux-reference-source")).to_have_value(json.loads(old)["reference"])
        first=page.locator("#ux-control-form-list .ux-human-test textarea").first
        initial=first.input_value()
        first.fill("999")
        start=len(posts)
        page.locator("#ux-save-controls").click()
        assert posts[start:]==[]
        first.fill(initial)
        with page.expect_response(lambda r:r.url.endswith("/packages/preflight"),timeout=15000) as response:
            page.locator("#ux-save-controls").click()
        assert response.value.status==200
        expect(page.locator("#ux-save-controls")).to_be_enabled()
        assert posts[start:]==["/api/v4/packages/preflight"],posts[start:]
        assert json.loads(page.locator("#package").input_value())==json.loads(old)
        checks.append("structured_review_form_preflight_only")

        # Test a failed timing request preserves diagnosis and export, no implicit retry.
        page.locator("#statement").fill(json.loads(old)["manifest"]["statement"])
        page.locator("#ux-full-target").select_option("approved")
        def fail_bench(r):
            r.fulfill(status=503,content_type="application/json",body=json.dumps({"detail":"Fixture measurement failure"}))
        page.route("**/api/v4/benchmark",fail_bench)
        partial,requests=run()
        assert partial["status"]=="partial"
        assert [v["name"] for v in partial["phases"]]==["analysis"]
        assert requests==["/api/v4/analyze","/api/v4/benchmark"]
        expect(page.locator("#results")).to_be_visible()
        expect(page.locator("#benchmark-results")).to_be_hidden()
        page.unroute("**/api/v4/benchmark",fail_bench)
        checks.append("measurement_failure_preserves_analysis")
        # Cancel a real in-flight diagnostic request; a timing request must not follow.
        tab("input")
        page.locator("#mutant").click()
        start=len(posts)
        with page.expect_request(lambda r:r.url.endswith("/v4/analyze"),timeout=15000):
            page.locator("#ux-run-full").click()
        tab("advanced")
        expect(page.locator("#cancel")).to_be_visible()
        page.locator("#cancel").click()
        expect(page.locator("#ux-run-full")).to_be_enabled(timeout=60000)
        expect(page.locator("#ux-tab-summary")).to_have_attribute("aria-selected","true")
        tab("advanced")
        expect(page.locator("#ux-full-export")).to_be_visible()
        with page.expect_download() as dl:page.locator("#ux-full-export").click()
        canceled_path=folder/"cancelled.json";dl.value.save_as(canceled_path)
        canceled=json.loads(canceled_path.read_text(encoding="utf-8"))
        assert canceled["status"]=="cancelled",canceled.get("status")
        assert "/api/v4/benchmark" not in posts[start:]
        checks.append("cancelled_analysis_does_not_start_measurement")
        # Mobile width must remain contained even when the result is present.
        page.set_viewport_size({"width":390,"height":844})
        tab("summary")
        page.evaluate("window.scrollTo(0,0)")
        page.screenshot(path=str(folder/"comprehensive-mobile.jpg"),type="jpeg",quality=70)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        checks.append("mobile_layout")
        assert not errors,errors
        assert not external,external
        browser.close()
    return {"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,
            "scope":"Synthetic local browser and real Docker; measurement failure simulated; no human usability study.",
            "wrong_case":a["witness"]["case"],"wrong_analysis_calls":a["run_report"]["physical_executions"],
            "wrong_benchmark_calls":b["run_report"]["physical_executions"],"passing_analysis_calls":a2["run_report"]["physical_executions"],
            "passing_benchmark_calls":b2["run_report"]["physical_executions"],"passing_reused_trace":example["reused_search_trace"],
            "wrong_measurement_correctness":b["points"][0]["correctness"],"passing_measurement_correctness":b2["points"][0]["correctness"]}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8795)
    parser.add_argument("--out",default="docs/mvp-evidence/comprehensive-ui-browser.json")
    parser.add_argument("--screenshots",default="results/comprehensive-ui-preview");args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}";folder=Path(args.screenshots);folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="algoxray-comprehensive-") as t:
        temp=Path(t);env={**os.environ,"ALGOXRAY_V4_PACKAGE_STORE":str(temp/"packages")}
        with (temp/"server.log").open("wb") as log:
            proc=subprocess.Popen([sys.executable,"-m","uvicorn","algoxray.api:app","--host","127.0.0.1","--port",str(args.port),"--log-level","warning"],env=env,stdout=log,stderr=log)
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(url+"/api/health",timeout=1) as r:
                            if r.status==200:break
                    except OSError:time.sleep(.1)
                else:raise RuntimeError("Server unavailable")
                report=test(url,folder)
                out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding="utf-8")
                print(json.dumps(report),flush=True)
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
