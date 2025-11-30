#!/usr/bin/env python3
"""
Update H5P libraries via Moodle Admin interface.
This is the CORRECT way to fix the H5P.Question theme bug.
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
        print("1. Logging in as admin...")
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", ADMIN_USER)
        await page.fill("#password", ADMIN_PASS)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")
        print("   Logged in!")

        # Go to H5P content type management
        print("\n2. Going to H5P content type management...")
        await page.goto(f"{MOODLE_URL}/h5p/libraries.php")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        await page.screenshot(path=str(SCREENSHOT_DIR / "h5p_libraries_before.png"), full_page=True)

        # Look for Update button
        print("\n3. Looking for 'Update content types' button...")
        update_btn = await page.query_selector("text='Update content types'")

        if not update_btn:
            # Try alternative selectors
            update_btn = await page.query_selector("input[value*='Update']")

        if not update_btn:
            update_btn = await page.query_selector("button:has-text('Update')")

        if update_btn:
            print("   Found update button, clicking...")
            await update_btn.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(10)  # Wait for update to complete
            await page.screenshot(path=str(SCREENSHOT_DIR / "h5p_update_result.png"), full_page=True)
            print("   Update initiated!")
        else:
            print("   No update button found. Checking current library versions...")

            # Check TrueFalse version
            truefalse = await page.query_selector("text='H5P.TrueFalse'")
            if truefalse:
                row = await truefalse.evaluate_handle("el => el.closest('tr')")
                version_cell = await row.query_selector("td:nth-child(2)")
                if version_cell:
                    version = await version_cell.text_content()
                    print(f"   TrueFalse version: {version}")

        # Check final state
        print("\n4. Final state of H5P libraries:")
        await page.screenshot(path=str(SCREENSHOT_DIR / "h5p_libraries_after.png"), full_page=True)

        # Now test one of the activities
        print("\n5. Testing H5P activity rendering...")
        await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id=127")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5)

        # Check for errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        await page.screenshot(path=str(SCREENSHOT_DIR / "h5p_test_after_update.png"), full_page=True)

        # Check iframe height
        iframe = await page.query_selector("iframe.h5p-player")
        if iframe:
            box = await iframe.bounding_box()
            print(f"   Iframe dimensions: {box}")
            if box and box['height'] > 50:
                print("   SUCCESS: H5P content is rendering!")
            else:
                print("   FAIL: Iframe has no height")
        else:
            print("   FAIL: No iframe found")

        print("\n6. Keeping browser open for 30 seconds for inspection...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(update_h5p_libraries())
