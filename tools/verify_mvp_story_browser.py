"""Live guided visualization regression: one large legal witness reduces to three items."""
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser

SOURCE="n=int(input())\na=list(map(int,input().split()))\ntotal=0\nfor i in range(n-1):\n    total += a[i]\nprint(total)\n"
PACKAGE={"manifest":{"id":"story_sum","title":"Sum all values","statement":"Read n in 3..100, then n integers in 1..9. Print the sum of all values.",
    "fields":[{"name":"n","kind":"int","min":3,"max":100},{"name":"a","kind":"ints","min":1,"max":9,"length_from":"n"}],
    "lines":[["n"],["a"]],"output":"tokens"},
    "reference":"n=int(input())\na=list(map(int,input().split()))\nprint(sum(a))\n",
    "controls":[{"case":{"n":3,"a":[1,2,3]},"expected":"6"},{"case":{"n":4,"a":[1,2,3,4]},"expected":"10"}]}

def test(url,folder):
    checks=[];errors=[];external=[];posts=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1000},accept_downloads=True)
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("request",lambda req:posts.append(req.url.removeprefix(url)) if req.method=="POST" else None)
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route);page.goto(url+"/v4")
        expect(page.locator("#package")).not_to_be_empty(timeout=15000)
        expect(page.locator("#ux-tools")).not_to_have_attribute("open","")
        page.locator("#ux-manual-problem > summary").click()
        expect(page.locator("#statement")).to_be_visible()
        expect(page.locator("#ux-run-full")).to_be_visible()
        page.locator("#ux-source-file").set_input_files({"name":"sum.py","mimeType":"text/x-python","buffer":SOURCE.encode()})
        expect(page.locator("#source")).to_have_value(SOURCE)
        assert not posts
        checks.append("local_file_load_no_execution")
        page.locator("#statement").fill(PACKAGE["manifest"]["statement"])
        page.locator("#ux-package-review").evaluate("(e)=>e.open=true")
        page.locator("#ux-package-json").evaluate("(e)=>e.open=true")
        page.locator("#package").fill(json.dumps(PACKAGE))
        page.locator("#ux-package-json").evaluate("(e)=>e.open=false")
        page.locator("#problem-url").fill("https://codeforces.com/problemset/problem/4/A")
        n=len(posts);page.locator("#ux-run-full").click();assert len(posts)==n
        page.locator("#problem-url").fill("")
        checks.append("unimported_link_cannot_reuse_previous_problem")
        page.locator("#ux-tab-advanced").click()
        page.locator("#ux-tools > summary").click()
        page.locator("#ux-analysis-options > summary").click()
        page.locator("#analysis-case").fill(json.dumps({"n":100,"a":[1]*100}))
        page.locator("#reduce-count").fill("1")
        page.locator("#ux-analysis-options > summary").click()
        page.locator("#ux-timing-options > summary").click()
        page.locator("#timing-repetitions").fill("2")
        page.locator("#ux-timing-options > summary").click()
        page.locator("#ux-tools > summary").click()
        page.locator("#ux-tab-input").click()
        page.locator("#ux-run-full").click()
        expect(page.locator("#ux-run-full")).to_be_enabled(timeout=30000)
        expect(page.locator("#ux-preview-reference")).to_have_attribute("open","")
        expect(page.locator("#ux-preview-controls")).to_have_attribute("open","")
        with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=150000) as response:
            page.locator("#ux-run-full").click()
        result=response.value.json()
        assert result["status"]=="observed_mismatch",result.get("status")
        expect(page.locator("#ux-run-full")).to_be_enabled(timeout=120000)
        expect(page.locator("#ux-tab-summary")).to_have_attribute("aria-selected","true")
        page.locator("#ux-tab-performance").click()
        expect(page.locator("#story-performance")).to_be_visible()
        page.locator("#ux-tab-fault").click()
        assert result["original_case"]["n"]==100 and result["witness"]["case"]["n"]==3
        assert result["reduction"]["original_complexity"][0]==100 and result["reduction"]["reduced_complexity"][0]==3
        assert result["evidence_localization"]["ranked"][0]["line"]==4
        assert result["evidence_localization"]["loop_bounds"][0]["omitted_indices"]==[2]
        expect(page.locator("#story-shrink-bars .story-bar-row")).to_have_count(2)
        expect(page.locator("#story-shrink-bars .story-bar-row strong")).to_have_text(["100","3"])
        page.locator("#story-shrink-bars button").first.click()
        assert page.locator("#story-shrink-input").text_content()==result["original_witness"]["stdin"]
        page.locator("#story-shrink-bars button").last.click()
        assert page.locator("#story-shrink-input").text_content()==result["witness"]["stdin"]
        checks.append("real_100_to_3_visual_shrink_and_input_navigation")
        expect(page.locator("#story-code-map [data-rank='1'] code")).to_contain_text("range(n-1)")
        expect(page.locator("#story-findings .story-range .story-skipped strong")).to_have_text(["2"])
        expect(page.locator("#story-findings .story-range .story-read strong")).to_have_text(["0","1"])
        outputs=page.locator(".story-witness-outputs pre")
        assert outputs.all_text_contents()==[result["witness"]["student"]["stdout"],result["witness"]["reference"]["stdout"]]
        before_compare=list(posts)
        comparison=page.locator(".story-witness-traces")
        comparison.locator("summary").click()
        student,reference=comparison.get_by_role("slider").all()
        previous_reference=reference.input_value()
        student.focus()
        student.press("End")
        last=result["witness"]["student"]["events"][-1]
        expect(comparison.locator(".story-compare-snapshot").first).to_contain_text(last["event_id"])
        assert reference.input_value()==previous_reference and posts==before_compare
        comparison.locator("summary").click()
        checks.append("same_witness_outputs_and_independent_reference_navigation")
        n=len(posts)
        page.screenshot(path=str(folder/"story-localization.jpg"),type="jpeg",quality=75)
        page.locator("#story-findings button.story-finding").first.click()
        expect(page.locator("#ux-tab-execution")).to_have_attribute("aria-selected","true")
        expect(page.locator("#story-line")).to_contain_text("range(n-1)")
        checks.append("ranked_source_and_observed_index_omission")
        previous=page.locator("#story-step").text_content()
        page.locator("#story-play").click()
        page.wait_for_function("(old)=>document.querySelector('#story-step').textContent!==old",arg=previous)
        # Leaving the trace tab pauses playback and preserves its selected step.
        page.locator("#ux-tab-performance").click()
        step=page.locator("#story-step").text_content()
        page.wait_for_timeout(800)
        expect(page.locator("#story-step")).to_have_text(step)
        assert len(posts)==n
        expect(page.locator("#story-hotspots .story-bar-row").first).to_be_visible()
        page.locator("#story-hotspots .story-bar-row").first.click()
        expect(page.locator("#ux-tab-execution")).to_have_attribute("aria-selected","true")
        page.locator("#ux-tab-performance").click()
        expect(page.locator("#story-performance-bars .story-bar-row")).to_have_count(2)
        checks.append("playback_and_hotspots_reuse_recorded_evidence")
        # Advanced repair is an explicit separate operation. It must not erase
        # the original comprehensive result or restart analysis/measurement.
        page.locator("#ux-tab-advanced").click()
        page.locator("#ux-story-details > summary").click()
        page.locator("#ux-repair > summary").click()
        page.locator("#candidate").fill(PACKAGE["reference"])
        page.locator("#patch-reviewed").check()
        start=len(posts)
        with page.expect_response(lambda r:r.url.endswith("/repair/verify"),timeout=120000) as response:
            page.locator("#verify-patch").click()
        repair=response.value.json()
        assert repair["status"]=="passed_named_tests",repair.get("status")
        expect(page.locator("#verify-patch")).to_be_enabled(timeout=60000)
        expect(page.locator("#ux-tab-advanced")).to_have_attribute("aria-selected","true")
        expect(page.locator("#ux-full-export")).to_be_visible()
        assert posts[start:]==["/api/v4/repair/verify"],posts[start:]
        page.locator("#ux-tab-summary").click()
        expect(page.locator("#actual")).to_have_text("2\n")
        expect(page.locator("#expected")).to_have_text("3\n")
        page.locator("#ux-tab-performance").click()
        expect(page.locator("#story-performance-bars .story-bar-row")).to_have_count(2)
        page.locator("#ux-tab-execution").click()
        expect(page.locator("#story-line")).to_be_visible()
        checks.append("advanced_repair_preserves_original_tabs")
        page.set_viewport_size({"width":390,"height":844})
        page.locator("#ux-tab-execution").click()
        page.locator("#story-timeline").scroll_into_view_if_needed()
        page.screenshot(path=str(folder/"story-mobile-result.jpg"),type="jpeg",quality=75)
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
        # All tabs are reachable on a narrow viewport; the strip scrolls independently.
        for name in ("summary","fault","performance","advanced","input","execution"):
            page.locator("#ux-tab-"+name).click()
            expect(page.locator("#ux-tab-"+name)).to_have_attribute("aria-selected","true")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),name
        page.evaluate("window.scrollTo(0,document.body.scrollHeight)")
        assert page.locator("#ux-tab-list").bounding_box()["y"]>=-2
        checks.append("mobile_result_width_and_sticky_tabs")
        assert not errors,errors
        assert not external,external
        browser.close()
    return {"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,
            "scope":"Synthetic live Docker development example; not human usability or research accuracy evidence.",
            "original":result["original_case"],"reduced":result["witness"]["case"],
            "reduction":result["reduction"],"localization":result["evidence_localization"],
            "student_trace_status":result["witness"]["student"]["trace_status"]}
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8798)
    parser.add_argument("--out",default="docs/mvp-evidence/story-visual-browser.json")
    parser.add_argument("--screenshots",default="results/story-ui-preview");args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}";folder=Path(args.screenshots);folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="algoxray-story-") as t:
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
                print(json.dumps({k:report[k] for k in ("status","checks","page_errors","external_requests","reduced")}),flush=True)
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
