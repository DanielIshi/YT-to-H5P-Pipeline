#!/usr/bin/env python3
"""
Test H5P iframe loading and check iframe content.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
USERNAME = "student1"
PASSWORD = "Student2025!"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def test_iframe():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Non-headless for debugging
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        # Login
        print("Logging in...")
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")
        print("Logged in!")

        # Go to activity
        print("\nGoing to MultiChoice activity (cmid=102)...")
        await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id=102")
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)

        # Check for iframe
        iframe_element = await page.query_selector("iframe.h5p-player")
        if iframe_element:
            print("Found iframe.h5p-player!")

            # Get iframe src
            src = await iframe_element.get_attribute("src")
            print(f"  src: {src}")

            # Get iframe style
            style = await iframe_element.get_attribute("style")
            print(f"  style: {style}")

            # Try to access iframe content
            frame = await iframe_element.content_frame()
            if frame:
                print("  Can access iframe content!")
                await asyncio.sleep(2)

                # Check content inside iframe
                body_html = await frame.evaluate("document.body.innerHTML")
                print(f"  Body length: {len(body_html)}")

                if "not logged in" in body_html.lower():
                    print("  ERROR: 'not logged in' message in iframe!")
                elif "alert-danger" in body_html:
                    print("  ERROR: Alert-danger found in iframe!")
                else:
                    print("  Content seems OK")

                # Take screenshot of iframe content
                await frame.locator("body").screenshot(path=str(SCREENSHOT_DIR / "iframe_content.png"))
                print("  Saved: iframe_content.png")
            else:
                print("  Cannot access iframe content (cross-origin?)")
        else:
            print("No iframe.h5p-player found!")

        # Take full page screenshot
        await page.screenshot(path=str(SCREENSHOT_DIR / "full_page.png"), full_page=True)
        print("\nSaved: full_page.png")

        # Keep browser open for manual inspection
        print("\nBrowser will stay open for 30 seconds for inspection...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_iframe())
