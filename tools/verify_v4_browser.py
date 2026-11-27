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
        page.locator("#demo").select_option("sum")
        page.locator("#load").click()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=10000) as response:
            page.locator("#approve").click()
        assert response.value.status==403
        checks.append("review_required")
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
