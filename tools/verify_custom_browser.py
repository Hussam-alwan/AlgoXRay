"""Real browser journeys for pasted local Python, file import and evidence-backed locations."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from verify_browser import available_browser

ROOT = Path(__file__).resolve().parents[1]
SOURCE = """def solve(payload):
    array = payload["array"]
    target = payload["target"]
    left = 0
    right = len(array) - 1
    while left < right:
        mid = (left + right) // 2
        if array[mid] == target:
            return mid
        if array[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""


def verify():
    from playwright.sync_api import sync_playwright
    url = "http://127.0.0.1:8789"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 8789))
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "algoxray.api:app", "--host", "127.0.0.1", "--port", "8789"],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    journeys = []
    errors, external, posts = [], [], []
    output = ROOT / "docs/screenshots"
    output.mkdir(parents=True, exist_ok=True)
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
                    if json.load(response).get("custom_code"):
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Custom-code server did not start")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=available_browser(), headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: posts.append(request.url) if request.method == "POST" else None)

            def route_request(route):
                if route.request.url.startswith(url + "/"):
                    route.continue_()
                else:
                    external.append(route.request.url)
                    route.abort()

            page.route("**/*", route_request)
            page.goto(url)
            page.locator("#connection-text").filter(has_text="المحرك متصل").wait_for()
            page.locator('[data-problem="binary_search_v1"]').click()
            page.locator("#mode-custom").click()
            assert page.locator("#custom-source-panel").is_visible()
            assert not page.locator("#fixture-select").is_visible()
            page.locator("#source-editor").fill(SOURCE)
            page.locator(".advanced > summary").click()
            page.locator("#manual-case").check()
            page.locator("#case-input").fill('{"array":[7],"target":7}')
            page.locator("#shrink").uncheck()
            page.locator("#analyze-button").click()
            assert page.locator("#error-message").is_visible()
            assert not posts
            journeys.append("local_trust_gate")
            page.locator("#trusted-local-code").check()
            page.locator("#analyze-button").click()
            page.locator("#status-title").filter(has_text="وجدنا حالة تؤكد اختلاف النتيجة").wait_for(timeout=60000)
            assert page.locator("#actual-output").inner_text() == "-1"
            assert page.locator("#expected-output").inner_text() == "0"
            assert "السطر 6" in page.locator("#diagnosis-text").inner_text()
            assert page.locator("#code-container .current").get_attribute("data-line") == "6"
            assert "left" in page.locator("#variables-container").inner_text()
            journeys.append("pasted_code_to_specific_observation")
            page.locator("#jump-to-diagnosis").click()
            assert page.locator("#code-container .current").get_attribute("data-line") == "6"
            for _ in range(3):
                page.locator("#reveal-hint").click()
            assert page.locator(".hint-card").count() == 3
            page.locator(".hint-card").last.get_by_role("button").click()
            journeys.append("diagnostic_event_navigation")
            with page.expect_download() as download:
                page.locator("#download-evidence").click()
            exported = ROOT / "results/custom-code-browser-evidence.json"
            download.value.save_as(str(exported))
            bundle = json.loads(exported.read_text(encoding="utf-8"))
            assert bundle["submission"]["source"] == SOURCE
            assert bundle["submission"]["adapter_id"] is None
            assert bundle["diagnosis"]["status"] == "supported"
            journeys.append("custom_evidence_export")
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(path=str(output / "custom-code-desktop.jpg"), type="jpeg", quality=85, full_page=True)
            page.locator("#source-editor").fill(SOURCE.replace("while left < right:", "while left <= right:"))
            assert not page.locator("#download-evidence").is_enabled()
            assert not page.locator("#diagnosis-summary").is_visible()
            page.locator("#analyze-button").click()
            page.locator("#status-title").filter(has_text="لم نجد خطأ ضمن الميزانية").wait_for()
            assert not page.locator("#diagnosis-summary").is_visible()
            journeys.append("edit_invalidates_old_evidence_and_correct_solution")
            page.locator("#source-editor").fill("def solve(payload):\n    return -1\n")
            page.locator("#analyze-button").click()
            page.locator("#status-title").filter(has_text="وجدنا حالة تؤكد اختلاف النتيجة").wait_for()
            assert "لا يوجد دليل كاف" in page.locator("#diagnosis-text").inner_text()
            journeys.append("unknown_logic_abstention")
            page.locator("#source-editor").fill("def solve(payload)\n    return -1\n")
            page.locator("#analyze-button").click()
            page.locator("#error-message").filter(has_text="السطر 1").wait_for()
            assert not page.locator("#download-evidence").is_enabled()
            journeys.append("syntax_error_line")
            page.locator("#source-editor").fill("def solve(payload):\n    items = payload['array']\n    return items[len(items)]\n")
            page.locator("#analyze-button").click()
            page.locator("#status-title").filter(has_text="وجدنا حالة يتوقف عليها الحل").wait_for()
            assert page.locator("#actual-output").inner_text() == "IndexError"
            assert "السطر 3" in page.locator("#diagnosis-text").inner_text()
            assert page.locator("#code-container .current").get_attribute("data-line") == "3"
            journeys.append("runtime_exception_exact_line")
            renamed = SOURCE.replace("left", "begin").replace("right", "finish")
            page.locator("#code-file").set_input_files({"name": "my_renamed_binary.py", "mimeType": "text/x-python", "buffer": renamed.encode()})
            page.wait_for_function("document.getElementById('editor-filename').textContent === 'my_renamed_binary.py'")
            assert page.locator("#source-editor").input_value() == renamed
            page.locator("#analyze-button").click()
            page.locator("#status-title").filter(has_text="وجدنا حالة تؤكد اختلاف النتيجة").wait_for()
            assert "begin" in page.locator("#diagnosis-text").inner_text()
            journeys.append("file_import_and_renamed_variables")
            page.locator('[data-problem="dijkstra_v1"]').click()
            page.locator("#source-editor").fill("def solve(payload):\n    return [0] * payload['n']\n")
            page.locator('[data-problem="binary_search_v1"]').click()
            assert page.locator("#source-editor").input_value() == renamed
            page.locator("#mode-fixture").click()
            assert page.locator("#fixture-select").is_visible()
            page.locator("#mode-custom").click()
            assert page.locator("#source-editor").input_value() == renamed
            journeys.append("per_problem_draft_retention")
            page.locator("#load-bug-example").click()
            assert "while left < right:" in page.locator("#source-editor").input_value()
            page.locator("#manual-case").uncheck()
            page.locator("#shrink").check()
            page.locator("#analyze-button").click()
            page.locator("#status-title").filter(has_text="وجدنا حالة تؤكد اختلاف النتيجة").wait_for(timeout=60000)
            assert "موضع مدعوم" in page.locator("#diagnosis-badge").inner_text()
            journeys.append("generated_counterexample_for_pasted_source")
            page.locator("#source-editor").fill(SOURCE + '\n# <img src="https://invalid.example/should-not-load" onerror="alert(1)">\n')
            assert page.locator("#code-container img").count() == 0
            assert '<img src=' in page.locator("#code-container").inner_text()
            journeys.append("source_rendered_as_text")
            before = len(posts)
            page.locator("#code-file").set_input_files({"name": "too_large.py", "mimeType": "text/x-python", "buffer": b"#" * 40000})
            page.locator("#error-message").filter(has_text="32 KiB").wait_for()
            assert len(posts) == before
            journeys.append("file_size_limit")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth") <= 390
            page.locator("#source-editor").scroll_into_view_if_needed()
            page.screenshot(path=str(output / "custom-code-mobile.jpg"), type="jpeg", quality=85)
            journeys.append("mobile_editor_layout")
            assert not errors, errors
            assert not external, external
            result = {"status": "passed", "journeys": journeys, "page_errors": errors, "external_requests": external,
                      "browser": browser.version, "url": url, "exported_evidence": str(exported.relative_to(ROOT))}
            (ROOT / "docs/custom-code-ui-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result), flush=True)
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    verify()
