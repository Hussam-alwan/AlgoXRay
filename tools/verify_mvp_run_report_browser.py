"""Browser round trip of local run report, explicit replay and integrity rejection."""
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser
P={"manifest":{"id":"report_roundtrip","title":"Double","statement":"Read n and print twice n. n in 0..9.",
    "fields":[{"name":"n","kind":"int","min":0,"max":9}],"lines":[["n"]],"output":"tokens"},
    "reference":"print(2*int(input()))","controls":[{"case":{"n":0},"expected":"0"},{"case":{"n":1},"expected":"2"}]}
def test(url,temp):
    checks=[];errors=[];external=[];analyses=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1400,"height":1000},accept_downloads=True)
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("request",lambda req:analyses.append(req.url) if req.url.endswith("/api/v4/analyze") else None)
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route);page.goto(url+"/v4?view=expert")
        expect(page.locator("#package")).not_to_be_empty(timeout=15000)
        page.locator("#package").fill(json.dumps(P));page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=35000) as response:page.locator("#approve").click()
        approved=response.value.json();assert approved["status"]=="approved_by_owner",approved
        expect(page.locator("#packages")).to_have_value(approved["key"])
        page.locator("#source").fill(P["reference"]);page.locator("#trusted").check()
        page.locator("#analysis-case").fill('{"n":2}');page.locator("#reduce-count").fill("0")
        def analyze():
            with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:page.locator("#run").click()
            return response.value.json()
        good=analyze();assert good["status"]=="no_witness_found",good
        expect(page.locator("#run-report-summary")).to_contain_text("no_witness_found")
        expect(page.locator("#run-report-stages")).to_contain_text("not_run")
        checks.append("no_witness_report")
        page.locator("#source").fill("print(int(input()))")
        page.locator("#trusted").check()
        bad=analyze();assert bad["status"]=="observed_mismatch",bad.get("status")
        expect(page.locator("#run-report-summary")).to_contain_text("observed_mismatch")
        with page.expect_download() as download:page.locator("#run-report-export").click()
        saved=temp/"report.json";download.value.save_as(saved)
        envelope=json.loads(saved.read_text(encoding="utf-8"));assert json.loads(envelope["payload"])["run_report"]["run_id"]==bad["analysis_id"]
        page.reload();expect(page.locator("#packages")).to_have_value(approved["key"],timeout=15000)
        n=len(analyses)
        page.locator("#run-report-import").set_input_files(saved)
        expect(page.locator("#reopen-summary")).to_contain_text("NOT authenticated")
        page.locator("#prepare-replay").click()
        expect(page.locator("#source")).to_have_value("print(int(input()))")
        expect(page.locator("#analysis-case")).to_have_value('{"n":2}')
        expect(page.locator("#reduce-count")).to_have_value("0")
        expect(page.locator("#trusted")).not_to_be_checked()
        expect(page.locator("#ai")).not_to_be_checked()
        assert len(analyses)==n
        checks.append("local_import_prepares_without_execution")
        page.locator("#trusted").check();again=analyze()
        assert again["status"]=="observed_mismatch" and again["witness"]["case"]==bad["witness"]["case"]
        assert again["analysis_id"]!=bad["analysis_id"]
        checks.append("explicit_replay_new_run_identity")
        envelope["payload"]+=" "
        tampered=temp/"tampered.json";tampered.write_text(json.dumps(envelope),encoding="utf-8")
        page.locator("#run-report-import").set_input_files(tampered)
        expect(page.locator("#reopen-summary")).to_contain_text("Invalid envelope or content hash")
        expect(page.locator("#prepare-replay")).to_be_hidden()
        checks.append("tampered_hash_rejected")
        assert not errors,errors
        assert not external,external
        browser.close()
    return {"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,
            "scope":"Real local browser and Docker; replay requires explicit source review; checksum is not authenticity.",
            "no_witness":good["run_report"],"original":bad["run_report"],"replay":again["run_report"]}
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8791);parser.add_argument("--out",default="docs/mvp-evidence/run-report-browser.json");args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}"
    with tempfile.TemporaryDirectory(prefix="algoxray-report-browser-") as t:
        temp=Path(t);env={**os.environ,"ALGOXRAY_V4_PACKAGE_STORE":str(temp/"packages")}
        with (temp/"server.log").open("wb") as log:
            process=subprocess.Popen([sys.executable,"-m","uvicorn","algoxray.api:app","--host","127.0.0.1","--port",str(args.port),"--log-level","warning"],env=env,stdout=log,stderr=log)
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(url+"/api/health",timeout=1) as r:
                            if r.status==200:break
                    except OSError:time.sleep(.1)
                else:raise RuntimeError("Server not ready")
                report=test(url,temp)
                out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding="utf-8")
                print(json.dumps({k:report[k] for k in ("status","checks","page_errors","external_requests")}),flush=True)
            finally:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
