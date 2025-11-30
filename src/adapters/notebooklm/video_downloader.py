"""
NotebookLM Video Downloader - Generate and download Video Overviews

Video Overviews are AI-generated educational videos with narrated slides.
Launched in 2025 with visual styles like Classic, Whiteboard, Watercolor, etc.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .client import NotebookLMClient
from .notebook_manager import Notebook
from .config import Selectors

logger = logging.getLogger(__name__)


class VideoFormat(Enum):
    """Video format options"""
    EXPLAINER = "explainer"  # Comprehensive, structured (~5-10 min)
    BRIEF = "brief"  # Bite-sized, quick overview (~2-3 min)


class VideoStyle(Enum):
    """Visual style options for video generation"""
    CLASSIC = "classic"
    WHITEBOARD = "whiteboard"
    WATERCOLOR = "watercolor"
    RETRO_PRINT = "retro_print"
    HERITAGE = "heritage"
    PAPERCRAFT = "papercraft"
    KAWAII = "kawaii"
    ANIME = "anime"


@dataclass
class VideoOverview:
    """Container for generated video overview"""
    notebook_id: str
    notebook_title: str
    format: VideoFormat = VideoFormat.EXPLAINER
    style: VideoStyle = VideoStyle.CLASSIC
    file_path: Optional[Path] = None
    duration_seconds: Optional[int] = None
    generated_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, generating, ready, failed


class VideoDownloader:
    """
    Generates and downloads Video Overviews from NotebookLM.

    Video Overviews transform notebook sources into AI-generated
    educational videos with narrated slides and custom visual styles.

    Usage:
        async with NotebookLMClient() as client:
            downloader = VideoDownloader(client)
            video = await downloader.generate_and_download(
                notebook,
                format=VideoFormat.EXPLAINER,
                style=VideoStyle.CLASSIC
            )
    """

    def __init__(self, client: NotebookLMClient):
        self.client = client

    async def generate_and_download(
        self,
        notebook: Notebook,
        format: VideoFormat = VideoFormat.EXPLAINER,
        style: VideoStyle = VideoStyle.CLASSIC,
        output_path: Optional[Path] = None,
        wait_for_completion: bool = True
    ) -> VideoOverview:
        """
        Generate a video overview and download it.

        Args:
            notebook: Target notebook
            format: Video format (Explainer or Brief)
            style: Visual style (Classic, Whiteboard, etc.)
            output_path: Where to save the video file
            wait_for_completion: Whether to wait for generation (~5-10 min)

        Returns:
            VideoOverview with file path and metadata
        """
        logger.info(f"Generating video overview for notebook: {notebook.id}")
        logger.info(f"Format: {format.value}, Style: {style.value}")

        video = VideoOverview(
            notebook_id=notebook.id or "",
            notebook_title=notebook.title,
            format=format,
            style=style
        )

        # Navigate to notebook
        await self._ensure_notebook_open(notebook)

        # Start generation
        generation_started = await self._start_generation(format, style)
        if not generation_started:
            video.status = "failed"
            return video

        video.status = "generating"

        if wait_for_completion:
            # Wait for video to be ready (can take 5-10 minutes!)
            logger.info("Video generation started. This may take 5-10 minutes...")
            is_ready = await self._wait_for_video_ready()

            if not is_ready:
                video.status = "failed"
                return video

            video.status = "ready"

            # Download the video
            output_path = output_path or self._default_output_path(notebook, style)
            downloaded = await self._download_video(output_path)

            if downloaded:
                video.file_path = output_path
                video.duration_seconds = await self._get_duration()
                logger.info(f"Video downloaded to: {output_path}")
            else:
                video.status = "failed"
                logger.error("Video download failed")

        return video

    async def _ensure_notebook_open(self, notebook: Notebook) -> None:
        """Navigate to notebook if not already open"""
        current_url = await self.client.get_current_url()
        if notebook.url and notebook.url not in current_url:
            await self.client.page.goto(notebook.url)
            await self.client.wait_for_loading()

    async def _start_generation(self, format: VideoFormat, style: VideoStyle) -> bool:
        """Start video overview generation"""
        page = self.client.page

        try:
            # Click Video Overview tab in Studio panel
            logger.info("Opening Video Overview tab...")
            await page.click(Selectors.VIDEO_OVERVIEW_TAB, timeout=10000)
            await asyncio.sleep(2)

            # Check if video already exists
            video_player = await page.query_selector(Selectors.VIDEO_PLAYER)
            if video_player:
                logger.info("Video overview already exists")
                return True

            # Select format (Explainer or Brief)
            await self._select_format(format)

            # Select visual style
            await self._select_style(style)

            # Click Generate button
            generate_btn = await page.query_selector(Selectors.GENERATE_VIDEO_BUTTON)
            if generate_btn:
                await generate_btn.click()
                logger.info("Video generation started")
                return True

            # Try alternative button text
            alt_buttons = [
                'button:has-text("Generate video")',
                'button:has-text("Create video")',
                'button:has-text("Generate")',
            ]

            for selector in alt_buttons:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    logger.info("Video generation started (alt button)")
                    return True

            logger.error("Could not find generate button")
            return False

        except Exception as e:
            logger.error(f"Failed to start generation: {e}")
            return False

    async def _select_format(self, format: VideoFormat) -> None:
        """Select video format (Explainer or Brief)"""
        page = self.client.page

        try:
            if format == VideoFormat.EXPLAINER:
                selector = Selectors.VIDEO_FORMAT_EXPLAINER
            else:
                selector = Selectors.VIDEO_FORMAT_BRIEF

            btn = await page.query_selector(selector)
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(0.5)
                logger.info(f"Selected format: {format.value}")

        except Exception as e:
            logger.debug(f"Format selection: {e}")

    async def _select_style(self, style: VideoStyle) -> None:
        """Select visual style"""
        page = self.client.page

        style_selectors = {
            VideoStyle.CLASSIC: Selectors.VIDEO_STYLE_CLASSIC,
            VideoStyle.WHITEBOARD: Selectors.VIDEO_STYLE_WHITEBOARD,
            VideoStyle.WATERCOLOR: Selectors.VIDEO_STYLE_WATERCOLOR,
        }

        try:
            # Try specific style button
            selector = style_selectors.get(style)
            if selector:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.5)
                    logger.info(f"Selected style: {style.value}")
                    return

            # Fallback: Try generic style selector
            style_selector = await page.query_selector(Selectors.VIDEO_STYLE_SELECTOR)
            if style_selector:
                await style_selector.click()
                await asyncio.sleep(0.5)

                # Click style option by text
                style_option = await page.query_selector(f'button:has-text("{style.value.title()}")')
                if style_option:
                    await style_option.click()
                    logger.info(f"Selected style: {style.value}")

        except Exception as e:
            logger.debug(f"Style selection: {e}")

    async def _wait_for_video_ready(self) -> bool:
        """Wait for video generation to complete"""
        page = self.client.page
        timeout = self.client.config.video_generation_timeout
        poll_interval = 10000  # 10 seconds

        logger.info(f"Waiting for video generation (timeout: {timeout/1000/60:.1f} min)...")

        elapsed = 0
        while elapsed < timeout:
            try:
                # Check for video player
                video_player = await page.query_selector(Selectors.VIDEO_PLAYER)
                if video_player:
                    src = await video_player.get_attribute("src")
                    if src:
                        logger.info("Video is ready")
                        return True

                # Check for download button
                download_btn = await page.query_selector(Selectors.DOWNLOAD_VIDEO_BUTTON)
                if download_btn and await download_btn.is_visible():
                    logger.info("Video is ready (download button visible)")
                    return True

                # Check for error
                error = await self.client.check_for_error()
                if error:
                    logger.error(f"Video generation error: {error}")
                    return False

                # Log progress
                progress = await page.query_selector('[class*="progress"], [role="progressbar"]')
                if progress:
                    progress_text = await progress.text_content()
                    if progress_text:
                        logger.info(f"Generation progress: {progress_text}")

            except Exception as e:
                logger.debug(f"Wait check: {e}")

            await asyncio.sleep(poll_interval / 1000)
            elapsed += poll_interval

            # Progress log every minute
            if elapsed % 60000 == 0:
                logger.info(f"Still generating... ({elapsed/60000:.0f} min elapsed)")

        logger.error("Video generation timed out")
        return False

    async def _download_video(self, output_path: Path) -> bool:
        """Download the generated video file"""
        page = self.client.page

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Method 1: Use download button
            download_btn = await page.query_selector(Selectors.DOWNLOAD_VIDEO_BUTTON)
            if download_btn:
                async with page.expect_download() as download_info:
                    await download_btn.click()

                download = await download_info.value
                await download.save_as(str(output_path))
                return True

            # Method 2: Get video source URL
            video_player = await page.query_selector(Selectors.VIDEO_PLAYER)
            if video_player:
                src = await video_player.get_attribute("src")
                if src:
                    response = await page.request.get(src)
                    if response.ok:
                        content = await response.body()
                        output_path.write_bytes(content)
                        return True

            # Method 3: Try any download link
            download_links = await page.query_selector_all(
                'a[download], a[href*=".mp4"], a[href*="video"]'
            )
            for link in download_links:
                href = await link.get_attribute("href")
                if href:
                    async with page.expect_download() as download_info:
                        await link.click()
                    download = await download_info.value
                    await download.save_as(str(output_path))
                    return True

            logger.error("Could not find download method")
            return False

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    async def _get_duration(self) -> Optional[int]:
        """Get video duration in seconds"""
        page = self.client.page

        try:
            video_player = await page.query_selector(Selectors.VIDEO_PLAYER)
            if video_player:
                duration = await page.evaluate(
                    "(video) => video.duration",
                    video_player
                )
                if duration and str(duration) != "NaN":
                    return int(duration)
        except Exception:
            pass

        return None

    def _default_output_path(self, notebook: Notebook, style: VideoStyle) -> Path:
        """Generate default output path for video file"""
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in notebook.title)
        safe_title = safe_title[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{style.value}_{timestamp}.mp4"
        return self.client.config.video_dir / filename

    async def check_video_exists(self, notebook: Notebook) -> bool:
        """Check if video overview already exists"""
        await self._ensure_notebook_open(notebook)

        page = self.client.page

        try:
            await page.click(Selectors.VIDEO_OVERVIEW_TAB, timeout=5000)
            await asyncio.sleep(1)

            video_player = await page.query_selector(Selectors.VIDEO_PLAYER)
            if video_player:
                src = await video_player.get_attribute("src")
                return bool(src)

            download_btn = await page.query_selector(Selectors.DOWNLOAD_VIDEO_BUTTON)
            return download_btn is not None and await download_btn.is_visible()

        except Exception:
            return False

    async def delete_video(self, notebook: Notebook) -> bool:
        """Delete existing video (to regenerate with different settings)"""
        await self._ensure_notebook_open(notebook)

        page = self.client.page

        try:
            await page.click(Selectors.VIDEO_OVERVIEW_TAB, timeout=5000)

            delete_selectors = [
                'button[aria-label*="Delete"]',
                'button:has-text("Delete")',
                'button:has-text("Remove")',
            ]

            for selector in delete_selectors:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    try:
                        await page.click('button:has-text("Delete")', timeout=3000)
                    except Exception:
                        pass
                    logger.info("Video deleted")
                    return True

            return False

        except Exception as e:
            logger.error(f"Delete video failed: {e}")
            return False
