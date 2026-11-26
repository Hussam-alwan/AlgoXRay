"""Browser acceptance of 0.2 via the same localhost UI as a presenter."""
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from verify_browser import available_browser

ROOT = Path(__file__).resolve().parents[1]
GRAPH = """def solve(payload):
    out = [None] * payload["n"]
    out[payload["source"]] = 0
    for u, v, w in payload["edges"]:
        if u == payload["source"]:
            out[v] = w
    return out
"""
BINARY = "def solve(data):\r\n    candidate = 0\r\n    return candidate\r\n"
FIXED = 'def solve(data):\n    return next((i for i, v in enumerate(data["array"]) if v == data["target"]), -1)\n'


def verify(url, output):
    output.mkdir(parents=True, exist_ok=True)
    journeys, errors, external = [], [], []
    def save(page, file):
        with page.expect_download() as dl:
            page.locator("#download-evidence").click()
        dl.value.save_as(str(output/file))
        return json.loads((output/file).read_text(encoding="utf-8"))
    def analyze(page):
        with page.expect_response(lambda r:r.url == url+"/api/analyze" and r.request.method=="POST",timeout=70000) as received:
            page.locator("#analyze-button").click()
        assert received.value.ok, received.value.status
        page.wait_for_function("!document.querySelector('#analyze-button').disabled")
        return received.value.json()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=browser.new_page(viewport={"width":1365,"height":960},device_scale_factor=1)
        page.on("pageerror",lambda error:errors.append(str(error)))
        def route(request):
            if request.request.url.startswith(url+"/"):
                request.continue_()
            else:
                external.append(request.request.url)
                request.abort()
        page.route("**/*",route)
        page.goto(url)
        page.locator("#connection-text").filter(has_text="المحرك متصل").wait_for()
        page.locator("#mode-custom").click()
        page.locator("#source-editor").fill(GRAPH)
        page.locator("#trusted-local-code").check()
        page.locator(".advanced summary").click()
        page.locator("#manual-case").check()
        page.locator("#case-input").fill('{"n":3,"edges":[[0,1,1],[0,2,3],[1,2,1]],"source":0}')
        graph = analyze(page)
        assert graph["witness_explanation"]["vertices"] == [0,1,2]
        assert graph["diagnosis"]["status"]=="witness_only"
        assert "1 + 1 = 2" in page.locator("#witness-values").inner_text()
        page.locator("#show-original").click()
        assert page.locator("#step-range").is_disabled()
        page.locator("#show-reduced").click()
        page.locator("#step-range").fill(str(max(0,len(graph["events"])-2)))
        assert page.evaluate("state.cy.elements('.current-edge,.current,.candidate').length")==0
        assert save(page,"graph-evidence.json")["submission"]["source"] == GRAPH
        page.locator("#witness-panel").scroll_into_view_if_needed()
        page.locator("#witness-panel").screenshot(path=str(output/"graph-proof.png"))
        page.locator(".analysis-grid").screenshot(path=str(output/"graph-trace.jpg"),type="jpeg",quality=85)
        journeys.extend(["graph_path_cost_and_source_export","custom_names_never_imply_graph_roles","original_trace_disabled"])
        page.locator('[data-problem="binary_search_v1"]').click()
        buf=b"\xef\xbb\xbf"+BINARY.encode()
        page.locator("#code-file").set_input_files({"name":"windows.py","mimeType":"text/plain","buffer":buf})
        page.locator("#editor-filename").filter(has_text="windows.py").wait_for()
        page.locator("#case-input").fill('{"array":[1,7,7],"target":7}')
        page.locator("#shrink").uncheck()
        b=analyze(page)
        assert b["submission"]["source"].encode()==buf and b["submission"]["source_sha256"]==hashlib.sha256(buf).hexdigest()
        assert b["claims"][-1]["adapter_id"]=="python_returned_index_v1"
        assert b["witness_explanation"]["matching_indices"] == [1,2]
        page.locator("#jump-to-diagnosis").click()
        assert page.locator("#code-container .current").get_attribute("data-line")=="3"
        save(page,"binary-evidence.json")
        journeys.extend(["bom_crlf_hash_roundtrip","return_line_and_all_duplicate_positions"])
        page.locator("#pin-witness").click()
        page.locator("#source-editor").fill(FIXED)
        assert page.locator("#download-evidence").is_disabled()
        corrected=analyze(page)
        assert corrected["manual_check"]["status"]=="pass" and corrected["manual_check"]["case"]==b["case"]
        assert "اجتاز الشاهد المحفوظ" in page.locator("#status-title").inner_text()
        save(page,"repair-evidence.json")
        page.locator("#witness-panel").scroll_into_view_if_needed()
        page.locator("#status-banner").screenshot(path=str(output/"repair-pass.png"))
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.documentElement.scrollWidth")<=390
        page.locator("#clear-witness").click()
        assert not page.locator("#manual-case").is_checked()
        journeys.extend(["repair_pins_identical_input","passing_repair_export","fresh_search_after_repair","phone_390"])
        assert not errors and not external,(errors,external)
        (output/"browser.json").write_text(json.dumps({"url":url,"browser":browser.version,"journeys":journeys,"page_errors":errors,"external_requests":external},indent=2),encoding="utf-8")
        print(json.dumps(journeys))
        browser.close()

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--url",default="http://127.0.0.1:8000")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    verify(args.url.rstrip("/"),args.out)
