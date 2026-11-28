"""Educational visualizations: live Docker traces and negative rendering fixtures.
These are development cases, not independent held-out research results."""
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser

SORT="a=list(map(int,input().split()))\nfor i in range(len(a)-1):\n    for j in range(len(a)-1-i):\n        if a[j]>a[j+1]:\n            a[j],a[j+1]=a[j+1],a[j]\ntotal=0\nfor i in range(len(a)):\n    total+=a[i]\nprint(a,total)\n"
RECURSION="def factorial(n):\n    if n<=1:\n        return 1\n    child=factorial(n-1)\n    result=n*child\n    return result\nprint(factorial(int(input())))\n"
DP="n=int(input())\ndp=[[0,0,0] for _ in range(n)]\nfor i in range(n):\n    for j in range(3):\n        if i==0 or j==0:\n            dp[i][j]=1\n        else:\n            dp[i][j]=dp[i-1][j]+dp[i][j-1]\nmemo={'answer':dp[n-1][2]}\nseen={1,2}\nprint(memo['answer'])\n"

def test(url,folder):
    checks=[];errors=[];external=[];posts=[];record={}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1000})
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("request",lambda req:posts.append(req.url.removeprefix(url)) if req.method=="POST" else None)
        def route(r):
            if r.request.url.startswith(url+"/"):r.continue_()
            else:external.append(r.request.url);r.abort()
        page.route("**/*",route)
        page.goto(url+"/v4")
        expect(page.locator("#source")).not_to_be_empty(timeout=15000)
        def tab(name):page.locator("#ux-tab-"+name).click()
        tab("advanced")
        page.locator("#ux-tools > summary").click()
        page.locator("#ux-separate-modes > summary").click()
        page.locator('[data-mode="understand"]').click()
        def run(source,stdin):
            tab("input")
            page.locator("#source").fill(source)
            page.locator("#manual-stdin").fill(stdin)
            page.locator("#trusted").check()
            before=len(posts)
            with page.expect_response(lambda r:r.url.endswith("/v4/observe"),timeout=60000) as response:
                page.locator("#observe-run").click()
            data=response.value.json()
            assert data["status"]=="manual_observation",data.get("status")
            expect(page.locator("#ux-tab-summary")).to_have_attribute("aria-selected","true")
            tab("execution")
            expect(page.locator("#learning-explain")).to_be_visible()
            assert posts[before:]==["/api/v4/observe"],posts[before:]
            return data,data["witness"]["student"]["events"]
        def select(i):
            page.locator("#story-rail button").nth(i).click()
            expect(page.locator("#story-step")).to_have_text(f"{i+1} / {page.locator('#story-rail button').count()}")
        sort,ev=run(SORT,"4 1 3 2\n")
        assert sort["witness"]["student"]["stdout"]=="[1, 2, 3, 4] 10\n"
        record["sort"]={"events":len(ev),"stdout":sort["witness"]["student"]["stdout"]}
        # First pair of distinct reordered numeric values in the same frame.
        idx=next(i for i in range(1,len(ev)) if isinstance(ev[i]["locals"].get("a"),list) and isinstance(ev[i-1]["locals"].get("a"),list) and ev[i]["frame_id"]==ev[i-1]["frame_id"] and ev[i]["locals"]["a"]!=ev[i-1]["locals"]["a"] and sorted(ev[i]["locals"]["a"])==sorted(ev[i-1]["locals"]["a"]))
        select(idx);before=len(posts)
        a,b=ev[idx-1]["locals"]["a"],ev[idx]["locals"]["a"]
        expected=[(a.index(v),i) for i,v in enumerate(b) if a.index(v)!=i]
        actual=page.locator('[data-variable="a"] .learning-movement').evaluate_all("(els)=>els.map(e=>[Number(e.dataset.from),Number(e.dataset.to)])")
        assert actual==[list(x) for x in expected],(actual,expected)
        expect(page.locator('[data-variable="a"] .learning-number-row strong')).to_have_text(list(map(str,b)))
        page.screenshot(path=str(folder/"learning-sort.jpg"),type="jpeg",quality=75)
        checks.append("observed_array_positions_and_numeric_bars")
        relation=next(r for r in sort["student_graph"]["relations"]["data"] if r["write"]["name"]=="total")
        i=next(i for i,e in enumerate(ev) if e["event_id"]==relation["after_event_id"])
        select(i)
        expect(page.locator("#learning-relations .learning-flow-result strong").first).to_have_text(str(relation["write"]["value"]))
        expect(page.locator("#learning-relations .learning-flow-reads strong")).to_have_text(list(map(str,relation["reads"].values())))
        expect(page.locator("#learning-source [aria-current=step]")).to_have_attribute("data-line",str(ev[i]["line"]))
        page.screenshot(path=str(folder/"learning-relation.jpg"),type="jpeg",quality=75)
        page.locator("#learning-relations button").first.click()
        expect(page.locator("#story-step")).to_have_text(f"{next(j for j,e in enumerate(ev) if e['event_id']==relation['before_event_id'])+1} / {len(ev)}")
        checks.append("recomputed_read_write_flow_and_evidence_navigation")
        i=next(i for i in range(len(ev)-1) if ev[i]["kind"]==ev[i+1]["kind"]=="line" and ev[i]["frame_id"]==ev[i+1]["frame_id"] and isinstance(ev[i]["locals"].get("total"),int) and isinstance(ev[i+1]["locals"].get("total"),int) and ev[i]["locals"]["total"]!=ev[i+1]["locals"]["total"])
        select(i)
        expect(page.locator("#learning-predict")).to_be_visible()
        page.locator("#learning-predict > summary").click()
        k=page.locator(".learning-question").get_attribute("data-variable")
        target=ev[i+1]["locals"][k]
        page.locator(".learning-answer-options button").filter(has_text=str(target)).first.click()
        expect(page.locator("#learning-feedback")).not_to_be_empty()
        page.locator("#learning-next-change").click()
        assert len(posts)==before
        checks.append("prediction_and_key_steps_do_not_execute")
        recursion,ev=run(RECURSION,"4\n")
        assert recursion["witness"]["student"]["stdout"]=="24\n"
        record["recursion"]={"events":len(ev),"stdout":"24\n"}
        i=next(i for i,e in enumerate(ev) if e["function"]=="factorial" and e["locals"].get("n")==1)
        select(i)
        frames={}
        for event in ev[:i+1]:
            frames.setdefault(event["frame_id"],event.get("parent_frame_id"))
        rows=page.locator("#learning-frames li[data-frame]").evaluate_all("(nodes)=>nodes.map(e=>[e.dataset.frame,e.dataset.parent||null])")
        assert dict(rows)==frames,(rows,frames)
        expect(page.locator("#learning-frames [aria-current=step]")).to_contain_text(ev[i]["frame_id"])
        page.screenshot(path=str(folder/"learning-recursion.jpg"),type="jpeg",quality=75)
        ri=next(i for i,e in enumerate(ev) if e["kind"]=="return" and e["function"]=="factorial")
        select(ri)
        # Return event exists but the schema does not contain a returned value.
        assert "return_value" not in ev[ri]
        expect(page.locator("#learning-explain")).to_contain_text("return")
        checks.append("actual_recursive_parent_frames_and_return_limit")
        dp,ev=run(DP,"3\n")
        assert dp["witness"]["student"]["stdout"]=="6\n"
        record["dp"]={"events":len(ev),"stdout":"6\n"}
        i=next(i for i in range(1,len(ev)) if ev[i]["locals"].get("dp",[[0]])==[[1,1,1],[1,2,3],[1,3,6]] and isinstance(ev[i]["locals"].get("dp"),list) and isinstance(ev[i-1]["locals"].get("dp"),list) and ev[i]["frame_id"]==ev[i-1]["frame_id"] and ev[i]["locals"]["dp"]!=ev[i-1]["locals"]["dp"])
        select(i)
        before,after=ev[i-1]["locals"]["dp"],ev[i]["locals"]["dp"]
        expected=[(r,c) for r,row in enumerate(after) for c,x in enumerate(row) if before[r][c]!=x]
        changed_cells=page.locator('[data-variable="dp"] td.learning-cell-changed').evaluate_all("(els)=>els.map(e=>[Number(e.dataset.row),Number(e.dataset.col)])")
        assert changed_cells==[list(x) for x in expected]
        expect(page.locator('#learning-changes [data-name="dp"]')).to_contain_text("dp[2][2]: 0")
        expect(page.locator(".learning-previous-source code")).to_contain_text("dp[i][j]=dp[i-1][j]+dp[i][j-1]")
        expect(page.locator('[data-variable="dp"] .story-transition .story-snapshot').last.locator("td")).to_have_text([str(x) for row in after for x in row])
        page.screenshot(path=str(folder/"learning-dp.jpg"),type="jpeg",quality=75)
        select(len(ev)-1)
        expect(page.locator('[data-variable="memo"] .learning-dict-row strong')).to_have_text("6")
        expect(page.locator('[data-variable="seen"] .learning-set span')).to_have_count(2)
        checks.append("actual_matrix_cell_updates_dictionary_and_set")
        # Explicit false-positive challenges with synthetic display-only fixtures.
        fixture=page.evaluate("""()=>{
          const L=AlgoXRayLearning;
          const dup=L.numericBars([2,1,1],[1,2,1]);
          const partial=L.numericBars({kind:'list',size:50,items:[2,1],truncated:true},[1,2]);
          const big=L.numericBars([9007199254740992],[]);
          const unsafe=L.changed(9007199254740992,9007199254740994);
          const row=(size,completed,median)=>({size,summary:{completed,requested:3,wall_ns:{min:median,median,max:median}},correctness:'recorded_match'});
          const graph=L.growth({size_field:'n',points:[row(1,3,100),row(2,0,200),row(4,3,400)]});
          return {dup:!!dup.querySelector('.learning-reorder'),partial:!!partial.querySelector('.learning-reorder'),big:!!big,unsafe,points:graph.querySelectorAll('circle').length,links:graph.querySelectorAll('line[stroke="#3158c8"]').length}
        }""")
        assert fixture=={"dup":False,"partial":False,"big":False,"unsafe":False,"points":2,"links":0},fixture
        checks.append("duplicate_partial_and_unsafe_numeric_abstention_growth_gaps")
        # Mobile actual nested trace display.
        page.set_viewport_size({"width":390,"height":844})
        select(i)
        page.locator("#learning-explain").scroll_into_view_if_needed()
        page.screenshot(path=str(folder/"learning-mobile.jpg"),type="jpeg",quality=75)
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
        checks.append("mobile_matrix_and_step_explanation")
        # A real approved development package, measured at three legal sizes.
        # One repetition per size tests the visual encoding, not a growth fit.
        page.set_viewport_size({"width":1440,"height":1000})
        tab("advanced")
        page.locator('[data-mode="diagnose"]').click()
        page.locator("#demo").select_option("sum")
        page.locator("#load").click()
        page.locator("#correct").click()
        expect(page.locator("#reviewed")).to_be_visible()
        page.locator("#reviewed").check()
        with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=50000) as response:
            page.locator("#approve").click()
        approved=response.value.json()
        assert approved["status"]=="approved_by_owner",approved.get("status")
        tab("advanced")
        page.locator('[data-mode="performance"]').click()
        tab("advanced")
        if not page.locator("#ux-timing-options").evaluate("(e)=>e.open"):
            page.locator("#ux-timing-options > summary").click()
        page.locator("#timing-repetitions").fill("1")
        tab("input")
        page.locator("#trusted").check()
        page.locator("#ux-scale-options > summary").click()
        page.locator("#size-field").fill("n")
        page.locator("#size-values").fill("1,4,12")
        with page.expect_response(lambda r:r.url.endswith("/v4/benchmark"),timeout=90000) as response:
            page.locator("#scaling-benchmark").click()
        measured=response.value.json()
        assert measured["stop_reason"]=="completed"
        assert [q["size"] for q in measured["points"]]==[1,4,12]
        assert all(q["summary"]["completed"]==1 and q["correctness"]=="recorded_match" for q in measured["points"])
        expect(page.locator("#ux-tab-summary")).to_have_attribute("aria-selected","true")
        tab("performance")
        expect(page.locator("#learning-growth")).to_be_visible()
        expect(page.locator("#learning-growth circle")).to_have_count(3)
        assert page.locator("#learning-growth g[data-size]").evaluate_all("(nodes)=>nodes.map(e=>Number(e.dataset.size))")==[1,4,12]
        assert measured["growth"]["status"]=="insufficient_points_or_repetitions"
        page.locator("#learning-growth").scroll_into_view_if_needed()
        page.screenshot(path=str(folder/"learning-growth.jpg"),type="jpeg",quality=75)
        record["growth"]={"points":[{"size":q["size"],"wall_ns":q["summary"]["wall_ns"],"correctness":q["correctness"]} for q in measured["points"]],"fit":measured["growth"]["status"]}
        checks.append("live_legal_growth_chart_and_no_complexity_claim")
        assert not errors,errors
        assert not external,external
        browser.close()
    return {"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,
            "scope":"Three synthetic development programs and a reviewed development benchmark executed in local Docker and browser; negative rendering fixtures; no independent research or human usability data.","programs":record,"negative_display_fixtures":fixture}
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8799)
    parser.add_argument("--out",default="docs/mvp-evidence/learning-visual-browser.json")
    parser.add_argument("--screenshots",default="results/learning-ui-preview");args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}";folder=Path(args.screenshots);folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="algoxray-learning-") as t:
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
                print(json.dumps(report),flush=True)
            finally:
                # Windows virtualenv launchers may own a child Python process.
                # Stop only the temporary server process tree started above.
                if os.name == "nt" and proc.poll() is None:
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=10, check=False)
                elif proc.poll() is None:
                    proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
                if os.name == "nt":time.sleep(0.5)
