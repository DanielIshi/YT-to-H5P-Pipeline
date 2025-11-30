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
from typing import Optional, Dict
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
    """

    # Ready indicator: "X Quelle · Vor X Min."
    READY_INDICATOR = " · Vor "

    # Generating indicators
    GENERATING_INDICATORS = [
        "Kommen Sie in ein paar Minuten wieder",
        "Come back in a few minutes",
        "wird erstellt",
        "Generating"
    ]

    # Buttons in Studio Panel (rechts)
    AUDIO_CARD = 'button:has-text("Audio-Zusammenfassung"), button:has-text("Audio Overview")'
    VIDEO_CARD = 'button:has-text("Video-Zusammenfassung"), button:has-text("Video Overview")'
    MINDMAP_CARD = 'button:has-text("Mindmap"), button:has-text("Mind map")'

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

    async def _check_card_status(self, selector: str, click_to_check: bool = True) -> str:
        """
        Check if a card shows ready or generating status.

        Args:
            selector: Button selector
            click_to_check: If True, click the card and check page content for status
        """
        page = self.client.page

        try:
            card = await page.query_selector(selector)
            if not card:
                return "not_started"

            # First check button text itself
            text = await card.text_content() or ""

            if self.READY_INDICATOR in text:
                return "ready"

            if any(ind in text for ind in self.GENERATING_INDICATORS):
                return "generating"

            # If click_to_check, click and check the panel content
            if click_to_check:
                await card.click()
                await asyncio.sleep(2)

                # Check page body for status indicators
                body = await page.inner_text('body')

                if self.READY_INDICATOR in body:
                    return "ready"

                if any(ind in body for ind in self.GENERATING_INDICATORS):
                    return "generating"

            return "not_started"

        except Exception as e:
            logger.error(f"Card status check failed: {e}")
            return "error"

    async def _close_panel(self):
        """Close any open panel by pressing Escape or clicking outside"""
        page = self.client.page
        try:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
        except:
            pass

    async def _harvest_audio(self) -> ContentStatus:
        """Check and download audio if ready from Studio panel"""
        page = self.client.page

        try:
            # Find ready audio items in artifact-library (Studio panel)
            # Ready items have "Vor X Min." in their text
            items = await page.query_selector_all('artifact-library-item')
            logger.info(f"Found {len(items)} artifact items")

            ready_audio_index = None
            for i, item in enumerate(items):
                text = await item.text_content() or ""
                # Check if it's audio and ready (has "Vor" = finished)
                if "Vor" in text and "Min" in text:
                    logger.info(f"Found ready item {i}: {text[:50]}...")
                    ready_audio_index = i + 1  # CSS nth-child is 1-indexed
                    break

            if ready_audio_index is None:
                # Check if any are still generating
                body = await page.inner_text('body')
                if any(ind in body for ind in self.GENERATING_INDICATORS):
                    return ContentStatus(status="generating")
                return ContentStatus(status="not_started")

            # Click 3-dots menu on the ready item
            three_dots = f'artifact-library-item:nth-child({ready_audio_index}) > div > button > span.mdc-button__label > button'
            await page.click(three_dots, timeout=10000)
            await asyncio.sleep(1)

            # Click Herunterladen
            output_path = self.output_dir / "audio" / f"audio_{datetime.now():%Y%m%d_%H%M%S}.mp3"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            async with page.expect_download() as download_info:
                await page.click('button:has-text("Herunterladen")', timeout=5000)

            download = await download_info.value
            await download.save_as(str(output_path))
            logger.info(f"Audio downloaded: {output_path}")
            return ContentStatus(status="ready", file=str(output_path))

        except Exception as e:
            logger.error(f"Audio harvest failed: {e}")
            return ContentStatus(status="error")

    async def _harvest_video(self) -> ContentStatus:
        """Check and download video if ready"""
        page = self.client.page
        # click_to_check=True will click the card, so panel is already open
        status = await self._check_card_status(self.VIDEO_CARD, click_to_check=True)
        logger.info(f"Video status: {status}")

        if status != "ready":
            return ContentStatus(status=status)

        try:
            # Panel is already open from status check
            await asyncio.sleep(1)

            output_path = self.output_dir / "video" / f"video_{datetime.now():%Y%m%d_%H%M%S}.mp4"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Try download button
            download_btn = await page.query_selector('button[aria-label*="Download"], button[aria-label*="Herunterladen"]')
            if download_btn and await download_btn.is_visible():
                async with page.expect_download() as download_info:
                    await download_btn.click()
                download = await download_info.value
                await download.save_as(str(output_path))
                logger.info(f"Video downloaded: {output_path}")
                return ContentStatus(status="ready", file=str(output_path))

            # Fallback: Get video src
            video_elem = await page.query_selector('video[src]')
            if video_elem:
                src = await video_elem.get_attribute("src")
                if src:
                    response = await page.request.get(src)
                    if response.ok:
                        output_path.write_bytes(await response.body())
                        logger.info(f"Video downloaded: {output_path}")
                        return ContentStatus(status="ready", file=str(output_path))

            return ContentStatus(status="error")

        except Exception as e:
            logger.error(f"Video harvest failed: {e}")
            return ContentStatus(status="error")

    async def _harvest_mindmap(self) -> ContentStatus:
        """Check and extract mindmap if ready"""
        page = self.client.page

        try:
            # Click mindmap card
            mindmap_card = await page.query_selector(self.MINDMAP_CARD)
            if not mindmap_card:
                return ContentStatus(status="not_started")

            await mindmap_card.click()
            await asyncio.sleep(3)

            # Find SVG with mindmap
            svgs = await page.query_selector_all('svg')
            mindmap_svg = None
            max_size = 0

            for svg in svgs:
                try:
                    html = await svg.evaluate("el => el.outerHTML")
                    # Skip icons
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

            return ContentStatus(status="generating")

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
