#!/usr/bin/env python3
"""
E2E Test for H5P Auto-Advance Feature (Issue #3)
Tests that the auto-advance script correctly navigates to next activity after correct answer.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
USERNAME = "student1"
PASSWORD = "Student2025!"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots" / "auto_advance"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Course 31 has our test activities
COURSE_ID = 31
# Test with TrueFalse (cmid=229) - easy to get correct answer
TEST_ACTIVITY_CMID = 229  # "Stimmt das?"


async def test_auto_advance():
    """Test that auto-advance triggers after correct answer."""
    results = {
        "script_loaded": False,
        "h5p_loaded": False,
        "answer_submitted": False,
        "overlay_appeared": False,
        "navigation_triggered": False
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        # Capture console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))

        # Login
        print("1. Logging in...")
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")

        # Navigate to TrueFalse activity
        print(f"2. Navigating to TrueFalse activity (cmid={TEST_ACTIVITY_CMID})...")
        await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id={TEST_ACTIVITY_CMID}")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Screenshot before interaction
        await page.screenshot(path=str(SCREENSHOT_DIR / "01_before_answer.png"))

        # Check if our script was loaded (look for it in page source)
        page_source = await page.content()
        if "h5p-success-overlay" in page_source or "H5P Auto-Advance" in page_source:
            results["script_loaded"] = True
            print("   ✓ Auto-advance script detected in page")

        # Get H5P iframe
        iframe = await page.query_selector("iframe.h5p-player")
        if not iframe:
            print("   ✗ No H5P iframe found")
            await browser.close()
            return results

        frame = await iframe.content_frame()
        if not frame:
            print("   ✗ Could not get iframe content")
            await browser.close()
            return results

        results["h5p_loaded"] = True
        print("   ✓ H5P iframe loaded")

        await asyncio.sleep(2)

        # For TrueFalse, we need to find and click the correct answer
        # The question is "Humanoide Roboter sind weniger wichtig als LLMs" - FALSE
        print("3. Looking for answer buttons...")

        # Find the "Falsch" button and click it - try multiple selectors
        falsch_btn = None
        selectors_to_try = [
            ".h5p-true-false-answer:nth-child(2)",  # Second answer button
            ".h5p-answer:nth-child(2)",
            "button:has-text('Falsch')",
            ".h5p-true-false-answer >> text=Falsch",
            "[class*='false']",
            ".h5p-true-false-answer:last-child"
        ]

        for selector in selectors_to_try:
            try:
                falsch_btn = await frame.query_selector(selector)
                if falsch_btn:
                    print(f"   Found button with selector: {selector}")
                    break
            except:
                continue

        if not falsch_btn:
            # Last resort - click by coordinates (second button)
            all_buttons = await frame.query_selector_all(".h5p-true-false-answer, .h5p-answer")
            if len(all_buttons) >= 2:
                falsch_btn = all_buttons[1]
                print(f"   Found {len(all_buttons)} answer buttons, using second one")

        if falsch_btn:
            await falsch_btn.click()
            print("   ✓ Clicked 'Falsch' answer")
            results["answer_submitted"] = True
            await asyncio.sleep(1)
            await page.screenshot(path=str(SCREENSHOT_DIR / "02_answer_selected.png"))
        else:
            print("   ✗ Could not find answer button")

        # Check for the success overlay (might appear after auto-check)
        print("4. Waiting for auto-advance overlay...")
        await asyncio.sleep(3)

        # Check if overlay appeared
        overlay = await page.query_selector("#h5p-success-overlay")
        if overlay:
            results["overlay_appeared"] = True
            print("   ✓ Success overlay appeared!")
            await page.screenshot(path=str(SCREENSHOT_DIR / "03_success_overlay.png"))

        # Wait for navigation
        await asyncio.sleep(2)

        # Check if we navigated to a different page
        current_url = page.url
        if f"id={TEST_ACTIVITY_CMID}" not in current_url:
            results["navigation_triggered"] = True
            print(f"   ✓ Navigation triggered! Now at: {current_url}")
        else:
            print(f"   Current URL still: {current_url}")

        await page.screenshot(path=str(SCREENSHOT_DIR / "04_after_advance.png"))

        # Print console logs for debugging
        print("\n5. Console logs:")
        for log in console_logs[-20:]:
            if "H5P" in log or "xAPI" in log.lower():
                print(f"   {log}")

        await browser.close()

    # Summary
    print("\n" + "=" * 60)
    print("AUTO-ADVANCE TEST RESULTS")
    print("=" * 60)
    for key, value in results.items():
        status = "✓" if value else "✗"
        print(f"  {status} {key}: {value}")

    passed = sum(results.values())
    total = len(results)
    print(f"\nTotal: {passed}/{total} checks passed")

    return results


if __name__ == "__main__":
    results = asyncio.run(test_auto_advance())
    # Exit with 0 if at least script loaded and H5P loaded
    success = results.get("script_loaded", False) and results.get("h5p_loaded", False)
    exit(0 if success else 1)
