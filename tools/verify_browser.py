"""Optional UI verification using Playwright and an existing Chrome/Edge binary."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def available_browser():
    candidates = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
    candidates += [shutil.which("google-chrome"), shutil.which("chromium")]
    return next((str(p) for p in candidates if p and Path(p).is_file()), None)


def verify(executable=None, port=8787):
    from playwright.sync_api import sync_playwright
    url = f"http://127.0.0.1:{port}"
    output = ROOT / "docs/screenshots"
    output.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "algoxray.api:app", "--host", "127.0.0.1", "--port", str(port)],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("UI test server did not start")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=executable or available_browser(), headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
            errors, external = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def route_request(route):
                if route.request.url.startswith(url + "/"):
                    route.continue_()
                else:
                    external.append(route.request.url)
                    route.abort()

            page.route("**/*", route_request)
            page.goto(url + "/")
            page.locator("#connection-text").filter(has_text="المحرك متصل").wait_for()
            assert page.evaluate("document.body.scrollWidth") <= 1440
            page.screenshot(path=str(output / "initial-desktop.jpg"), type="jpeg", quality=85, full_page=True)
            page.locator("#analyze-button").click()
            page.locator("#status-title").filter(has_text="وجدنا حالة تؤكد اختلاف النتيجة").wait_for(timeout=60000)
            for _ in range(3):
                page.locator("#reveal-hint").click()
            assert page.locator(".hint-card").count() == 3
            page.locator(".hint-card button").click()
            assert page.locator(".code-line.current").count() == 1
            with page.expect_download() as download_info:
                page.locator("#download-evidence").click()
            evidence_file = output / "ui-export.json"
            download_info.value.save_as(str(evidence_file))
            evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
            assert evidence["status"] == "witness_found" and evidence["verification"]["replay_matches"] == 3
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(output / "dijkstra-desktop.jpg"), type="jpeg", quality=85, full_page=True)
            page.locator("#show-original").click()
            assert not page.locator("#step-range").is_enabled()
            page.locator("#show-reduced").click()
            assert page.locator("#step-range").is_enabled()
            page.locator('[data-problem="binary_search_v1"]').click()
            page.locator(".advanced > summary").click()
            page.locator("#manual-case").check()
            page.locator("#case-input").fill('{"array":[0],"target":0}')
            page.locator("#analyze-button").click()
            page.locator("#status-title").filter(has_text="وجدنا حالة تؤكد اختلاف النتيجة").wait_for()
            assert page.locator("#actual-output").inner_text() == "-1"
            assert page.locator("#expected-output").inner_text() == "0"
            page.locator("#reveal-hint").click()
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(output / "binary-desktop.jpg"), type="jpeg", quality=85, full_page=True)
            page.locator("#fixture-select").select_option("binary_correct")
            page.locator("#case-input").fill('{"array":[1,2,2,2,5],"target":2}')
            page.locator("#analyze-button").click()
            page.locator("#status-title").filter(has_text="لم نجد خطأ ضمن الميزانية").wait_for()
            assert not page.locator("#reveal-hint").is_enabled()
            page.locator("#case-input").fill("{invalid}")
            page.locator("#analyze-button").click()
            assert page.locator("#error-message").is_visible()
            page.locator('[data-problem="dijkstra_v1"]').click()
            page.locator("#manual-case").uncheck()
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.body.scrollWidth") <= 390
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(output / "mobile.jpg"), type="jpeg", quality=85, full_page=True)
            page.locator('[data-view="guide"]').click()
            assert page.locator("#view-guide").is_visible()
            page.locator('[data-view="experiments"]').click()
            page.locator("#benchmark-state").get_by_role("heading").wait_for()
            assert not errors, errors
            assert not external, external
            result = {"status": "passed", "journeys": ["offline_load", "generated_dijkstra", "trace_navigation", "source_bound_hint",
                      "json_export", "original_view", "binary_singleton", "duplicate_control", "invalid_json", "mobile_layout", "guide", "benchmark_view"],
                      "viewport_desktop": [1440, 1100], "viewport_mobile": [390, 844], "page_errors": errors,
                      "external_requests": external, "browser": browser.version, "url": url}
            (ROOT / "docs/ui-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result), flush=True)
            browser.close()
            return result
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    verify(args.browser, args.port)
