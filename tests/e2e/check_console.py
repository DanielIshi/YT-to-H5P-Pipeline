#!/usr/bin/env python3
"""Check console errors and network requests"""
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

        console_msgs = []
        failed_requests = []

        page.on("console", lambda msg: console_msgs.append({
            "type": msg.type,
            "text": msg.text
        }))

        page.on("requestfailed", lambda req: failed_requests.append({
            "url": req.url,
            "failure": req.failure
        }))

        # Login
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")

        console_msgs.clear()
        failed_requests.clear()

        # Check cmid=125
        print("Loading H5P activity cmid=125...")
        await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id=125")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(8)  # Wait longer for H5P

        print(f"\n=== Console messages ({len(console_msgs)}) ===")
        for msg in console_msgs:
            if msg["type"] in ["error", "warning"]:
                print(f"[{msg['type']}] {msg['text'][:200]}")

        print(f"\n=== Failed requests ({len(failed_requests)}) ===")
        for req in failed_requests:
            print(f"  {req['url'][:100]}")
            print(f"    Failure: {req['failure']}")

        # Check iframe src
        iframe = await page.query_selector("iframe.h5p-player")
        if iframe:
            src = await iframe.get_attribute("src")
            print(f"\n=== H5P iframe src ===\n{src}")

            # Check iframe dimensions
            box = await iframe.bounding_box()
            print(f"\nIframe bounding box: {box}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(check())
