"""Live browser smoke for independent trace, sample comparison and timing."""
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser

def worker_ids(*, include_stopped=False):
    command=["docker","ps","--filter","name=algoxray-v4-","--format","{{.ID}}"]
    if include_stopped:command.append("--all")
    return set(subprocess.check_output(command,text=True,timeout=5).split())

def test(url):
    errors=[];external=[];checks=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1400,"height":1000},accept_downloads=True)
        page.on("pageerror",lambda e:errors.append(str(e)))
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route);page.goto(url+"/v4")
        expect(page.locator("#package")).not_to_be_empty(timeout=15000)
        page.locator("#source").fill("n=int(input())\nprint(n*n)")
        page.locator("#manual-stdin").fill("3\n")
        page.locator("#trusted").check()
        with page.expect_response(lambda r:r.url.endswith("/v4/observe"),timeout=35000) as response:
            page.locator("#observe-run").click()
        observed=response.value.json()
        assert observed["judgment"]["status"]=="oracle_unavailable"
        assert observed["witness"]["student"]["stdout"]=="9\n"
        expect(page.locator("#results")).to_be_visible()
        assert page.locator("#graph .node").count()>0
        expect(page.locator("#reference")).to_be_disabled()
        expect(page.locator("#repair-panel")).to_be_hidden()
        checks.append("manual_trace_without_reference")
        page.locator("#manual-expected").fill("10");page.locator("#sample-reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/v4/observe"),timeout=35000) as response:
            page.locator("#observe-run").click()
        sample=response.value.json()
        assert sample["judgment"]["status"]=="sample_mismatch" and not sample["judgment"]["general_correctness_claim"]
        expect(page.locator("#expected")).to_have_text("10")
        checks.append("reviewed_sample_limited_judgment")
        page.locator("#timing-repetitions").fill("2")
        with page.expect_response(lambda r:r.url.endswith("/v4/benchmark"),timeout=50000) as response:
            page.locator("#plain-benchmark").click()
        plain=response.value.json()
        assert plain["points"][0]["summary"]["completed"]==2,plain
        assert plain["points"][0]["reference_status"]=="not_run"
        expect(page.locator("#benchmark-results")).to_be_visible()
        expect(page.locator("#results")).to_be_hidden()
        checks.append("independent_repeated_timing")
        page.locator("#demo").select_option("sum");page.locator("#load").click();page.locator("#correct").click()
        page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=35000) as response:
            page.locator("#approve").click()
        approved=response.value.json();assert approved["status"]=="approved_by_owner",approved
        expect(page.locator("#packages")).to_have_value(approved["key"])
        page.locator("#trusted").check()
        page.locator("summary").filter(has_text="قياس الزمن حسب حجم").click()
        page.locator("#size-field").fill("n");page.locator("#size-values").fill("1,4,12")
        page.locator("#timing-repetitions").fill("3")
        with page.expect_response(lambda r:r.url.endswith("/v4/benchmark"),timeout=90000) as response:
            page.locator("#scaling-benchmark").click()
        scaled=response.value.json()
        assert scaled["stop_reason"]=="completed",scaled
        assert [p["size"] for p in scaled["points"]]==[1,4,12]
        assert all(p["summary"]["completed"]==3 and p["correctness"]=="recorded_match" for p in scaled["points"]),scaled
        expect(page.locator("#benchmark-chart svg")).to_be_visible()
        assert page.locator("#benchmark-table tbody tr").count()==3
        with page.expect_download() as download:page.locator("#benchmark-export").click()
        assert download.value.suggested_filename=="algoxray-benchmark.json"
        checks.append("legal_scaling_curve_and_export")
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.body.scrollWidth")<=390
        checks.append("mobile_width")
        page.locator("#source").fill("print(1)")
        expect(page.locator("#benchmark-results")).to_be_hidden()
        checks.append("source_change_invalidates_measurement")

        page.locator("#source").fill("import time\nn = int(input())\nif n >= 4: time.sleep(5)\nprint(sum(map(int, input().split())))")
        page.locator("#size-values").fill("1,4")
        page.locator("#timing-repetitions").fill("1")
        page.locator("#trusted").check()
        with page.expect_response(lambda r:r.url.endswith("/v4/benchmark"),timeout=45000) as response:
            page.locator("#scaling-benchmark").click()
        censored=response.value.json()
        assert censored["points"][0]["summary"]["completed"]==1,censored
        timed=censored["points"][1]
        assert timed["summary"]["timeouts"]==1 and timed["summary"]["wall_ns"] is None,censored
        assert timed["runs"][0]["timeout_basis"]=="host_benchmark_wall_clock",timed
        assert timed["runs"][0]["cleanup_confirmed"] is True,timed
        expect(page.locator("#benchmark-chart .benchmark-timeout")).to_have_count(1)
        expect(page.locator("#benchmark-chart circle")).to_have_count(1)
        checks.append("timeout_retained_and_marked_without_invented_runtime")

        page.locator("#source").fill("import time\ntime.sleep(5)\n")
        page.locator("#timing-seconds").fill("3")
        page.locator("#trusted").check()
        existing_workers=worker_ids()
        with page.expect_response(lambda r:r.url.endswith("/v4/benchmark"),timeout=45000) as response:
            page.locator("#plain-benchmark").click()
            deadline=time.monotonic()+7
            new_workers=set()
            while not new_workers and time.monotonic()<deadline:
                new_workers=worker_ids()-existing_workers
                if not new_workers:time.sleep(.05)
            assert len(new_workers)==1,new_workers
            worker_id=next(iter(new_workers))
            config=json.loads(subprocess.check_output(["docker","inspect","--format","{{json .HostConfig}}",worker_id],text=True,timeout=5))
            limits={key:config[key] for key in ("Memory","MemorySwap","NanoCpus","PidsLimit","NetworkMode","ReadonlyRootfs")}
            page.locator("#cancel").click()
        cancelled=response.value.json()
        assert limits=={"Memory":128*1024**2,"MemorySwap":128*1024**2,"NanoCpus":500_000_000,
                        "PidsLimit":32,"NetworkMode":"none","ReadonlyRootfs":True},limits
        assert cancelled["stop_reason"]=="cancelled",cancelled
        assert cancelled["run_report"]["workers"][-1]["cleanup_confirmed"] is True,cancelled
        assert worker_id not in worker_ids(include_stopped=True)
        checks.append("active_benchmark_cancel_and_worker_limits")
        assert not errors,errors
        assert not external,external
        browser.close()
    return {"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,
            "scope":"Synthetic development smoke; local timings are not Codeforces timings or a complexity proof.",
            "manual_judgment":observed["judgment"],"sample_judgment":sample["judgment"],
            "plain":plain,"scaled":scaled,"censored":censored,"cancelled":cancelled,"worker_limits":limits}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8794);parser.add_argument("--out",default="docs/mvp-evidence/observation-browser.json");args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}"
    with tempfile.TemporaryDirectory(prefix="algoxray-observation-browser-") as temp:
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
                print(json.dumps({k:report[k] for k in ("status","checks","page_errors","external_requests")}))
                print(json.dumps({"sizes":[p["size"] for p in report["scaled"]["points"]],
                                  "wall_medians_ns":[p["summary"]["wall_ns"]["median"] for p in report["scaled"]["points"]],
                                  "growth":report["scaled"]["growth"]}))
            finally:
                server.terminate()
                try:server.wait(timeout=5)
                except subprocess.TimeoutExpired:server.kill();server.wait()
