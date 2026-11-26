"""Option B browser acceptance, with isolated evidence and no historical overwrites."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright
from verify_browser import available_browser
from verify_core_browser import verify as core_verify

ROOT = Path(__file__).resolve().parents[1]

def run(output, port):
    output.mkdir(parents=True, exist_ok=False)
    url = f"http://127.0.0.1:{port}"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    with (output / "server.log").open("wb") as log:
        server = subprocess.Popen([sys.executable,"-m","uvicorn","algoxray.api:app","--host","127.0.0.1","--port",str(port)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                try:
                    with urllib.request.urlopen(url+"/api/health",timeout=1) as response:
                        if json.load(response)["status"]=="ready": break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError("Server did not start")
            core_verify(url,output/"core")
            journeys,errors,external=[],[],[]
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=available_browser(),headless=True)
                page=browser.new_page(viewport={"width":1440,"height":1000},accept_downloads=True)
                page.on("pageerror",lambda error:errors.append(str(error)))
                def route(request):
                    if request.request.url.startswith(url+"/"): request.continue_()
                    else:
                        external.append(request.request.url)
                        request.abort()
                page.route("**/*",route)
                page.goto(url+"/")
                page.locator("#connection-text").filter(has_text="المحرك متصل").wait_for()
                assert page.locator("[data-problem]").count()==3
                page.locator('[data-problem="max_subarray_v1"]').click()
                page.locator("#fixture-select").select_option("max_subarray_empty_bug")
                page.locator(".advanced summary").click()
                page.locator("#manual-case").check()
                page.locator("#shrink").uncheck()
                page.locator("#case-input").fill('{"array":[-5,-2,-7]}')
                def analyze():
                    with page.expect_response(lambda r:r.url==url+"/api/analyze" and r.request.method=="POST",timeout=70000) as received:
                        page.locator("#analyze-button").click()
                    assert received.value.ok,received.value.status
                    page.wait_for_function("!document.querySelector('#analyze-button').disabled")
                    return received.value.json()
                bundle=analyze()
                assert bundle["status"]=="witness_found" and bundle["observed_output"]==0 and bundle["expected_output"]==-2
                assert bundle["witness_explanation"]["segment"]==[-2]
                assert page.locator("#array-container .in-range").count()==1
                assert bundle["events"] and all("frame_id" in e for e in bundle["events"])
                assert bundle["verification"]["replay_matches"]==3
                with page.expect_download() as dl:
                    page.locator("#download-evidence").click()
                dl.value.save_as(str(output/"max-subarray-evidence.json"))
                assert json.loads((output/"max-subarray-evidence.json").read_text(encoding="utf-8"))["run_id"]==bundle["run_id"]
                page.screenshot(path=str(output/"max-subarray-desktop.png"),full_page=True)
                journeys.extend(["dynamic_problem_registry","max_subarray_wrong_answer","segment_visualization","frame_ids","replay_and_export"])
                page.locator("#fixture-select").select_option("max_subarray_correct")
                assert analyze()["manual_check"]["status"]=="pass"
                journeys.append("max_subarray_correct_control")
                page.locator('[data-problem="binary_search_v1"]').click()
                page.locator("#fixture-select").select_option("binary_missing_last")
                page.locator("#case-input").fill('{"array":[7],"target":7}')
                bundle=analyze()
                assert bundle["ranked_observations"]
                page.locator("#ranked-observations button").first.click()
                assert page.locator("#code-container .current").get_attribute("data-line")==str(bundle["ranked_observations"][0]["line"])
                journeys.append("ranked_observation_navigation")
                page.locator("#mode-custom").click()
                page.locator("#source-editor").fill("import time\ndef solve(x):\n    time.sleep(10)\n    return -1\n")
                page.locator("#trusted-local-code").check()
                # Exercise the real race: hold the custom-code session response until
                # cancellation was requested before the server registered the analysis.
                held=[]
                hold=lambda route:held.append(route)
                page.route(url+"/api/session",hold)
                with page.expect_response(lambda r:r.url==url+"/api/analyze" and r.request.method=="POST",timeout=20000) as received:
                    with page.expect_request(url+"/api/session"):
                        page.locator("#analyze-button").click()
                    page.locator("#cancel-analysis").wait_for(state="visible")
                    with page.expect_response(lambda r:r.url.endswith("/cancel") and r.status==404,timeout=5000):
                        page.locator("#cancel-analysis").click()
                    assert len(held)==1
                    with page.expect_response(lambda r:r.url.endswith("/cancel") and r.status==200,timeout=10000):
                        held[0].continue_()
                page.unroute(url+"/api/session",hold)
                cancelled=received.value.json()
                assert cancelled["status"]=="cancelled" and not cancelled["claims"],cancelled["status"]
                page.wait_for_function("!document.querySelector('#analyze-button').disabled")
                journeys.append("server_side_cancellation")
                page.locator("#mode-fixture").click()
                page.locator('[data-view="author"]').click()
                page.locator("#author-problem").select_option("max_subarray_v1")
                page.locator("#author-controls").fill('[{"case":{"array":[-5,-2]},"expected":-2}]')
                page.locator("#author-run").click()
                page.locator("#author-result").filter(has_text="checks_passed").wait_for()
                journeys.append("author_package_review")
                page.locator('[data-view="lab"]').click()
                page.set_viewport_size({"width":390,"height":844})
                assert page.evaluate("document.documentElement.scrollWidth")<=390
                page.screenshot(path=str(output/"mobile.png"),full_page=True)
                journeys.append("mobile")
                page.locator('[data-view="experiments"]').click()
                page.locator("#option-b-benchmark-state h2").wait_for()
                assert page.locator("#option-b-benchmark-state").is_visible()
                journeys.append("separate_option_b_results")
                assert not errors and not external,(errors,external)
                result={"status":"passed","journeys":journeys,"page_errors":errors,"external_requests":external,"browser":browser.version}
                (output/"browser.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
                print(json.dumps(result),flush=True)
                browser.close()
        finally:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--port",type=int,default=8793)
    args=parser.parse_args()
    run(args.out,args.port)
