"""
E2E Test for NotebookLM Video Overview (Lernvideo) Generation

Prerequisites:
- Chrome running with: chrome.exe --remote-debugging-port=9222
- Logged into NotebookLM (https://notebooklm.google.com)

Run with: pytest tests/e2e/test_notebooklm_video.py -v -s

Note: Video generation takes 5-10 minutes!
"""

import asyncio
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.adapters.notebooklm.client import NotebookLMClient
from src.adapters.notebooklm.config import NotebookLMConfig
from src.adapters.notebooklm.notebook_manager import NotebookManager
from src.adapters.notebooklm.video_downloader import VideoDownloader, VideoFormat, VideoStyle


# Test content - Corporate LLMs summary
CORPORATE_LLMS_CONTENT = """
# Corporate LLMs - Private KI für Unternehmen

Corporate LLMs (Large Language Models) ermöglichen Unternehmen, KI-Technologie
ohne Datenweitergabe an externe Anbieter zu nutzen.

## Kernvorteile:

1. **Datenschutz**: Alle Daten bleiben im Unternehmen
2. **Compliance**: DSGVO-konforme Verarbeitung
3. **Anpassbarkeit**: Fine-Tuning auf firmenspezifische Daten
4. **Sicherheit**: Keine Abhängigkeit von Cloud-Anbietern

## Anwendungsfälle:

- Interne Dokumentenanalyse
- Kundenservice-Automatisierung
- Code-Assistenz für Entwickler
- Wissensmanagement

## Implementierungsoptionen:

- Self-hosted (On-Premise)
- Private Cloud
- Hybrid-Lösungen

Corporate LLMs sind die Zukunft der sicheren KI-Nutzung in Unternehmen.
"""


@pytest.fixture
def output_dir(tmp_path):
    """Create output directory for test artifacts"""
    output = tmp_path / "notebooklm_video_test"
    output.mkdir(parents=True, exist_ok=True)
    return output


@pytest.fixture
def config(output_dir):
    """Create NotebookLM config with CDP connection"""
    return NotebookLMConfig(
        cdp_url="http://localhost:9223",
        headless=False,
        output_dir=output_dir,
        video_dir=output_dir / "video",
        video_generation_timeout=900000  # 15 minutes for video generation
    )


class TestNotebookLMVideo:
    """E2E tests for NotebookLM Video Overview generation"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(1200)  # 20 min total timeout for video
    async def test_generate_video_overview_classic(self, config, output_dir):
        """
        Test full video generation workflow with Classic style:
        1. Create notebook
        2. Add Corporate LLMs content
        3. Generate video overview (Classic style, Explainer format)
        4. Download video file
        5. Verify file exists and has content
        """
        notebook = None

        async with NotebookLMClient(config) as client:
            # Check authentication
            authenticated = await client.ensure_authenticated()
            assert authenticated, "Authentication failed - please log in to NotebookLM first"

            # Create notebook
            manager = NotebookManager(client)
            notebook = await manager.create_notebook("Corporate LLMs Video Test")
            assert notebook.id is not None, "Notebook creation failed"
            print(f"\n✅ Notebook created: {notebook.url}")

            # Add content
            await manager.add_text_source(notebook, CORPORATE_LLMS_CONTENT, title="Corporate LLMs")
            print("✅ Content added to notebook")

            # Wait for content processing
            await asyncio.sleep(3)

            # Generate video
            video_downloader = VideoDownloader(client)
            print("⏳ Generating video overview (this may take 5-10 minutes)...")

            video = await video_downloader.generate_and_download(
                notebook,
                format=VideoFormat.EXPLAINER,
                style=VideoStyle.CLASSIC,
                output_path=output_dir / "video" / "corporate_llms_classic.mp4"
            )

            # Assertions
            assert video.status == "ready", f"Video generation failed: {video.status}"
            assert video.file_path is not None, "No video file path returned"
            assert video.file_path.exists(), f"Video file not found: {video.file_path}"
            assert video.file_path.stat().st_size > 0, "Video file is empty"

            print(f"\n✅ Video generated successfully!")
            print(f"   File: {video.file_path}")
            print(f"   Size: {video.file_path.stat().st_size / 1024 / 1024:.1f} MB")
            print(f"   Style: {video.style.value}")
            print(f"   Format: {video.format.value}")
            if video.duration_seconds:
                print(f"   Duration: {video.duration_seconds}s")

            # Cleanup - delete notebook
            await manager.delete_notebook(notebook)
            print("✅ Notebook cleaned up")

    @pytest.mark.asyncio
    @pytest.mark.timeout(1200)
    async def test_generate_video_brief_whiteboard(self, config, output_dir):
        """
        Test video generation with Brief format and Whiteboard style.
        Brief videos are shorter (~2-3 min instead of ~5-10 min).
        """
        async with NotebookLMClient(config) as client:
            authenticated = await client.ensure_authenticated()
            assert authenticated, "Authentication failed"

            manager = NotebookManager(client)
            notebook = await manager.create_notebook("Corporate LLMs Brief Video")

            try:
                await manager.add_text_source(notebook, CORPORATE_LLMS_CONTENT, title="Corporate LLMs")
                await asyncio.sleep(3)

                video_downloader = VideoDownloader(client)
                print("⏳ Generating brief whiteboard video...")

                video = await video_downloader.generate_and_download(
                    notebook,
                    format=VideoFormat.BRIEF,
                    style=VideoStyle.WHITEBOARD,
                    output_path=output_dir / "video" / "corporate_llms_brief_whiteboard.mp4"
                )

                assert video.status == "ready"
                assert video.file_path and video.file_path.exists()
                print(f"\n✅ Brief video saved: {video.file_path}")

            finally:
                await manager.delete_notebook(notebook)

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_check_existing_video(self, config):
        """Test checking if video already exists for a notebook"""
        async with NotebookLMClient(config) as client:
            authenticated = await client.ensure_authenticated()
            if not authenticated:
                pytest.skip("Not authenticated")

            manager = NotebookManager(client)
            notebook = await manager.create_notebook("Video Check Test")

            try:
                video_downloader = VideoDownloader(client)

                # Initially, no video should exist
                exists = await video_downloader.check_video_exists(notebook)
                assert not exists, "Video should not exist for new notebook"
                print("✅ Correctly detected no existing video")

            finally:
                await manager.delete_notebook(notebook)


class TestNotebookLMVideoFromFile:
    """E2E tests using existing Corporate LLMs content file"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(1200)
    async def test_video_from_mindmap_file(self, config):
        """
        Test video generation from existing Corporate LLMs mindmap file.
        Uses the pre-generated mindmap as input content.
        """
        mindmap_file = Path(__file__).parent.parent / "output" / "notebooklm" / "mindmap" / "Corporate LLMs - Private KI_mindmap.md"

        if not mindmap_file.exists():
            pytest.skip(f"Mindmap file not found: {mindmap_file}")

        content = mindmap_file.read_text(encoding="utf-8")
        output_dir = mindmap_file.parent.parent / "video"
        output_dir.mkdir(parents=True, exist_ok=True)

        async with NotebookLMClient(config) as client:
            authenticated = await client.ensure_authenticated()
            assert authenticated, "Authentication failed"

            manager = NotebookManager(client)
            notebook = await manager.create_notebook("Corporate LLMs - Video from Mindmap")

            try:
                await manager.add_text_source(notebook, content, title="Corporate LLMs Mindmap")
                await asyncio.sleep(3)

                video_downloader = VideoDownloader(client)
                video = await video_downloader.generate_and_download(
                    notebook,
                    format=VideoFormat.EXPLAINER,
                    style=VideoStyle.CLASSIC,
                    output_path=output_dir / "corporate_llms_from_mindmap.mp4"
                )

                assert video.status == "ready"
                assert video.file_path and video.file_path.exists()
                print(f"\n✅ Video saved to: {video.file_path}")

            finally:
                await manager.delete_notebook(notebook)


class TestVideoStyles:
    """Test different video style options"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("style", [
        VideoStyle.CLASSIC,
        VideoStyle.WHITEBOARD,
        VideoStyle.WATERCOLOR,
    ])
    @pytest.mark.timeout(1200)
    async def test_video_style(self, config, output_dir, style):
        """Test video generation with different visual styles"""
        async with NotebookLMClient(config) as client:
            authenticated = await client.ensure_authenticated()
            if not authenticated:
                pytest.skip("Not authenticated")

            manager = NotebookManager(client)
            notebook = await manager.create_notebook(f"Style Test - {style.value}")

            try:
                await manager.add_text_source(
                    notebook,
                    "KI verändert die Arbeitswelt. Automatisierung steigert Effizienz.",
                    title="KI Test"
                )
                await asyncio.sleep(3)

                video_downloader = VideoDownloader(client)
                video = await video_downloader.generate_and_download(
                    notebook,
                    format=VideoFormat.BRIEF,  # Brief for faster test
                    style=style,
                    output_path=output_dir / "video" / f"style_test_{style.value}.mp4"
                )

                assert video.status == "ready", f"Style {style.value} failed"
                print(f"✅ Style {style.value}: OK")

            finally:
                await manager.delete_notebook(notebook)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
