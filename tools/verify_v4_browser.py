"""Playwright acceptance against the live V4 loopback instance."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser
def main():
    url="http://127.0.0.1:8002"
    out=Path("results/v4-browser");out.mkdir(parents=True,exist_ok=True)
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
        page.locator("#package").wait_for()
        expect(page.locator("#package")).to_have_value(re.compile("hamburgers"),timeout=15000)
        page.locator("#demo").select_option("sum")
        page.locator("#load").click()
        page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=35000) as response:
            page.locator("#approve").click()
        assert response.value.ok and response.value.json()["status"]=="approved_by_owner",response.value.json()
        expect(page.locator("#packages")).to_have_value(re.compile(r"^[a-f0-9]{64}$"),timeout=15000)
        checks.append("author_approval")
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
        page.screenshot(path=str(out/"desktop.png"),full_page=True)
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.body.scrollWidth")<=390
        checks.append("mobile")
        page.screenshot(path=str(out/"mobile.png"),full_page=True)
        assert not errors,errors
        assert not external,external
        browser.close()
    report={"status":"passed","checks":checks,"page_errors":errors,"external_requests":external}
    (out/"report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
if __name__=="__main__":main()
