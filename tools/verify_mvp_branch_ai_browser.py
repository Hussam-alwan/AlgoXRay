"""Real browser/worker with a controlled structured diagnosis. No cloud requests."""
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser

SOURCE="n=int(input())\nif n>=0:\n    out=1\nelse:\n    out=0\nprint(out)\n"
P={"manifest":{"id":"branch_sign","title":"Positive integer","statement":"Read n in -4..4. Print 1 if n is positive, otherwise 0.",
    "fields":[{"name":"n","kind":"int","min":-4,"max":4}],"lines":[["n"]],"output":"tokens"},
    "reference":"n=int(input())\nprint(int(n>0))\n","controls":[{"case":{"n":0},"expected":"0"},{"case":{"n":-1},"expected":"0"}]}

def server(port):
    from algoxray import v4_api
    from algoxray.v4_provider import ProviderError
    class Fixture:
        model="controlled-branch-fixture";usage={}
        def propose(self,task,data,schema):
            if "# outage" in data.get("source",""):raise ProviderError("controlled_outage")
            assert task=="diagnosis" and data["context_version"]==2
            assert data["location_candidates"] and data["observed_branches"]
            event=next(e for e in data["events"] if e["line"]==2 and e["kind"]=="line")
            return {"hypotheses":[{"text":"Inspect the condition at zero.","line":2,"event_ids":[event["event_id"]]},
                                  {"text":"Consider the other branch as a static hypothesis.","line":5,"event_ids":[event["event_id"]],"basis":"static"},
                                  {"text":"Unsupported anchor.","line":2,"event_ids":["invented"]}],
                    "facts":[{"event_id":event["event_id"],"variable":"n","value":0},{"event_id":event["event_id"],"variable":"n","value":99}],
                    "branches":[{"event_id":event["event_id"],"line":2,"condition":True}]}
    v4_api.provider_for=lambda *a,**kw:Fixture()
    import uvicorn
    uvicorn.run("algoxray.api:app",host="127.0.0.1",port=port,log_level="warning")

def test(url):
    checks=[];errors=[];external=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1400,"height":1000})
        page.on("pageerror",lambda e:errors.append(str(e)))
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route);page.goto(url+"/v4")
        expect(page.locator("#package")).not_to_be_empty(timeout=15000)
        page.locator("#package").fill(json.dumps(P));page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=35000) as response:
            page.locator("#approve").click()
        approved=response.value.json();assert approved["status"]=="approved_by_owner",approved
        expect(page.locator("#packages")).to_have_value(approved["key"])
        page.locator("#source").fill(SOURCE);page.locator("#trusted").check()
        page.locator("#count").fill("1");page.locator("#reduce-count").fill("0");page.locator("#spectrum").check();page.locator("#ai").check()
        with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:
            page.locator("#run").click()
        r=response.value.json()
        assert r["status"]=="observed_mismatch" and r["ai_status"]=="ok",r.get("ai_error")
        assert r["suspiciousness"]["passing_count"]>=1
        assert r["suspiciousness"]["branches"]["ranked"][0]["line"]==2
        expect(page.locator("#branch-ranking")).to_contain_text("condition_true")
        expect(page.locator("#branch-coverage")).to_contain_text("L2")
        page.locator("#branch-ranking button").first.click()
        expect(page.locator("#code .active")).to_contain_text("if n>=0")
        checks.append("observed_branch_ranking_source_link")
        assert r["ai_conflicting_claims"]==1
        assert [h["status"] for h in r["hypotheses"]]==["hypothesis","hypothesis","unsupported"]
        assert not r["hypotheses"][1]["line_observed_in_supplied_anchors"]
        assert r["ai_facts"][1]["status"]=="contradicted"
        expect(page.locator("#hypotheses .hypothesis").nth(1)).to_contain_text("L5")
        expect(page.locator("#ai-context")).to_contain_text("supplied_event_ids")
        checks.append("checked_claims_static_hypothesis_and_invented_anchor")
        page.locator("#source").fill(SOURCE+"# outage\n");page.locator("#trusted").check()
        with page.expect_response(lambda x:x.url.endswith("/v4/analyze"),timeout=90000) as response:
            page.locator("#run").click()
        outage=response.value.json()
        assert outage["status"]=="observed_mismatch" and outage["ai_status"]=="unavailable_or_invalid"
        assert outage["evidence_localization"]["ranked"]
        expect(page.locator("#branch-coverage")).to_contain_text("condition_true")
        checks.append("provider_outage_preserves_branch_evidence")
        assert not errors,errors
        assert not external,external
        browser.close()
    return {"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,
            "scope":"Real browser and local Docker; explicitly mocked model output, not model accuracy.",
            "witness":r["witness"]["case"],"ranking":r["suspiciousness"],"context":r["ai_context"],
            "hypotheses":r["hypotheses"],"facts":r["ai_facts"],"outage_status":outage["ai_status"]}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8790);parser.add_argument("--out",default="docs/mvp-evidence/branch-ai-browser.json");parser.add_argument("--server-mode",action="store_true");args=parser.parse_args()
    if args.server_mode:server(args.port);raise SystemExit()
    url=f"http://127.0.0.1:{args.port}"
    with tempfile.TemporaryDirectory(prefix="algoxray-branch-browser-") as temp:
        env={**os.environ,"ALGOXRAY_V4_PACKAGE_STORE":str(Path(temp)/"packages")}
        with (Path(temp)/"server.log").open("wb") as log:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"--server-mode","--port",str(args.port)],env=env,stdout=log,stderr=log)
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(url+"/api/health",timeout=1) as r:
                            if r.status==200:break
                    except OSError:time.sleep(.1)
                else:raise RuntimeError("Server not ready")
                report=test(url);out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
                out.write_text(json.dumps(report,indent=2),encoding="utf-8")
                print(json.dumps({k:report[k] for k in ("status","checks","page_errors","external_requests","witness")}),flush=True)
            finally:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
