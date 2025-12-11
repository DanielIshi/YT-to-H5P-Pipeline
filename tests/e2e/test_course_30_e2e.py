#!/usr/bin/env python3
"""
E2E Test: Verify Course 30 H5P content displays correctly.
Tests all 8 activities in the newly generated course.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
USERNAME = "student1"
PASSWORD = "Student2025!"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Course 31 activities (cmid 224-230)
COURSE_ID = 31
ACTIVITIES = [
    {"cmid": 224, "title": "Kernbegriffe der KI-Entwicklung", "type": "dialogcards"},
    {"cmid": 225, "title": "Was sind Humanoide Roboter?", "type": "multichoice"},
    {"cmid": 226, "title": "Hauptthemen der KI-Entwicklung", "type": "accordion"},
    {"cmid": 227, "title": "Wichtige Aussagen zur KI", "type": "blanks"},
    {"cmid": 228, "title": "Kategorisierung von KI-Anwendungen", "type": "draganddrop"},
    {"cmid": 229, "title": "Stimmt das?", "type": "truefalse"},
    {"cmid": 230, "title": "Was haben Sie gelernt?", "type": "summary"},
]


async def test_course_30():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        # Login
        print("Logging in as student1...")
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")
        print("Logged in!")

        # Enrol in course if needed
        print("Checking course enrolment...")
        await page.goto(f"{MOODLE_URL}/course/view.php?id={COURSE_ID}")
        await page.wait_for_load_state("networkidle")
        enrol_button = await page.query_selector("input[value='Enrol me'], button:has-text('Enrol')")
        if enrol_button:
            print("Enrolling in course...")
            await enrol_button.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)
            print("Enrolled!")

        # Test each activity
        for act in ACTIVITIES:
            print(f"\nTesting {act['type']}: {act['title']} (cmid={act['cmid']})...")

            try:
                await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id={act['cmid']}")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)  # Wait for H5P to load

                # Check for iframe
                iframe = await page.query_selector("iframe.h5p-player")
                if not iframe:
                    results.append({"cmid": act["cmid"], "type": act["type"], "status": "FAIL", "error": "No iframe found"})
                    continue

                # Access iframe content
                frame = await iframe.content_frame()
                if not frame:
                    results.append({"cmid": act["cmid"], "type": act["type"], "status": "FAIL", "error": "Cannot access iframe"})
                    continue

                await asyncio.sleep(2)

                # Check content inside iframe
                body_html = await frame.evaluate("document.body.innerHTML")

                # Check for errors
                if "error" in body_html.lower() and "alert-danger" in body_html:
                    results.append({"cmid": act["cmid"], "type": act["type"], "status": "FAIL", "error": "Error in iframe content"})
                elif len(body_html) < 100:
                    results.append({"cmid": act["cmid"], "type": act["type"], "status": "FAIL", "error": "Empty content"})
                elif "h5p-content" in body_html or "h5p-" in body_html:
                    # Check for specific content type elements
                    has_content = False
                    if act["type"] == "dialogcards" and "h5p-dialogcards" in body_html:
                        has_content = True
                    elif act["type"] == "multichoice" and ("h5p-multichoice" in body_html or "h5p-answer" in body_html):
                        has_content = True
                    elif act["type"] == "accordion" and "h5p-accordion" in body_html:
                        has_content = True
                    elif act["type"] == "blanks" and "h5p-blanks" in body_html:
                        has_content = True
                    elif act["type"] == "draganddrop" and ("h5p-drag" in body_html or "draggable" in body_html.lower()):
                        has_content = True
                    elif act["type"] == "truefalse" and ("h5p-true-false" in body_html or "true" in body_html.lower()):
                        has_content = True
                    elif act["type"] == "summary" and "h5p-summary" in body_html:
                        has_content = True
                    elif act["type"] == "interactivevideo" and ("h5p-interactive-video" in body_html or "video" in body_html.lower()):
                        has_content = True
                    else:
                        # Generic H5P content check
                        has_content = "h5p-content" in body_html

                    if has_content:
                        results.append({"cmid": act["cmid"], "type": act["type"], "status": "PASS"})
                        # Take screenshot
                        await page.screenshot(path=str(SCREENSHOT_DIR / f"course30_{act['cmid']}_{act['type']}.png"))
                    else:
                        results.append({"cmid": act["cmid"], "type": act["type"], "status": "PARTIAL", "note": "H5P present but type-specific elements not found"})
                else:
                    results.append({"cmid": act["cmid"], "type": act["type"], "status": "FAIL", "error": "No H5P content found"})

            except Exception as e:
                results.append({"cmid": act["cmid"], "type": act["type"], "status": "ERROR", "error": str(e)})
                print(f"  Error: {e}")

        await browser.close()

    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS FOR COURSE 30")
    print("="*60)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] in ["FAIL", "ERROR"])

    for r in results:
        status_icon = "✓" if r["status"] == "PASS" else "✗" if r["status"] in ["FAIL", "ERROR"] else "~"
        error_info = f" - {r.get('error', r.get('note', ''))}" if r.get('error') or r.get('note') else ""
        print(f"  {status_icon} [{r['cmid']}] {r['type']}: {r['status']}{error_info}")

    print("="*60)
    print(f"TOTAL: {passed}/{len(results)} passed")

    if failed > 0:
        print("\nE2E VERIFICATION FAILED!")
        return False
    else:
        print("\nE2E VERIFICATION PASSED!")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_course_30())
    exit(0 if success else 1)
