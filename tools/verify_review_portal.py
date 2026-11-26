"""Exercise the standalone reviewer portal without producing real study ratings."""
import argparse
from pathlib import Path
import csv
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright
from verify_browser import available_browser

def verify(path):
    with TemporaryDirectory() as temp,sync_playwright() as p:
        b=p.chromium.launch(executable_path=available_browser(),headless=True)
        page=b.new_page(accept_downloads=True,viewport={"width":1280,"height":900})
        errors=[];network=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("request",lambda r:network.append(r.url) if r.url.startswith(("http:","https:")) else None)
        page.goto(path.resolve().as_uri())
        page.locator("#reviewer").fill("SYNTHETIC-UI-TEST-NOT-A-REVIEWER")
        page.locator("#save").click()
        assert "required" in page.locator("#ratingStatus").inner_text()
        page.locator("#verdict").select_option("uncheckable")
        page.locator("#reason").fill('UI test only, "quoted" text.\nNot a human rating.')
        page.locator("#save").click()
        assert "1 /" in page.locator("#progress").inner_text()
        with page.expect_download() as d: page.locator("#export-claim").click()
        target=Path(temp)/"claim.csv";d.value.save_as(str(target))
        rows=list(csv.DictReader(target.open(encoding="utf-8",newline="")))
        assert len(rows)==1 and rows[0]["reviewer"].startswith("SYNTHETIC") and "\n" in rows[0]["reason"]
        page.reload()
        page.locator("#resume").set_input_files(str(target))
        assert "Imported" in page.locator("#importStatus").inner_text()
        assert "1 /" in page.locator("#progress").inner_text()
        page.locator("#location-tab").click()
        page.locator("#verdict").select_option("located")
        page.locator("#lines").fill("999999")
        page.locator("#reason").fill("UI-only validation test.")
        page.locator("#save").click()
        assert "valid 1-based" in page.locator("#ratingStatus").inner_text()
        page.locator("#lines").fill("1;1")
        page.locator("#save").click()
        with page.expect_download() as d: page.locator("#export-location").click()
        location=Path(temp)/"loc.csv";d.value.save_as(str(location))
        rows=list(csv.DictReader(location.open(encoding="utf-8",newline="")))
        assert rows[0]["acceptable_lines"]=="1"
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.documentElement.scrollWidth<=390")
        assert not errors and not network,(errors,network)
        b.close()
        print("Reviewer portal validation, CSV export/import, location validation and mobile passed; synthetic temporary ratings discarded.")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("path",type=Path);a=p.parse_args();verify(a.path)
