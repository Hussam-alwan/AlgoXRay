"""Live Docker/browser smoke: different legal outputs and both repair witnesses."""
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser

P={"manifest":{"id":"two_sum_multi","title":"Two sum — any valid pair",
    "statement":"Read n (2..6), target k (0..20), and n integers (0..9). Print any two distinct 1-based indices whose values sum to k, or NONE if no pair exists.",
    "fields":[{"name":"n","kind":"int","min":2,"max":6},{"name":"k","kind":"int","min":0,"max":20},
              {"name":"a","kind":"ints","min":0,"max":9,"length_from":"n"}],
    "lines":[["n","k"],["a"]],"output":"tokens"},
    "checker":{"kind":"two_sum_indices","version":1,"array":"a","target":"k","index_base":1,"no_solution":"NONE"},
    "reference":"n,k=map(int,input().split())\na=list(map(int,input().split()))\nans='NONE'\nfor i in range(n):\n for j in range(i+1,n):\n  if a[i]+a[j]==k: ans=f'{i+1} {j+1}'\nprint(ans)\n",
    "reference_alt":"n,k=map(int,input().split())\na=list(map(int,input().split()))\nseen={}\nfor j,x in enumerate(a,1):\n if k-x in seen:\n  print(seen[k-x],j)\n  break\n seen[x]=j\nelse: print('NONE')\n",
    "controls":[{"case":{"n":4,"k":5,"a":[1,4,2,3]},"expected":"2 1"},
                {"case":{"n":2,"k":20,"a":[0,1]},"expected":"NONE"}]}
BAD="n,k=map(int,input().split())\na=list(map(int,input().split()))\nprint('1 1')\n"

def test(url):
    checks=[];errors=[];external=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1400,"height":1000})
        page.on("pageerror",lambda e:errors.append(str(e)))
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route);page.goto(url+"/v4?view=expert")
        expect(page.locator("#package")).not_to_be_empty(timeout=15000)
        page.locator("#package").fill(json.dumps(P));page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=60000) as response:
            page.locator("#approve").click()
        approved=response.value.json();assert approved["status"]=="approved_by_owner",approved
        expect(page.locator("#packages")).to_have_value(approved["key"])
        checks.append("distinct_valid_reference_outputs_approved")
        page.locator("#source").fill(P["reference_alt"]);page.locator("#trusted").check();page.locator("#count").fill("1")
        with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:
            page.locator("#run").click()
        good=response.value.json();assert good["status"]=="no_witness_found",good
        checks.append("different_valid_solution_not_accused")
        page.locator("#source").fill(BAD);page.locator("#trusted").check();page.locator("#reduce-count").fill("2")
        with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:
            page.locator("#run").click()
        bad=response.value.json()
        assert bad["status"]=="observed_mismatch" and bad["original_case"]!=bad["witness"]["case"],bad.get("status")
        assert bad["witness"]["judgment"]["status"]=="rejected"
        expect(page.locator("#scope")).to_contain_text("owner_reviewed_semantic_checker")
        checks.append("semantic_rejection_and_reduction")
        page.locator("#candidate").fill(P["reference_alt"]);page.locator("#patch-reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/repair/verify"),timeout=90000) as response:
            page.locator("#verify-patch").click()
        repaired=response.value.json();assert repaired["status"]=="passed_named_tests",repaired
        assert {x["kind"] for x in repaired["witness_reproductions"]}=={"witness","original_witness"}
        expect(page.locator("#patch-status")).to_contain_text("suite_sha256")
        expect(page.locator("#source")).to_have_value(BAD)
        checks.append("both_witnesses_and_suite_identity")
        page.locator("#candidate").fill("print('NONE')")
        expect(page.locator("#patch-status")).to_have_text("")
        expect(page.locator("#patch-reviewed")).not_to_be_checked()
        checks.append("candidate_edit_invalidates_old_repair")
        assert not errors,errors
        assert not external,external
        browser.close()
    return {"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,
            "scope":"Synthetic fixture, local Docker, simulated owner review. Not a benchmark.",
            "original_case":bad["original_case"],"reduced_case":bad["witness"]["case"],
            "judgment":bad["witness"]["judgment"],"repair":repaired}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8791);parser.add_argument("--out",default="docs/mvp-evidence/checker-repair-browser.json");args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}"
    with tempfile.TemporaryDirectory(prefix="algoxray-checker-browser-") as temp:
        env={**os.environ,"ALGOXRAY_V4_PACKAGE_STORE":str(Path(temp)/"packages")}
        with (Path(temp)/"server.log").open("wb") as log:
            server=subprocess.Popen([sys.executable,"-m","uvicorn","algoxray.api:app","--host","127.0.0.1","--port",str(args.port)],env=env,stdout=log,stderr=log)
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(url+"/api/health",timeout=1) as r:
                            if r.status==200:break
                    except OSError:time.sleep(.1)
                else:raise RuntimeError("Server not ready")
                report=test(url);out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
                out.write_text(json.dumps(report,indent=2),encoding="utf-8")
                print(json.dumps({k:report[k] for k in ("status","checks","page_errors","external_requests","original_case","reduced_case","judgment")}),flush=True)
                print(json.dumps({"repair_status":report["repair"]["status"],"checks":len(report["repair"]["checks"]),"executions":report["repair"]["executions"]}),flush=True)
            finally:
                server.terminate()
                try:server.wait(timeout=5)
                except subprocess.TimeoutExpired:server.kill();server.wait()
