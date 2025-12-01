"""
NotebookLM Harvester - Prüft und lädt fertige Inhalte

Öffnet ein existierendes Notebook und lädt alle fertigen Inhalte herunter.
Kann beliebig oft ausgeführt werden bis alles fertig ist.

Usage:
    python -m src.adapters.notebooklm.notebook_harvester \
        --url "https://notebooklm.google.com/notebook/ABC123" \
        --output-dir tests/output/notebooklm
"""

import asyncio
import argparse
import json
import logging
import re
import sys
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Tuple
from datetime import datetime

from .client import NotebookLMClient
from .config import NotebookLMConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ContentStatus:
    """Status of a single content type"""
    status: str  # "ready", "generating", "not_started", "error"
    file: Optional[str] = None


@dataclass
class HarvestResult:
    """Result of harvest operation"""
    notebook_url: str
    audio: ContentStatus = field(default_factory=lambda: ContentStatus("unknown"))
    video: ContentStatus = field(default_factory=lambda: ContentStatus("unknown"))
    mindmap: ContentStatus = field(default_factory=lambda: ContentStatus("unknown"))


class NotebookHarvester:
    """
    Checks and downloads ready content from NotebookLM notebook.

    NotebookLM Studio Panel Structure (Dec 2025):
    - Each artifact is an <artifact-library-item>
    - Icon in <mat-icon class="artifact-icon"> determines type:
      - audio_magic_era = Audio
      - subscriptions = Video
      - flowchart = Mindmap
      - tablet = Briefing Doc
      - quiz = Quiz
      - stacked_bar_chart = Infografik
      - cards_star = Lernkarten
    - Ready items have "Vor X Min/Std" in .artifact-details
    - Audio/Video have play button with aria-label="Wiedergeben"
    - Download via 3-dot menu (more_vert) -> "Herunterladen"
    """

    # Icon names for content types
    AUDIO_ICON = "audio_magic_era"
    VIDEO_ICON = "subscriptions"
    MINDMAP_ICON = "flowchart"

    # Ready indicator: "X Quelle · Vor X Min."
    READY_INDICATOR = "Vor "

    # Generating indicators
    GENERATING_INDICATORS = [
        "Kommen Sie in ein paar Minuten wieder",
        "Come back in a few minutes",
        "wird erstellt",
        "Generating"
    ]

    def __init__(self, client: NotebookLMClient, output_dir: Path):
        self.client = client
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def harvest(self, notebook_url: str, types: Optional[list] = None) -> HarvestResult:
        """
        Check and download all ready content from notebook.

        Args:
            notebook_url: URL of the notebook
            types: List of types to harvest ["audio", "video", "mindmap"], default all

        Returns:
            HarvestResult with status and file paths
        """
        types = types or ["audio", "video", "mindmap"]

        result = HarvestResult(notebook_url=notebook_url)
        page = self.client.page

        # Open notebook
        logger.info(f"Opening notebook: {notebook_url}")
        await page.goto(notebook_url)
        await asyncio.sleep(3)

        # Harvest each type (close panel between each to avoid overlap)
        if "audio" in types:
            result.audio = await self._harvest_audio()
            await self._close_panel()

        if "video" in types:
            result.video = await self._harvest_video()
            await self._close_panel()

        if "mindmap" in types:
            result.mindmap = await self._harvest_mindmap()

        return result

    async def _close_panel(self):
        """Close any open panel by pressing Escape or clicking outside"""
        page = self.client.page
        try:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
        except:
            pass

    async def _find_artifact_by_icon(self, icon_name: str) -> Optional[tuple]:
        """
        Find artifact-library-item by its icon name.

        Args:
            icon_name: Icon text like "audio_magic_era", "subscriptions", "flowchart"

        Returns:
            Tuple of (item_element, title, is_ready) or None if not found
        """
        page = self.client.page
        items = await page.query_selector_all('artifact-library-item')

        for item in items:
            # Get icon text
            icon_el = await item.query_selector('mat-icon.artifact-icon')
            if not icon_el:
                continue

            icon_text = (await icon_el.text_content() or "").strip()
            if icon_name not in icon_text:
                continue

            # Found matching item - get title and check if ready
            title_el = await item.query_selector('.artifact-title')
            title = (await title_el.text_content() or "").strip() if title_el else "Unknown"

            details_el = await item.query_selector('.artifact-details')
            details = (await details_el.text_content() or "") if details_el else ""

            is_ready = self.READY_INDICATOR in details
            is_generating = any(ind in details for ind in self.GENERATING_INDICATORS)

            logger.info(f"Found {icon_name}: '{title}' - ready={is_ready}, generating={is_generating}")

            if is_generating:
                return (item, title, False)

            return (item, title, is_ready)

        return None

    async def _harvest_audio(self) -> ContentStatus:
        """Check and download audio if ready from Studio panel"""
        page = self.client.page

        try:
            # Find audio artifact by icon
            result = await self._find_artifact_by_icon(self.AUDIO_ICON)

            if result is None:
                logger.info("No audio artifact found")
                return ContentStatus(status="not_started")

            item, title, is_ready = result

            if not is_ready:
                logger.info(f"Audio '{title}' is still generating")
                return ContentStatus(status="generating")

            logger.info(f"Audio '{title}' is ready, downloading...")

            # Click the 3-dot menu button (more_vert)
            more_btn = await item.query_selector('button[aria-label="Mehr"]')
            if not more_btn:
                logger.error("Could not find 'Mehr' button on audio item")
                return ContentStatus(status="error")

            await more_btn.click()
            await asyncio.sleep(1)

            # Click "Herunterladen" in the menu
            output_path = self.output_dir / "audio" / f"audio_{datetime.now():%Y%m%d_%H%M%S}.mp3"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                async with page.expect_download(timeout=30000) as download_info:
                    # Try different selectors for download button
                    download_clicked = False
                    for selector in [
                        'button:has-text("Herunterladen")',
                        'button:has-text("Download")',
                        '[role="menuitem"]:has-text("Herunterladen")',
                        '[role="menuitem"]:has-text("Download")',
                    ]:
                        try:
                            await page.click(selector, timeout=3000)
                            download_clicked = True
                            break
                        except:
                            continue

                    if not download_clicked:
                        raise Exception("Could not click download button")

                download = await download_info.value
                await download.save_as(str(output_path))
                logger.info(f"Audio downloaded: {output_path}")
                return ContentStatus(status="ready", file=str(output_path))

            except Exception as e:
                logger.error(f"Download failed: {e}")
                # Close menu
                await page.keyboard.press("Escape")
                return ContentStatus(status="error")

        except Exception as e:
            logger.error(f"Audio harvest failed: {e}")
            return ContentStatus(status="error")

    async def _harvest_video(self) -> ContentStatus:
        """Check and download video if ready from Studio panel"""
        page = self.client.page

        try:
            # Find video artifact by icon
            result = await self._find_artifact_by_icon(self.VIDEO_ICON)

            if result is None:
                logger.info("No video artifact found")
                return ContentStatus(status="not_started")

            item, title, is_ready = result

            if not is_ready:
                logger.info(f"Video '{title}' is still generating")
                return ContentStatus(status="generating")

            logger.info(f"Video '{title}' is ready, downloading...")

            # Click the 3-dot menu button (more_vert)
            more_btn = await item.query_selector('button[aria-label="Mehr"]')
            if not more_btn:
                logger.error("Could not find 'Mehr' button on video item")
                return ContentStatus(status="error")

            await more_btn.click()
            await asyncio.sleep(1)

            # Click "Herunterladen" in the menu
            output_path = self.output_dir / "video" / f"video_{datetime.now():%Y%m%d_%H%M%S}.mp4"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                async with page.expect_download(timeout=60000) as download_info:
                    download_clicked = False
                    for selector in [
                        'button:has-text("Herunterladen")',
                        'button:has-text("Download")',
                        '[role="menuitem"]:has-text("Herunterladen")',
                        '[role="menuitem"]:has-text("Download")',
                    ]:
                        try:
                            await page.click(selector, timeout=3000)
                            download_clicked = True
                            break
                        except:
                            continue

                    if not download_clicked:
                        raise Exception("Could not click download button")

                download = await download_info.value
                await download.save_as(str(output_path))
                logger.info(f"Video downloaded: {output_path}")
                return ContentStatus(status="ready", file=str(output_path))

            except Exception as e:
                logger.error(f"Download failed: {e}")
                await page.keyboard.press("Escape")
                return ContentStatus(status="error")

        except Exception as e:
            logger.error(f"Video harvest failed: {e}")
            return ContentStatus(status="error")

    async def _harvest_mindmap(self) -> ContentStatus:
        """Check and extract mindmap if ready from Studio panel"""
        page = self.client.page

        try:
            # Find mindmap artifact by icon
            result = await self._find_artifact_by_icon(self.MINDMAP_ICON)

            if result is None:
                logger.info("No mindmap artifact found")
                return ContentStatus(status="not_started")

            item, title, is_ready = result

            if not is_ready:
                logger.info(f"Mindmap '{title}' is still generating")
                return ContentStatus(status="generating")

            logger.info(f"Mindmap '{title}' is ready, opening to extract SVG...")

            # Click the mindmap card to open it (not the menu)
            card_btn = await item.query_selector('button.artifact-button-content')
            if card_btn:
                await card_btn.click()
            else:
                await item.click()

            await asyncio.sleep(3)

            # Find SVG with mindmap content
            svgs = await page.query_selector_all('svg')
            mindmap_svg = None
            max_size = 0

            for svg in svgs:
                try:
                    html = await svg.evaluate("el => el.outerHTML")
                    # Skip icons (Google UI)
                    if 'class="gb_' in html or 'focusable="false"' in html:
                        continue
                    # Look for mindmap markers
                    if ('class="node"' in html or 'class="node-name"' in html) and len(html) > max_size:
                        max_size = len(html)
                        mindmap_svg = html
                except:
                    continue

            if mindmap_svg and max_size > 5000:
                output_path = self.output_dir / "mindmap" / f"mindmap_{datetime.now():%Y%m%d_%H%M%S}.svg"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(mindmap_svg, encoding="utf-8")
                logger.info(f"Mindmap saved: {output_path}")
                return ContentStatus(status="ready", file=str(output_path))

            logger.warning("Could not find mindmap SVG content")
            return ContentStatus(status="error")

        except Exception as e:
            logger.error(f"Mindmap harvest failed: {e}")
            return ContentStatus(status="error")


async def main():
    parser = argparse.ArgumentParser(description="NotebookLM Harvester - Download ready content")
    parser.add_argument("--url", required=True, help="Notebook URL")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--types", default="audio,video,mindmap", help="Content types to harvest")
    parser.add_argument("--cdp-port", type=int, default=9222, help="Chrome CDP port")

    args = parser.parse_args()

    types = [t.strip() for t in args.types.split(",")]
    output_dir = Path(args.output_dir)

    config = NotebookLMConfig(cdp_url=f"http://localhost:{args.cdp_port}")

    async with NotebookLMClient(config) as client:
        harvester = NotebookHarvester(client, output_dir)
        result = await harvester.harvest(args.url, types)

    # Output JSON
    output = {
        "notebook_url": result.notebook_url,
        "audio": asdict(result.audio),
        "video": asdict(result.video),
        "mindmap": asdict(result.mindmap)
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
