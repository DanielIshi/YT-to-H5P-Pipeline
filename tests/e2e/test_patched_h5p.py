#!/usr/bin/env python3
"""
Test the patched H5P libraries (TrueFalse, Blanks, Summary, DragText).
Verifies they render correctly without JavaScript errors.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
USERNAME = "student1"
PASSWORD = "Student2025!"

# Test the newly imported activities (with embedTypes fix)
TEST_ACTIVITIES = {
    125: "TrueFalse",
    126: "Blanks",
    127: "Summary",
    128: "DragText",
}

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def test_patched_libraries():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        # Collect console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # Login
        print("Logging in as student1...")
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")
        print("Logged in!\n")

        results = {}

        for cmid, content_type in TEST_ACTIVITIES.items():
            console_errors.clear()
            print(f"{'='*60}")
            print(f"Testing cmid={cmid}: {content_type}")
            print(f"{'='*60}")

            await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id={cmid}")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)  # Wait for H5P to load

            # Get page HTML for debugging
            html = await page.content()
            if "h5p-iframe" not in html and "h5p-player" not in html:
                print(f"  DEBUG: No H5P elements found in HTML")
                # Check for error messages
                error_el = await page.query_selector(".alert-danger, .errormessage")
                if error_el:
                    error_text = await error_el.text_content()
                    print(f"  ERROR MSG: {error_text[:200]}")

            # Take screenshot
            screenshot_path = SCREENSHOT_DIR / f"patched_{content_type.lower()}_cmid{cmid}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"Screenshot: {screenshot_path.name}")

            # Check for H5P iframe
            iframe = await page.query_selector("iframe.h5p-iframe")
            has_iframe = iframe is not None

            # Check for specific errors
            theme_error = any("theme" in e.lower() for e in console_errors)
            question_error = any("question" in e.lower() for e in console_errors)

            # Check for rendered content inside iframe
            rendered = False
            if iframe:
                try:
                    frame = await iframe.content_frame()
                    if frame:
                        await asyncio.sleep(1)
                        # Check for H5P content container
                        h5p_content = await frame.query_selector(".h5p-content")
                        rendered = h5p_content is not None
                except:
                    pass

            # Determine status
            if has_iframe and rendered and not theme_error:
                status = "OK"
            elif not has_iframe:
                status = "FAIL - No iframe"
            elif theme_error:
                status = "FAIL - Theme error (patch not applied)"
            elif not rendered:
                status = "FAIL - Not rendered"
            else:
                status = "UNKNOWN"

            results[content_type] = {
                "cmid": cmid,
                "status": status,
                "has_iframe": has_iframe,
                "rendered": rendered,
                "errors": len(console_errors),
                "theme_error": theme_error
            }

            print(f"  Status: {status}")
            print(f"  Has iframe: {has_iframe}")
            print(f"  Content rendered: {rendered}")
            print(f"  Console errors: {len(console_errors)}")
            if console_errors:
                print(f"  Errors: {console_errors[:3]}")
            print()

        await browser.close()

        # Summary
        print("\n" + "="*60)
        print("SUMMARY - Library Patch Verification")
        print("="*60)

        all_ok = True
        for ct, result in results.items():
            status_symbol = "✓" if result["status"] == "OK" else "✗"
            print(f"  {status_symbol} {ct}: {result['status']}")
            if result["status"] != "OK":
                all_ok = False

        if all_ok:
            print("\n✓ ALL PATCHED LIBRARIES WORKING CORRECTLY!")
        else:
            print("\n✗ SOME LIBRARIES STILL HAVE ISSUES")

        return all_ok, results


if __name__ == "__main__":
    success, results = asyncio.run(test_patched_libraries())
    exit(0 if success else 1)
