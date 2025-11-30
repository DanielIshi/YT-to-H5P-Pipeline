#!/usr/bin/env python3
"""
Test H5P console errors to find the root cause of rendering issues.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
USERNAME = "student1"
PASSWORD = "Student2025!"

# Test one working and one broken
TEST_ACTIVITIES = {
    102: "MultiChoice (WORKS)",
    104: "TrueFalse (BROKEN)",
}


async def test_console():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        # Collect ALL console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append({
            "type": msg.type,
            "text": msg.text
        }))

        # Login
        print("Logging in...")
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")

        for cmid, name in TEST_ACTIVITIES.items():
            console_messages.clear()
            print(f"\n{'='*60}")
            print(f"Testing cmid={cmid}: {name}")
            print(f"{'='*60}")

            await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id={cmid}")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)  # Wait for H5P to load

            # Print all console messages
            print(f"\nConsole messages ({len(console_messages)}):")
            errors = [m for m in console_messages if m['type'] == 'error']
            warnings = [m for m in console_messages if m['type'] == 'warning']

            if errors:
                print(f"\n  ERRORS ({len(errors)}):")
                for e in errors[:10]:
                    print(f"    - {e['text'][:200]}")

            if warnings:
                print(f"\n  WARNINGS ({len(warnings)}):")
                for w in warnings[:5]:
                    print(f"    - {w['text'][:150]}")

            # Check for H5P specific messages
            h5p_msgs = [m for m in console_messages if 'h5p' in m['text'].lower()]
            if h5p_msgs:
                print(f"\n  H5P-related messages:")
                for m in h5p_msgs[:10]:
                    print(f"    [{m['type']}] {m['text'][:200]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_console())
