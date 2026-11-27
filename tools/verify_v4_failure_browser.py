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
  def propose(self,*args,**kwargs):raise ProviderError("controlled_test_provider_unavailable")
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
  page.route("**/*",route);page.goto(url+"/v4")
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
  page.locator("#package").fill(json.dumps(package));approve()
  page.locator("#source").fill("def broken(:\n    pass\n")
  with page.expect_response(lambda r:r.url.endswith("/v4/analyze"),timeout=90000) as response:page.locator("#run").click()
  value=response.value.json();assert value["status"]=="observed_mismatch" and value["kind"]=="exception",value.get("status")
  assert value["witness"]["student"].get("events",[])==[]
  assert page.locator("#graph .node").count()==0
  expect(page.locator("#step")).to_contain_text("No events");checks.append("syntax_exception_has_no_fabricated_trace")
  page.screenshot(path=str(out/"missing-trace.png"),full_page=True)
  assert not errors,errors
  assert not external,external
  browser.close()
 report={"status":"passed","checks":checks,"page_errors":errors,"external_requests":external,"scope":"Real browser and isolated worker; controlled mocked provider outage and authored negative packages. No live cloud request or human study."}
 (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps(report),flush=True)
if __name__=="__main__":main()
