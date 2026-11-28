"""Browser smoke for new problem intake, V2 multi-case contract, and reduction UI."""
import argparse, json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from verify_browser import available_browser

STATEMENT="Read T (1 <= T <= 3). For each case read n (1 <= n <= 4), then n distinct sorted integers from 0 to 9. Print their sum per case."
MANIFEST={"schema_version":2,"id":"new_repeated_sum","title":"Repeated sorted sum",
          "statement":STATEMENT,"fields":[{"name":"n","kind":"int","min":1,"max":4},
              {"name":"a","kind":"ints","min":0,"max":9,"length_from":"n","sorted":True,"unique":True}],
          "lines":[["n"],["a"]],"output":"tokens","repeat":{"min":1,"max":3}}
REFERENCE="import sys\nit=iter(map(int,sys.stdin.buffer.read().split()))\nfor _ in range(next(it)):\n    a=[next(it) for i in range(next(it))]\n    print(sum(a))\n"
STUDENT=REFERENCE.replace("sum(a)","sum(a[:-1])")
CONTROLS=[{"case":{"t":2,"cases":[{"n":2,"a":[0,3]},{"n":3,"a":[1,2,4]}]},"expected":"3\n7\n"},
          {"case":{"t":1,"cases":[{"n":1,"a":[5]}]},"expected":"5\n"}]

def test(url):
    checks=[];errors=[];external=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1400,"height":1000})
        page.on("pageerror",lambda e:errors.append(str(e)))
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route)
        page.goto(url+"/v4")
        expect(page.locator("#package")).not_to_be_empty(timeout=15000)
        page.locator("#problem-url").fill("https://example.com/problem")
        with page.expect_response(lambda r:r.url.endswith("/packages/intake"),timeout=10000) as response:
            page.locator("#import-problem").click()
        assert response.value.status==422
        checks.append("intake_allowlist")
        page.locator("#statement").fill(STATEMENT)
        page.locator("#statement-kind").select_option("description")
        page.locator("#manual-samples").fill(json.dumps([{"stdin":"1\n1\n5\n","stdout":"5\n"}]))
        with page.expect_response(lambda r:r.url.endswith("/packages/intake"),timeout=15000) as response:
            page.locator("#prepare-statement").click()
        assert response.value.ok
        data=response.value.json()
        expect(page.locator("#intake-review")).to_contain_text("description")
        checks.append("description_prepared_without_ai")
        package={"manifest":MANIFEST,"reference":REFERENCE,"controls":CONTROLS,"intake":data["intake"]}
        page.locator("#package").fill(json.dumps(package))
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=15000) as response:
            page.locator("#approve").click()
        assert response.value.status==403
        checks.append("approval_guard")
        page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=35000) as response:
            page.locator("#approve").click()
        approved=response.value.json()
        assert approved["status"]=="approved_by_owner",approved
        expect(page.locator("#packages")).to_have_value(approved["key"])
        checks.append("v2_package_approved")
        page.locator("#source").fill(STUDENT);page.locator("#trusted").check()
        page.locator("#count").fill("1");page.locator("#reduce-count").fill("4")
        with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:
            page.locator("#run").click()
        result=response.value.json()
        assert result["status"]=="observed_mismatch",result.get("status")
        assert result["original_case"]["t"]==2 and result["witness"]["case"]["t"]==1
        expect(page.locator("#reduction-panel")).to_be_visible()
        expect(page.locator("#reduction-evidence")).to_contain_text("original_replays")
        expect(page.locator("#reduction-original")).to_have_text(result["original_witness"]["stdin"])
        expect(page.locator("#reduction-best")).to_have_text(result["witness"]["stdin"])
        assert page.locator("#graph .node").count()>0
        checks.append("v2_real_docker_reduction_ui")
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.body.scrollWidth")<=390
        checks.append("mobile_width")
        page.locator("#candidate").fill(REFERENCE)
        page.locator("#patch-reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/v4/repair/verify"),timeout=90000) as response:
            page.locator("#verify-patch").click()
        repaired=response.value.json()
        assert repaired["status"]=="passed_named_tests",repaired
        assert all(row["status"]=="reproduced" for row in repaired["witness_reproductions"])
        assert {row["kind"] for row in repaired["witness_reproductions"]}=={"witness","original_witness"}
        expect(page.locator("#source")).to_have_value(STUDENT)
        expect(page.locator("#patch-status")).to_contain_text(repaired["suite_sha256"])
        checks.append("intake_witness_to_repair_on_both_cases")
        assert not errors,errors
        assert not external,external
        browser.close()
    return {"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,
            "scope":"Synthetic development fixture and owner-review simulation, not user study.",
            "analysis":{"status":result["status"],"original_case":result["original_case"],
                        "reduced_case":result["witness"]["case"],"attempts":result["attempts"],
                        "executions":result["executions"],"reduction":result["reduction"]},
            "repair":{"status":repaired["status"],"suite_sha256":repaired["suite_sha256"],
                      "planned_cases":repaired["planned_cases"],"executions":repaired["executions"]}}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8795);parser.add_argument("--out",default="docs/mvp-evidence/intake-v2-browser.json");args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}"
    with tempfile.TemporaryDirectory(prefix="algoxray-mvp-browser-") as temp:
        env={**os.environ,"ALGOXRAY_V4_PACKAGE_STORE":str(Path(temp)/"packages"),
             "ALGOXRAY_V4_REPAIR_STORE":str(Path(temp)/"repairs")}
        with (Path(temp)/"server.log").open("wb") as log:
            server=subprocess.Popen([sys.executable,"-m","uvicorn","algoxray.api:app","--host","127.0.0.1","--port",str(args.port)],env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(url+"/api/health",timeout=1) as r:
                            if r.status==200:break
                    except OSError:time.sleep(.1)
                else:raise RuntimeError("Server not ready")
                report=test(url)
                out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
                out.write_text(json.dumps(report,indent=2),encoding="utf-8")
                print(json.dumps(report),flush=True)
            finally:
                server.terminate()
                try:server.wait(timeout=5)
                except subprocess.TimeoutExpired:server.kill();server.wait()
