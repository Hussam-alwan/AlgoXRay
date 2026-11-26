"""Print owned local report HTML using an installed Edge/Chrome and Playwright."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    candidates = [Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
                  Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe"]
    executable = next((p for p in candidates if p.is_file()), None)
    if not executable:
        raise SystemExit("Install Edge/Chrome or export the HTML through your browser's print dialog")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(executable), headless=True)
        for name in ("poster", "manuscript_draft"):
            page = browser.new_page(viewport={"width": 1588, "height": 2245})
            page.goto((ROOT / f"docs/{name}.html").as_uri(), wait_until="load")
            page.emulate_media(media="print")
            dimensions = page.evaluate("({width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight})")
            page.pdf(path=str(ROOT / f"docs/{name}.pdf"), prefer_css_page_size=True, print_background=True)
            print(json.dumps({"file": f"docs/{name}.pdf", "layout": dimensions}))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
