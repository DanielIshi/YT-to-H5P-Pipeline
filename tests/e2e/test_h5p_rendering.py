#!/usr/bin/env python3
"""
Playwright E2E test for H5P rendering in Moodle.
Tests which content types actually render vs just show intro text.
"""
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
USERNAME = "student1"
PASSWORD = "Student2025!"

# Test all content types in Section 11
CONTENT_TYPES = {
    101: "Dialogcards",
    102: "MultiChoice",
    103: "Accordion",
    104: "(-) TrueFalse",
    105: "(-) Blanks",
    106: "(-) Summary",
    107: "(-) DragAndDrop",
    110: "[FIXED] Blanks",
    111: "[FIXED] Summary",
    112: "[FIXED] TrueFalse",
    113: "[FIXED] DragText",
    114: "[OFFICIAL] Blanks",
}

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def test_h5p_rendering():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            # Add permissions for cross-origin iframes
            bypass_csp=True
        )
        page = await context.new_page()

        # Enable cross-origin isolation
        await context.grant_permissions(["clipboard-read", "clipboard-write"])

        # Collect console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # Login
        print("Logging in...")
        await page.goto(f"{MOODLE_URL}/login/index.php")
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#loginbtn")
        await page.wait_for_load_state("networkidle")

        results = {}

        for cmid, name in CONTENT_TYPES.items():
            console_errors.clear()
            print(f"\n{'='*50}")
            print(f"Testing cmid={cmid}: {name}")

            try:
                await page.goto(f"{MOODLE_URL}/mod/h5pactivity/view.php?id={cmid}", timeout=30000)
                await page.wait_for_load_state("domcontentloaded", timeout=20000)
            except Exception as e:
                print(f"  Navigation error: {e}")
                continue

            # Wait for H5P iframe to load
            await asyncio.sleep(5)

            # Take screenshot
            await page.screenshot(path=str(SCREENSHOT_DIR / f"cmid_{cmid}.png"), full_page=True)
            print(f"  Screenshot saved: cmid_{cmid}.png")

            # Save page HTML for debugging
            html_content = await page.content()
            with open(SCREENSHOT_DIR / f"cmid_{cmid}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"  HTML saved: cmid_{cmid}.html")

            # Check if H5P iframe exists on page
            h5p_iframe = await page.query_selector("iframe.h5p-iframe")
            h5p_embed = await page.query_selector(".h5p-iframe-wrapper")
            h5p_placeholder = await page.query_selector("[data-region='h5p-player']")
            print(f"  h5p-iframe element: {h5p_iframe is not None}")
            print(f"  h5p-iframe-wrapper: {h5p_embed is not None}")
            print(f"  h5p-player region: {h5p_placeholder is not None}")

            # Check iframe dimensions
            iframe_info = await page.evaluate("""
                () => {
                    const iframe = document.querySelector('iframe.h5p-iframe');
                    if (!iframe) return { found: false };
                    const style = window.getComputedStyle(iframe);
                    return {
                        found: true,
                        width: style.width,
                        height: style.height,
                        computedHeight: iframe.offsetHeight,
                        src: iframe.src
                    };
                }
            """)

            # Check for H5P content inside iframe
            h5p_content = await page.evaluate("""
                () => {
                    const iframe = document.querySelector('iframe.h5p-iframe');
                    if (!iframe || !iframe.contentDocument) return { accessible: false };
                    try {
                        const doc = iframe.contentDocument;
                        const body = doc.body;
                        const h5pContainer = doc.querySelector('.h5p-container');
                        const h5pContent = doc.querySelector('.h5p-content');
                        const hasQuestion = doc.querySelector('.h5p-question') !== null;
                        const hasBlanksFillIn = doc.querySelector('.h5p-blanks') !== null;
                        const hasSummary = doc.querySelector('.h5p-summary') !== null;
                        const hasDialogcards = doc.querySelector('.h5p-dialogcards') !== null;
                        const hasAccordion = doc.querySelector('.h5p-accordion') !== null;
                        const hasMultiChoice = doc.querySelector('.h5p-multichoice') !== null;
                        const hasTrueFalse = doc.querySelector('.h5p-true-false') !== null;
                        const hasDragText = doc.querySelector('.h5p-drag-text') !== null;

                        return {
                            accessible: true,
                            bodyHTML: body ? body.innerHTML.substring(0, 500) : '',
                            hasContainer: h5pContainer !== null,
                            hasContent: h5pContent !== null,
                            hasQuestion: hasQuestion,
                            hasBlanksFillIn: hasBlanksFillIn,
                            hasSummary: hasSummary,
                            hasDialogcards: hasDialogcards,
                            hasAccordion: hasAccordion,
                            hasMultiChoice: hasMultiChoice,
                            hasTrueFalse: hasTrueFalse,
                            hasDragText: hasDragText,
                            bodyLength: body ? body.innerHTML.length : 0
                        };
                    } catch (e) {
                        return { accessible: false, error: e.toString() };
                    }
                }
            """)

            # Determine if rendered
            rendered = False
            height = iframe_info.get('computedHeight', 0)
            if height > 100 and h5p_content.get('bodyLength', 0) > 1000:
                rendered = True

            results[cmid] = {
                "name": name,
                "rendered": rendered,
                "iframe_height": height,
                "body_length": h5p_content.get('bodyLength', 0),
                "has_container": h5p_content.get('hasContainer', False),
                "has_content": h5p_content.get('hasContent', False),
                "has_question": h5p_content.get('hasQuestion', False),
                "console_errors": console_errors.copy()
            }

            status = "✓ RENDERED" if rendered else "✗ FAILED"
            print(f"  {status}")
            print(f"  iframe height: {height}px")
            print(f"  body length: {h5p_content.get('bodyLength', 0)}")
            print(f"  has container: {h5p_content.get('hasContainer', False)}")
            print(f"  has content: {h5p_content.get('hasContent', False)}")
            if console_errors:
                print(f"  JS errors: {len(console_errors)}")
                for err in console_errors[:3]:
                    print(f"    - {err[:100]}")

        await browser.close()

        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        rendered_count = sum(1 for r in results.values() if r['rendered'])
        total = len(results)
        print(f"Rendered: {rendered_count}/{total}")

        print("\nWorking:")
        for cmid, r in results.items():
            if r['rendered']:
                print(f"  ✓ {r['name']} (cmid={cmid})")

        print("\nFailed:")
        for cmid, r in results.items():
            if not r['rendered']:
                print(f"  ✗ {r['name']} (cmid={cmid}, height={r['iframe_height']}px)")

        return results


if __name__ == "__main__":
    asyncio.run(test_h5p_rendering())
