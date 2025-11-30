#!/usr/bin/env python3
"""
Use Playwright to update H5P libraries via Moodle Admin.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
ADMIN_USER = "admin"
ADMIN_PASS = "4Baumschulenweg$"

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def update_h5p_libraries():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        # Login as admin
        print("Logging in as admin...")
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", ADMIN_USER)
        await page.fill("#password", ADMIN_PASS)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")
        print("Logged in!")

        # Go to H5P settings
        print("\nGoing to H5P content type management...")
        await page.goto(f"{MOODLE_URL}/admin/settings.php?section=h5psettings")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        await page.screenshot(path=str(SCREENSHOT_DIR / "h5p_settings.png"))
        print("Screenshot saved: h5p_settings.png")

        # Go to H5P library management
        print("\nGoing to H5P libraries...")
        await page.goto(f"{MOODLE_URL}/h5p/libraries.php")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        await page.screenshot(path=str(SCREENSHOT_DIR / "h5p_libraries.png"), full_page=True)
        print("Screenshot saved: h5p_libraries.png")

        # Check if there's an update button
        update_btn = await page.query_selector("text='Update content types'")
        if update_btn:
            print("\nFound 'Update content types' button, clicking...")
            await update_btn.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            await page.screenshot(path=str(SCREENSHOT_DIR / "h5p_update_result.png"), full_page=True)
            print("Screenshot saved: h5p_update_result.png")

        # Keep browser open for manual inspection
        print("\nBrowser will stay open for 60 seconds for manual inspection...")
        await asyncio.sleep(60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(update_h5p_libraries())
