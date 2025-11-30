#!/usr/bin/env python3
"""Quick check of H5P page HTML"""
import asyncio
from playwright.async_api import async_playwright

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
USERNAME = "student1"
PASSWORD = "Student2025!"


async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        # Login
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")

        # Check cmid=125
        await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id=125")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5)

        html = await page.content()

        # Search for H5P-related elements
        print("=== Searching for H5P elements ===")
        for term in ["h5p-iframe", "h5p-player", "h5p-content", "iframe", "class=\"h5p"]:
            if term in html:
                # Find context
                idx = html.find(term)
                snippet = html[max(0, idx-50):idx+100]
                print(f"\nFound '{term}':")
                print(f"  ...{snippet}...")

        # Also check for errors
        print("\n=== Checking for errors ===")
        for term in ["error", "Error", "alert-danger", "exception"]:
            if term in html.lower():
                idx = html.lower().find(term)
                snippet = html[max(0, idx-30):idx+100]
                print(f"\nFound '{term}':")
                print(f"  ...{snippet[:150]}...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(check())
