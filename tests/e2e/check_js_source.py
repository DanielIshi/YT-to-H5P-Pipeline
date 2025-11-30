#!/usr/bin/env python3
"""Check which JS file is actually being loaded for TrueFalse"""
import asyncio
from playwright.async_api import async_playwright

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
USERNAME = "student1"
PASSWORD = "Student2025!"


async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Clear browser cache by using fresh context
        context = await browser.new_context(
            ignore_https_errors=True,
            bypass_csp=True
        )
        page = await context.new_page()

        js_requests = []

        def log_request(request):
            url = request.url
            if 'true-false' in url.lower() or 'truefalse' in url.lower():
                js_requests.append(url)

        page.on("request", log_request)

        # Login
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")

        # Load H5P
        print("Loading H5P activity...")
        await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id=125")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5)

        print(f"\n=== TrueFalse JS requests ({len(js_requests)}) ===")
        for url in js_requests:
            print(f"  {url}")

        # Try to fetch the embed page and find script URLs
        embed_url = "https://moodle.srv947487.hstgr.cloud/h5p/embed.php?url=https%3A%2F%2Fmoodle.srv947487.hstgr.cloud%2Fpluginfile.php%2F168%2Fmod_h5pactivity%2Fpackage%2F0%2Ftest_truefalse.h5p"

        page2 = await context.new_page()
        all_scripts = []
        page2.on("request", lambda r: all_scripts.append(r.url) if r.resource_type == "script" else None)

        await page2.goto(embed_url)
        await page2.wait_for_load_state("networkidle")
        await asyncio.sleep(5)

        print(f"\n=== All script requests from embed page ({len(all_scripts)}) ===")
        for url in all_scripts:
            print(f"  {url[:120]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(check())
