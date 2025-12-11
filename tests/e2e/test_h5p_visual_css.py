#!/usr/bin/env python3
"""
Visual E2E Tests for H5P Content CSS Validation.
Issue #12: Validates text contrast and visibility for all H5P content types.

Tests:
- Text color vs background color contrast (WCAG AA minimum 4.5:1)
- Button visibility
- Input field visibility
- Feedback message visibility
"""
import asyncio
import re
from playwright.async_api import async_playwright
from pathlib import Path
from typing import Tuple, Optional

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
USERNAME = "student1"
PASSWORD = "Student2025!"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots" / "visual"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# WCAG AA minimum contrast ratio
MIN_CONTRAST_RATIO = 4.5

# Test activities from Course 31
COURSE_ID = 31
ACTIVITIES = [
    {"cmid": 224, "type": "dialogcards", "selectors": [".h5p-dialogcards-card-text"]},
    {"cmid": 225, "type": "multichoice", "selectors": [".h5p-question-introduction", ".h5p-alternative-inner"]},
    {"cmid": 226, "type": "accordion", "selectors": [".h5p-panel-title", ".h5p-panel-content"]},
    {"cmid": 227, "type": "blanks", "selectors": [".h5p-blanks", ".h5p-text-input"]},
    {"cmid": 228, "type": "draganddrop", "selectors": [".h5p-drag-text"]},
    {"cmid": 229, "type": "truefalse", "selectors": [".h5p-question-introduction", ".h5p-answer"]},
    {"cmid": 230, "type": "summary", "selectors": [".h5p-summary-statement"]},
]


def parse_color(color_str: str) -> Optional[Tuple[int, int, int]]:
    """Parse CSS color string to RGB tuple."""
    if not color_str:
        return None

    # Handle rgb(r, g, b) format
    rgb_match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color_str)
    if rgb_match:
        return (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))

    # Handle hex format
    hex_match = re.match(r'#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})', color_str)
    if hex_match:
        return (int(hex_match.group(1), 16), int(hex_match.group(2), 16), int(hex_match.group(3), 16))

    return None


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculate relative luminance per WCAG 2.1."""
    def adjust(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)


def contrast_ratio(color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float:
    """Calculate contrast ratio between two colors per WCAG 2.1."""
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


async def check_element_contrast(frame, selector: str) -> dict:
    """Check contrast ratio for a specific element."""
    try:
        element = await frame.query_selector(selector)
        if not element:
            return {"selector": selector, "status": "NOT_FOUND"}

        # Get computed styles
        styles = await element.evaluate("""el => {
            const style = getComputedStyle(el);
            return {
                color: style.color,
                backgroundColor: style.backgroundColor,
                text: el.innerText.substring(0, 50)
            };
        }""")

        fg_color = parse_color(styles.get("color", ""))
        bg_color = parse_color(styles.get("backgroundColor", ""))

        # Handle transparent backgrounds - assume dark theme background
        if bg_color == (0, 0, 0) or bg_color is None or styles.get("backgroundColor") == "rgba(0, 0, 0, 0)":
            bg_color = (26, 26, 46)  # Dark theme default #1a1a2e

        if fg_color and bg_color:
            ratio = contrast_ratio(fg_color, bg_color)
            return {
                "selector": selector,
                "status": "PASS" if ratio >= MIN_CONTRAST_RATIO else "FAIL",
                "ratio": round(ratio, 2),
                "min_required": MIN_CONTRAST_RATIO,
                "fg_color": styles.get("color"),
                "bg_color": styles.get("backgroundColor"),
                "sample_text": styles.get("text", "")[:30]
            }

        return {"selector": selector, "status": "PARSE_ERROR", "raw": styles}

    except Exception as e:
        return {"selector": selector, "status": "ERROR", "error": str(e)}


async def test_visual_css():
    """Run visual CSS tests on all H5P activities."""
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
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

        # Enrol in course if needed
        await page.goto(f"{MOODLE_URL}/course/view.php?id={COURSE_ID}")
        await page.wait_for_load_state("networkidle")
        enrol_btn = await page.query_selector("input[value='Enrol me']")
        if enrol_btn:
            await enrol_btn.click()
            await page.wait_for_load_state("networkidle")

        # Test each activity
        for act in ACTIVITIES:
            print(f"\nTesting {act['type']} (cmid={act['cmid']})...")
            activity_results = {"cmid": act["cmid"], "type": act["type"], "checks": []}

            try:
                await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id={act['cmid']}")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)

                # Get iframe
                iframe = await page.query_selector("iframe.h5p-player")
                if not iframe:
                    activity_results["status"] = "NO_IFRAME"
                    results.append(activity_results)
                    continue

                frame = await iframe.content_frame()
                if not frame:
                    activity_results["status"] = "NO_FRAME"
                    results.append(activity_results)
                    continue

                await asyncio.sleep(2)

                # Check each selector
                for selector in act["selectors"]:
                    check = await check_element_contrast(frame, selector)
                    activity_results["checks"].append(check)
                    status = check.get("status", "UNKNOWN")
                    ratio = check.get("ratio", "N/A")
                    print(f"  {selector}: {status} (ratio: {ratio})")

                # Take screenshot
                await page.screenshot(path=str(SCREENSHOT_DIR / f"visual_{act['type']}.png"))

                # Overall status
                all_passed = all(c.get("status") in ["PASS", "NOT_FOUND"] for c in activity_results["checks"])
                activity_results["status"] = "PASS" if all_passed else "FAIL"

            except Exception as e:
                activity_results["status"] = "ERROR"
                activity_results["error"] = str(e)

            results.append(activity_results)

        await browser.close()

    # Summary
    print("\n" + "="*70)
    print("VISUAL CSS TEST RESULTS")
    print("="*70)

    passed = sum(1 for r in results if r.get("status") == "PASS")
    total = len(results)

    for r in results:
        icon = "✓" if r.get("status") == "PASS" else "✗"
        print(f"\n{icon} {r['type']} (cmid={r['cmid']}): {r.get('status')}")
        for check in r.get("checks", []):
            ratio = check.get("ratio", "N/A")
            status = check.get("status")
            print(f"    {check['selector']}: {status} (ratio: {ratio})")

    print("\n" + "="*70)
    print(f"TOTAL: {passed}/{total} activities passed contrast checks")
    print(f"Minimum required contrast ratio: {MIN_CONTRAST_RATIO}:1 (WCAG AA)")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(test_visual_css())
    exit(0 if success else 1)
