"""Live browser smoke for source tree links and evidence-ranked loop bounds."""
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser

SOURCE="n=int(input())\na=list(map(int,input().split()))\ntotal=0\nfor i in range(n-1):\n    total += a[i]\nprint(total)\n"
PACKAGE={"manifest":{"id":"sum_all_mvp","title":"Sum all values",
    "statement":"Read n in 4..6 followed by n integers in 0..9. Print sum of every value.",
    "fields":[{"name":"n","kind":"int","min":4,"max":6},{"name":"a","kind":"ints","min":0,"max":9,"length_from":"n"}],
    "lines":[["n"],["a"]],"output":"tokens"},
    "reference":"n=int(input())\na=list(map(int,input().split()))\nprint(sum(a))\n",
    "controls":[{"case":{"n":4,"a":[1,2,3,4]},"expected":"10"},
                {"case":{"n":5,"a":[1,2,3,4,5]},"expected":"15"}]}

def test(url):
    checks=[];errors=[];external=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1400,"height":1000},accept_downloads=True)
        page.on("pageerror",lambda e:errors.append(str(e)))
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route);page.goto(url+"/v4")
        expect(page.locator("#package")).not_to_be_empty(timeout=15000)
        page.locator("#package").fill(json.dumps(PACKAGE));page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=35000) as response:
            page.locator("#approve").click()
        approved=response.value.json()
        assert approved["status"]=="approved_by_owner",approved
        expect(page.locator("#packages")).to_have_value(approved["key"])
        page.locator("#source").fill(SOURCE);page.locator("#trusted").check()
        page.locator("#count").fill("1");page.locator("#reduce-count").fill("0")
        with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:
            page.locator("#run").click()
        result=response.value.json()
        assert result["status"]=="observed_mismatch",result.get("status")
        loc=result["evidence_localization"];tree=result["student_graph"]["structure"]
        assert loc["effect_site"]["line"]==6
        assert loc["ranked"][0]["line"]==4
        assert loc["loop_bounds"][0]["omitted_indices"]==[3]
        assert loc["source_sha256"]==tree["source_sha256"] and not loc["causal_fault_proven"]
        expect(page.locator("#bounds-findings")).to_contain_text("omitted [3]")
        page.locator("#bounds-findings button").first.click()
        expect(page.locator("#code .active")).to_contain_text("range(n-1)")
        checks.append("observed_bounds_and_effect_source_link")
        page.locator("summary").filter(has_text="AST").click()
        expect(page.locator("#ast-tree")).to_be_visible()
        expect(page.locator("#ast-tree .ast-node").filter(has_text="For").first).to_be_visible()
        page.locator("#ast-tree .ast-node").filter(has_text="For").first.click()
        expect(page.locator("#code .profile-range").first).to_contain_text("range(n-1)")
        expect(page.locator("#ast-scope")).to_contain_text("statement_start")
        checks.append("ast_to_recorded_source_event")
        page.locator("#reference").click()
        expect(page.locator("#ast-tree .ast-node").filter(has_text="For")).to_have_count(0)
        page.locator("#student").click()
        expect(page.locator("#ast-tree .ast-node").filter(has_text="For")).to_have_count(1)
        checks.append("ast_student_reference_source_identity")
        with page.expect_download() as download:page.locator("#export").click()
        assert download.value.suggested_filename=="algoxray-v4-evidence.json"
        checks.append("evidence_export")
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.body.scrollWidth")<=390
        checks.append("mobile_width")
        assert not errors,errors
        assert not external,external
        browser.close()
    return {"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,
            "scope":"Synthetic development fixture, not localization accuracy evaluation.",
            "source":SOURCE,"witness":result["witness"]["case"],
            "expected":result["witness"]["reference"]["stdout"],"actual":result["witness"]["student"]["stdout"],
            "source_structure":tree,"localization":loc}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8793);parser.add_argument("--out",default="docs/mvp-evidence/localization-browser.json");args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}"
    with tempfile.TemporaryDirectory(prefix="algoxray-localization-browser-") as temp:
        env={**os.environ,"ALGOXRAY_V4_PACKAGE_STORE":str(Path(temp)/"packages")}
        with (Path(temp)/"server.log").open("wb") as log:
            server=subprocess.Popen([sys.executable,"-m","uvicorn","algoxray.api:app","--host","127.0.0.1","--port",str(args.port)],env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(url+"/api/health",timeout=1) as r:
                            if r.status==200:break
                    except OSError:time.sleep(.1)
                else:raise RuntimeError("Server not ready")
                report=test(url);out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
                out.write_text(json.dumps(report,indent=2),encoding="utf-8")
                print(json.dumps({k:report[k] for k in ("status","checks","page_errors","external_requests","expected","actual")}))
                print(json.dumps({"effect":report["localization"]["effect_site"],"ranked":report["localization"]["ranked"],"bounds":report["localization"]["loop_bounds"]}))
            finally:
                server.terminate()
                try:server.wait(timeout=5)
                except subprocess.TimeoutExpired:server.kill();server.wait()
