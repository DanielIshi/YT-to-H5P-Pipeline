#!/usr/bin/env python3
"""
E2E Test: NotebookLM Mindmap Animation

Complete flow:
1. Create new notebook
2. Add text source
3. Generate mindmap
4. Extract and animate

XPaths based on Nov 2025 NotebookLM UI (user-provided).
"""

import asyncio
import logging
import sys
import subprocess
import socket
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from src.adapters.notebooklm.config import NotebookLMConfig
from src.adapters.notebooklm.mindmap_extractor import MindmapExtractor, MindmapData
from src.adapters.notebooklm.mindmap_animator import MindmapAnimator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def is_chrome_debug_port_open(port=9222):
    """Check if Chrome debug port is already listening"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(('localhost', port))
        return result == 0
    finally:
        sock.close()


def start_chrome_if_needed():
    """Start Chrome with debug port if not already running"""
    if is_chrome_debug_port_open():
        logger.info("Chrome debug port already open, connecting to existing session...")
        return True

    logger.info("Starting Chrome with debug port...")
    chrome_path = r'C:\Users\Daniel\AppData\Local\Google\Chrome\Application\chrome.exe'
    user_data = r'C:\Users\Daniel\chrome-debug-profile'

    subprocess.Popen([
        chrome_path,
        '--remote-debugging-port=9222',
        f'--user-data-dir={user_data}',
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for Chrome to start
    for _ in range(10):
        if is_chrome_debug_port_open():
            logger.info("Chrome started successfully")
            return True
        import time
        time.sleep(1)

    logger.error("Failed to start Chrome")
    return False


# Test content - kurzer Text für schnelle Verarbeitung
TEST_CONTENT = """
Künstliche Intelligenz (KI) in Unternehmen

1. Einführung
KI transformiert die Geschäftswelt. Unternehmen nutzen Machine Learning und Deep Learning für Automatisierung und Entscheidungsfindung.

2. Anwendungsbereiche
- Kundenservice: Chatbots und virtuelle Assistenten
- Marketing: Personalisierung und Predictive Analytics
- Produktion: Qualitätskontrolle und Predictive Maintenance
- Finanzen: Betrugserkennung und Risikobewertung

3. Implementierung
Erfolgreiche KI-Projekte erfordern:
- Klare Zieldefinition
- Qualitativ hochwertige Daten
- Iterative Entwicklung
- Change Management

4. Herausforderungen
- Datenschutz und Compliance
- Fachkräftemangel
- Integration in bestehende Systeme
- Erklärbarkeit von KI-Entscheidungen

5. Zukunftsperspektiven
Generative KI, LLMs und Autonomous Agents werden die nächste Welle der digitalen Transformation antreiben.
"""

# XPaths from Nov 2025 NotebookLM UI (user-provided)
XPATHS = {
    # Welcome page
    "neu_erstellen": "/html/body/labs-tailwind-root/div/welcome-page/div/div[1]/div/div[2]/div/div/button",

    # Studio panel (right side)
    "mindmap_btn": "/html/body/labs-tailwind-root/div/notebook/div/section[3]/studio-panel/div/div[1]/basic-create-artifact-button[3]",
    "artifact_library": "/html/body/labs-tailwind-root/div/notebook/div/section[3]/studio-panel/div/div[3]/artifact-library",
}


async def check_artifact_completion(page):
    """Check if any artifact shows 'X Quelle - Vor X Min.' (completion indicator)"""
    result = await page.evaluate("""
        () => {
            const artifactLib = document.querySelector('artifact-library');
            if (!artifactLib) return {found: false, reason: 'no artifact-library'};

            const text = artifactLib.innerText || '';

            // Check for "X Quelle - Vor X Min." pattern (German)
            const match = text.match(/(\\d+)\\s*Quelle.*Vor\\s*(\\d+)/i);
            if (match) {
                return {found: true, sources: match[1], minutes: match[2], text: text.substring(0, 100)};
            }

            // Check for "wird erstellt" (still generating)
            if (text.includes('wird erstellt') || text.includes('Creating')) {
                return {found: false, reason: 'still generating', text: text.substring(0, 100)};
            }

            return {found: false, reason: 'no completion pattern', text: text.substring(0, 100)};
        }
    """)
    return result


async def run_e2e_test():
    """Complete E2E test with NotebookLM"""
    output_dir = Path(__file__).parent / "output" / "notebooklm" / "animation"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info("=" * 60)
    logger.info("NotebookLM Mindmap E2E Test")
    logger.info("=" * 60)

    # Ensure Chrome is running with debug port
    if not start_chrome_if_needed():
        logger.error("Cannot connect to Chrome. Please start Chrome manually with --remote-debugging-port=9222")
        return False

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        logger.info("Connected to Chrome")

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(60000)

        try:
            # ============================================================
            # STEP 1: Navigate to NotebookLM
            # ============================================================
            await page.goto("https://notebooklm.google.com")
            logger.info("Navigating to NotebookLM...")

            # Wait for "Neu erstellen" button using XPath
            await page.wait_for_selector(f'xpath={XPATHS["neu_erstellen"]}', timeout=60000)
            logger.info("✅ Page loaded")
            await page.screenshot(path=str(output_dir / f"01_home_{timestamp}.png"))

            # ============================================================
            # STEP 2: Click "Neu erstellen"
            # ============================================================
            logger.info("Step 1: Creating new notebook...")
            await page.click(f'xpath={XPATHS["neu_erstellen"]}')
            logger.info("  Clicked 'Neu erstellen'")
            await asyncio.sleep(2)
            await page.screenshot(path=str(output_dir / f"02_popup_{timestamp}.png"))

            # ============================================================
            # STEP 3: Click "Kopierter Text" chip
            # ============================================================
            logger.info("Step 2: Clicking 'Kopierter Text' chip...")

            # The chip is in the upload dialog
            chip_clicked = False
            chip_selectors = [
                'mat-chip:has-text("Kopierter Text")',
                'text="Kopierter Text"',
                '.mdc-evolution-chip:has-text("Kopierter Text")',
            ]

            for selector in chip_selectors:
                try:
                    elem = await page.wait_for_selector(selector, timeout=3000)
                    if elem:
                        await elem.click()
                        logger.info(f"  Clicked 'Kopierter Text' via: {selector}")
                        chip_clicked = True
                        break
                except:
                    continue

            if not chip_clicked:
                logger.warning("  Could not find chip, please click 'Kopierter Text' manually...")
                await asyncio.sleep(10)

            await asyncio.sleep(2)
            await page.screenshot(path=str(output_dir / f"03_text_dialog_{timestamp}.png"))

            # ============================================================
            # STEP 4: Enter text in textarea (in the dialog overlay)
            # ============================================================
            logger.info("Step 3: Entering text content...")

            # The textarea should be in a dialog overlay (.cdk-overlay-container)
            # Wait for it to appear
            textarea = None
            for attempt in range(15):
                # Look specifically in the overlay container (dialog)
                textarea = await page.query_selector('.cdk-overlay-container textarea')
                if not textarea:
                    textarea = await page.query_selector('textarea')

                if textarea:
                    is_disabled = await textarea.get_attribute('disabled')
                    if is_disabled is None:
                        logger.info(f"  Found editable textarea (attempt {attempt + 1})")
                        break
                    else:
                        textarea = None  # Reset if disabled

                logger.info(f"  Waiting for textarea... ({attempt + 1}/15)")
                await asyncio.sleep(1)

            if not textarea:
                logger.error("  Could not find textarea in dialog!")
                await page.screenshot(path=str(output_dir / f"error_no_textarea_{timestamp}.png"))
                return False

            # Focus and fill
            await textarea.click(force=True)
            await asyncio.sleep(0.5)
            await textarea.fill(TEST_CONTENT)
            logger.info(f"  Entered {len(TEST_CONTENT)} chars")
            await page.screenshot(path=str(output_dir / f"04_text_entered_{timestamp}.png"))

            # ============================================================
            # STEP 5: Click "Einfügen" button (in the dialog)
            # ============================================================
            logger.info("Step 4: Clicking 'Einfügen'...")

            # Look for the button in the dialog overlay
            insert_clicked = False
            insert_selectors = [
                '.cdk-overlay-container button:has-text("Einfügen")',
                'button:has-text("Einfügen")',
                '.cdk-overlay-container button[type="submit"]',
                'form button[type="submit"]',
            ]

            for sel in insert_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=3000)
                    if btn:
                        await btn.click()
                        logger.info(f"  Clicked 'Einfügen' via: {sel}")
                        insert_clicked = True
                        break
                except:
                    continue

            if not insert_clicked:
                # Try pressing Enter as fallback
                logger.warning("  Could not find 'Einfügen' button, pressing Enter...")
                await page.keyboard.press("Enter")

            # ============================================================
            # STEP 6: Wait for notebook creation
            # ============================================================
            logger.info("Step 5: Waiting for notebook creation...")
            await asyncio.sleep(3)

            # Wait for URL to contain /notebook/
            for i in range(30):
                if "/notebook/" in page.url:
                    logger.info(f"  Notebook created after {i+1}s")
                    break
                await asyncio.sleep(1)

            await asyncio.sleep(3)
            notebook_id = page.url.split("/notebook/")[-1].split("/")[0].split("?")[0] if "/notebook/" in page.url else "unknown"
            logger.info(f"  Notebook ID: {notebook_id}")
            await page.screenshot(path=str(output_dir / f"05_notebook_ready_{timestamp}.png"))

            # ============================================================
            # STEP 7: Click Mind map button in Studio panel
            # ============================================================
            logger.info("Step 6: Generating Mind map...")

            # Use the exact XPath for mindmap button
            try:
                await page.click(f'xpath={XPATHS["mindmap_btn"]}', timeout=10000)
                logger.info("  Clicked Mind map button via XPath")
            except:
                # Fallback selectors
                fallback_selectors = [
                    'button:has-text("Mindmap")',
                    'button:has-text("Mind map")',
                    'basic-create-artifact-button:nth-child(3)',
                ]
                for sel in fallback_selectors:
                    try:
                        await page.click(sel, timeout=3000)
                        logger.info(f"  Clicked via fallback: {sel}")
                        break
                    except:
                        continue

            await page.screenshot(path=str(output_dir / f"06_mindmap_generating_{timestamp}.png"))

            # ============================================================
            # STEP 8: Wait for Mind map completion (check every 3s)
            # ============================================================
            logger.info("Step 7: Waiting for Mind map generation...")
            logger.info("  Checking every 3s for 'X Quelle - Vor X Min.' pattern...")

            mindmap_ready = False
            for i in range(30):  # Max 90 seconds (30 * 3s)
                await asyncio.sleep(3)

                status = await check_artifact_completion(page)
                if status.get('found'):
                    logger.info(f"  ✅ Mind map ready after {(i+1)*3}s!")
                    logger.info(f"     {status.get('sources')} Quelle(n), Vor {status.get('minutes')} Min.")
                    mindmap_ready = True
                    break

                reason = status.get('reason', 'unknown')
                if reason == 'still generating':
                    logger.info(f"  Still generating... ({(i+1)*3}s)")
                else:
                    logger.info(f"  Waiting... ({(i+1)*3}s) - {reason}")

                # Take screenshot every 15s
                if (i+1) % 5 == 0:
                    await page.screenshot(path=str(output_dir / f"07_generating_{(i+1)*3}s_{timestamp}.png"))

            await page.screenshot(path=str(output_dir / f"08_mindmap_ready_{timestamp}.png"))

            if not mindmap_ready:
                logger.warning("  Mind map generation timeout - trying to proceed anyway...")

            # ============================================================
            # STEP 9: Click on the Mind map artifact to open it
            # ============================================================
            logger.info("Step 8: Opening Mind map view...")

            # Click on the artifact in artifact-library (right panel)
            # Look for completed artifact with "Quelle - Vor" text
            result = await page.evaluate("""
                () => {
                    const artifactLib = document.querySelector('artifact-library');
                    if (!artifactLib) return {error: 'No artifact-library found'};

                    // Find all clickable items
                    const items = artifactLib.querySelectorAll('button, div[role="button"], [tabindex="0"]');
                    for (const item of items) {
                        const text = item.innerText || '';
                        // Match completed artifacts
                        if (text.match(/\\d+\\s*Quelle.*Vor/i)) {
                            item.click();
                            return {success: true, text: text.substring(0, 60)};
                        }
                    }

                    // Fallback: click first item with flowchart icon
                    const flowchart = artifactLib.querySelector('mat-icon[fonticon="flowchart"]');
                    if (flowchart) {
                        const parent = flowchart.closest('button, div[role="button"], [tabindex="0"]');
                        if (parent) {
                            parent.click();
                            return {success: true, method: 'flowchart icon'};
                        }
                    }

                    return {error: 'No artifact to click'};
                }
            """)

            if result.get('success'):
                logger.info(f"  Clicked artifact: {result.get('text', result.get('method', 'unknown'))}")
            else:
                logger.warning(f"  Could not click artifact: {result}")
                logger.info("  👆 Please click on the Mind map artifact in the right panel...")
                await asyncio.sleep(15)

            await asyncio.sleep(5)  # Wait for mindmap to render
            await page.screenshot(path=str(output_dir / f"09_mindmap_view_{timestamp}.png"))

            # ============================================================
            # STEP 10: Extract Mind map SVG
            # ============================================================
            logger.info("Step 9: Extracting Mind map SVG...")

            await asyncio.sleep(2)

            svg_content = await page.evaluate("""
                () => {
                    const svgs = document.querySelectorAll('svg');
                    let best = null;
                    let bestSize = 0;

                    for (const svg of svgs) {
                        const html = svg.outerHTML;
                        // Look for SVG with node markers
                        if (html.includes('class="node"') && html.length > bestSize) {
                            best = html;
                            bestSize = html.length;
                        }
                    }

                    // Fallback: largest SVG > 5KB
                    if (!best) {
                        for (const svg of svgs) {
                            if (svg.outerHTML.length > bestSize && svg.outerHTML.length > 5000) {
                                best = svg.outerHTML;
                                bestSize = svg.outerHTML.length;
                            }
                        }
                    }

                    return best;
                }
            """)

            if svg_content:
                logger.info(f"  ✅ SVG extracted: {len(svg_content)} chars")

                # Save SVG
                svg_path = output_dir / f"mindmap_{timestamp}.svg"
                svg_path.write_text(svg_content, encoding="utf-8")
                logger.info(f"  Saved to: {svg_path}")

                # Parse nodes
                class MockClient:
                    def __init__(self, pg, cfg):
                        self._page = pg
                        self.config = cfg
                    @property
                    def page(self):
                        return self._page

                config = NotebookLMConfig(output_dir=output_dir)
                client = MockClient(page, config)
                extractor = MindmapExtractor(client)

                nodes = extractor._extract_nodes_from_svg(svg_content)
                logger.info(f"  Extracted {len(nodes)} nodes")

                if nodes:
                    for node in nodes[:5]:
                        logger.info(f"    - {node.text} (level {node.level})")
                    if len(nodes) > 5:
                        logger.info(f"    ... and {len(nodes) - 5} more")

                    # Build hierarchy and create animation
                    # _build_hierarchy needs nodes and connections (empty list if not available)
                    root = extractor._build_hierarchy(nodes, [])
                    if root:
                        mindmap_data = MindmapData(
                            notebook_id=notebook_id,
                            notebook_title="Test Mindmap",
                            root_node=root,
                            nodes=nodes,
                            svg_content=svg_content
                        )

                        # Create animation timeline
                        animator = MindmapAnimator(client)
                        timeline = animator.create_sequential_timeline(mindmap_data, pause_per_node=2.0)

                        logger.info(f"  Animation timeline: {len(timeline.steps)} steps, {timeline.total_duration}s")

                        # Save timeline
                        timeline_path = output_dir / f"timeline_{timestamp}.json"
                        import json
                        timeline_data = {
                            "steps": [
                                {
                                    "timestamp": s.timestamp,
                                    "action": s.action,
                                    "node_id": s.node_id,
                                    "node_text": s.node_text,
                                    "duration": s.duration
                                }
                                for s in timeline.steps
                            ],
                            "total_duration": timeline.total_duration
                        }
                        timeline_path.write_text(json.dumps(timeline_data, indent=2), encoding="utf-8")
                        logger.info(f"  Timeline saved to: {timeline_path}")

                        logger.info("")
                        logger.info("🎉 SUCCESS! Mind map extracted and animation timeline created.")
                        return True

            else:
                logger.error("  ❌ No Mind map SVG found!")
                await page.screenshot(path=str(output_dir / f"error_no_svg_{timestamp}.png"))

            return False

        except Exception as e:
            logger.error(f"Test failed: {e}")
            try:
                await page.screenshot(path=str(output_dir / f"error_{timestamp}.png"))
            except:
                pass
            raise

        finally:
            logger.info("")
            logger.info("=" * 60)
            logger.info("TEST COMPLETE")
            logger.info(f"Output: {output_dir}")
            logger.info("=" * 60)
            logger.info("Tab kept open for review")


if __name__ == "__main__":
    success = asyncio.run(run_e2e_test())
    sys.exit(0 if success else 1)
