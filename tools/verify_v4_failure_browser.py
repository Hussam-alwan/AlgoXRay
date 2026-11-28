"""Real browser, synthetic packages and explicitly injected provider outage. No production hook."""
import argparse,json,os,re,subprocess,sys,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from verify_browser import available_browser

def server(port):
 from algoxray import v4_api
 from algoxray.v4_provider import ProviderError
 class Outage:
  model="controlled-outage-test";usage={}
  def propose(self,task,data,schema):
   if "# profile-diagnosis-fixture" in data.get("source",""):
    import ast
    line=next(n.lineno for n in ast.walk(ast.parse(data["source"])) if isinstance(n,ast.While))
    event=next(e for e in data["events"] if e["line"]==line and e.get("kind")=="line")
    return {"hypotheses":[{"text":"Inspect the repeated loop bounds in the recorded events.","event_ids":[event["event_id"]],"line":line}],
        "facts":[{"event_id":event["event_id"],"variable":"l","value":event["locals"]["l"]}],
        "branches":[{"event_id":event["event_id"],"line":line,"condition":True}]}
   raise ProviderError("controlled_test_provider_unavailable")
 v4_api.provider_for=lambda *args,**kwargs:Outage()
 v4_api.model_health=lambda:{"status":"unavailable","models":[]}
 import uvicorn
 uvicorn.run("algoxray.api:app",host="127.0.0.1",port=port,log_level="warning")

def main():
 parser=argparse.ArgumentParser();parser.add_argument("--out");parser.add_argument("--port",type=int,default=8805);parser.add_argument("--server-mode",action="store_true");a=parser.parse_args()
 if a.server_mode:return server(a.port)
 if not a.out:raise SystemExit("--out required")
 out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False);url=f"http://127.0.0.1:{a.port}"
 env={**os.environ,"ALGOXRAY_V4_PACKAGE_STORE":str(out/"test-only-packages"),"ALGOXRAY_V4_REPAIR_STORE":str(out/"test-only-repairs")}
 with (out/"server.log").open("wb") as log:
  process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"--server-mode","--port",str(a.port)],env=env,stdout=log,stderr=subprocess.STDOUT)
  try:
   for _ in range(100):
    try:
     with urllib.request.urlopen(url+"/api/health",timeout=1) as r:
      if r.status==200:break
    except OSError:time.sleep(.1)
   else:raise RuntimeError("Test server unavailable")
   return test(url,out)
  finally:
   process.terminate()
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill()
def test(url,out):
 checks=[];errors=[];external=[]
 reference="n=int(input())\na=list(map(int,input().split()))\nprint(sum(a))\n"
 package={"manifest":{"id":"browser_failure_sum","title":"Synthetic browser failure sum","statement":"Sum n integers. n is from 1 to 3; every value is from -2 to 2.","fields":[{"name":"n","kind":"int","min":1,"max":3},{"name":"a","kind":"ints","min":-2,"max":2,"length_from":"n"}],"lines":[["n"],["a"]],"output":"tokens"},"reference":reference,"controls":[{"case":{"n":2,"a":[1,1]},"expected":"2"},{"case":{"n":1,"a":[2]},"expected":"2"}]}
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=available_browser(),headless=True);page=browser.new_page(viewport={"width":1400,"height":1000})
  page.on("pageerror",lambda e:errors.append(str(e)))
  def route(r):
   if r.request.url.startswith(url+"/"):r.continue_()
   else:external.append(r.request.url);r.abort()
  page.route("**/*",route);page.goto(url+"/v4?view=expert")
  expect(page.locator("#package")).to_have_value(re.compile("hamburgers"),timeout=15000)
  page.locator("#package").fill(json.dumps(package));page.locator("#reviewed").check()
  def approve():
   with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=45000) as response:page.locator("#approve").click()
   value=response.value.json();assert response.value.ok and value["status"]=="approved_by_owner",value
   expect(page.locator("#packages")).to_have_value(value["key"],timeout=10000)
  approve();page.locator("#trusted").check();page.locator("#count").fill("2")
  page.locator("#ai").check()
  page.locator("#source").fill(reference.replace("print(sum(a))","print(sum(a)-1)"))
  with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:page.locator("#run").click()
  result=response.value.json();assert result["status"]=="observed_mismatch" and result["ai_status"]=="unavailable_or_invalid",result.get("status")
  assert result["ai_error"]=="controlled_test_provider_unavailable"
  assert page.locator("#graph .node").count()>0 and result["replay_count"]==3
  (out/"outage.json").write_text(json.dumps(result,indent=2),encoding="utf-8");checks.append("provider_outage_keeps_replayed_witness_and_graph")
  page.locator("#source").fill(reference)
  with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:page.locator("#run").click()
  assert response.value.json()["status"]=="no_witness_found"
  expect(page.locator("#results")).to_be_hidden();checks.append("correct_control_not_accused_during_provider_outage")
  invalid=json.loads(json.dumps(package));invalid["manifest"]["fields"][0]["kind"]="arbitrary_python"
  page.locator("#package").fill(json.dumps(invalid))
  with page.expect_response(lambda r:r.url.endswith("/packages/approve"),timeout=10000) as response:page.locator("#approve").click()
  assert response.value.status==422;checks.append("unsupported_contract_rejected")
  disagree=json.loads(json.dumps(package));disagree["manifest"]["id"]="browser_disagreement"
  disagree["reference_alt"]="n=int(input())\na=list(map(int,input().split()))\nprint(sum(a)+(1 if any(x<0 for x in a) else 0))\n"
  page.locator("#package").fill(json.dumps(disagree));approve()
  page.locator("#source").fill(reference)
  with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:page.locator("#run").click()
  value=response.value.json();assert value["status"]=="oracle_unavailable" and value["detail"]["reference"]["status"]=="oracle_disagreement",value
  expect(page.locator("#results")).to_be_hidden();checks.append("later_reference_disagreement_blocks_accusation")
  page.locator("#manual-stdin").fill("2\n1 1\n")
  with page.expect_response(lambda r:r.url.endswith("/v4/observe"),timeout=35000) as response:page.locator("#observe-run").click()
  manual=response.value.json()
  assert manual["status"]=="manual_observation" and manual["judgment"]["status"]=="oracle_unavailable",manual
  assert manual["witness"]["student"]["stdout"]=="2\n"
  expect(page.locator("#graph .node").first).to_be_visible()
  checks.append("manual_trace_available_after_reference_disagreement")
  page.locator("#package").fill(json.dumps(package));approve()
  page.locator("#source").fill("def broken(:\n    pass\n")
  with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:page.locator("#run").click()
  value=response.value.json();assert value["status"]=="observed_mismatch" and value["kind"]=="exception",value.get("status")
  assert value["witness"]["student"].get("events",[])==[]
  assert page.locator("#graph .node").count()==0
  expect(page.locator("#step")).to_contain_text("لا توجد أحداث مسجلة");checks.append("syntax_exception_has_no_fabricated_trace")
  page.screenshot(path=str(out/"missing-trace.png"),full_page=True)
  timeout_source="l=1\nr=2\nwhile l<r:\n    mid=(l+r)//2\n    l=mid\n"
  page.locator("#source").fill(timeout_source)
  with page.expect_response(lambda r:r.url.endswith("/v4/profile"),timeout=45000) as response:page.locator("#profile-run").click()
  profile_outage=response.value.json()
  assert profile_outage["kind"]=="timeout" and profile_outage["ai_status"]=="unavailable_or_invalid"
  assert profile_outage["execution_diagnostics"]["findings"] and page.locator("#graph .node").count()>0
  expect(page.locator("#ai-state")).to_contain_text("تعذّر")
  expect(page.locator("#facts")).to_contain_text("تعذّر")
  (out/"profile-outage.json").write_text(json.dumps(profile_outage,indent=2),encoding="utf-8")
  checks.append("profile_opt_in_outage_keeps_timeout_evidence_and_explains_state")
  page.locator("#source").fill(timeout_source+"# profile-diagnosis-fixture\n")
  with page.expect_response(lambda r:r.url.endswith("/v4/profile"),timeout=45000) as response:page.locator("#profile-run").click()
  profile_ai=response.value.json()
  assert profile_ai["kind"]=="timeout" and profile_ai["ai_status"]=="ok"
  assert profile_ai["ai_facts"][0]["status"]=="matches_recorded_snapshot"
  assert profile_ai["ai_branches"][0]["status"]=="matches_recorded_condition"
  expect(page.locator("#ai-state")).to_contain_text("اكتمل")
  expect(page.locator("#facts")).to_contain_text("مطابق")
  expect(page.locator("#branch-facts")).to_contain_text("مطابق")
  assert "execution_status" in page.locator("#ai-context").text_content()
  page.locator("#hypotheses .hypothesis").first.click()
  expect(page.locator("#code .active")).to_contain_text("while")
  (out/"profile-fixture.json").write_text(json.dumps(profile_ai,indent=2),encoding="utf-8")
  checks.append("profile_checked_opt_in_hypotheses_facts_conditions_and_context")
  assert not errors,errors
  assert not external,external
  browser.close()
 report={"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,"scope":"Real browser and isolated worker; controlled mocked provider outage and authored negative packages. Opt-in success uses a controlled structured proposal. No live cloud request or human study."}
 (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps(report),flush=True)
if __name__=="__main__":main()
