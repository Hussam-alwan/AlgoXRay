"""Observe the delivered editor on the user's existing loopback service."""
import base64
import json
from pathlib import Path
import urllib.request

from playwright.sync_api import sync_playwright
from verify_browser import available_browser
from verify_custom_browser import SOURCE

ROOT = Path(__file__).resolve().parents[1]


def main():
    url = "http://127.0.0.1:8000"
    with urllib.request.urlopen(url + "/api/health", timeout=3) as response:
        health = json.load(response)
    assert health.get("custom_code") is True
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=available_browser(), headless=True)
        page = browser.new_page(viewport={"width": 1150, "height": 800})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        page.locator("#connection-text").filter(has_text="المحرك متصل").wait_for()
        page.locator('[data-problem="binary_search_v1"]').click()
        page.locator("#mode-custom").click()
        page.locator("#source-editor").fill(SOURCE)
        page.locator("#trusted-local-code").check()
        page.locator(".advanced > summary").click()
        page.locator("#manual-case").check()
        page.locator("#case-input").fill('{"array":[7],"target":7}')
        page.locator("#shrink").uncheck()
        page.locator("#analyze-button").click()
        page.locator("#status-title").filter(has_text="وجدنا حالة تؤكد اختلاف النتيجة").wait_for(timeout=60000)
        assert page.locator("#actual-output").inner_text() == "-1"
        assert page.locator("#expected-output").inner_text() == "0"
        assert "السطر 6" in page.locator("#diagnosis-text").inner_text()
        assert not errors, errors
        page.locator("#diagnosis-summary").scroll_into_view_if_needed()
        shot = ROOT / "docs/screenshots/custom-code-live.jpg"
        page.screenshot(path=str(shot), type="jpeg", quality=25)
        result = {"status": "passed", "url": url, "custom_code": True, "actual": -1, "expected": 0,
                  "supported_condition_line": 6, "page_errors": errors, "screenshot": str(shot.relative_to(ROOT))}
        (ROOT / "docs/custom-code-live-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({**result, "screenshot_bytes": shot.stat().st_size}))
        browser.close()


if __name__ == "__main__":
    main()
