#!/usr/bin/env python3
"""
NotebookLM CLI - Command-line interface for NotebookLM automation

Usage:
    # From YouTube transcript (Supabase)
    python -m src.adapters.notebooklm.cli --youtube-url-id 2454 --output ./output

    # From text file
    python -m src.adapters.notebooklm.cli --text-file transcript.txt --title "KI Grundlagen"

    # From text directly
    python -m src.adapters.notebooklm.cli --text "Your content here..." --title "Quick Note"

    # Generate specific content types
    python -m src.adapters.notebooklm.cli --text-file content.txt --audio --faq --study-guide
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Optional
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.adapters.notebooklm.client import NotebookLMClient
from src.adapters.notebooklm.config import NotebookLMConfig
from src.adapters.notebooklm.notebook_manager import NotebookManager
from src.adapters.notebooklm.content_extractor import ContentExtractor
from src.adapters.notebooklm.audio_downloader import AudioDownloader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_transcript_from_supabase(youtube_url_id: int) -> Optional[dict]:
    """Fetch transcript from Supabase youtube_urls table"""
    try:
        import httpx
        from dotenv import load_dotenv

        load_dotenv()

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{supabase_url}/rest/v1/youtube_urls",
                params={"id": f"eq.{youtube_url_id}", "select": "*"},
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}"
                }
            )

            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]

        logger.error(f"YouTube URL ID {youtube_url_id} not found")
        return None

    except Exception as e:
        logger.error(f"Supabase fetch failed: {e}")
        return None


async def main(args: argparse.Namespace) -> int:
    """Main CLI entry point"""

    # Determine input content
    content = None
    title = args.title or "NotebookLM Learning Module"

    if args.youtube_url_id:
        # Fetch from Supabase
        logger.info(f"Fetching transcript from Supabase (ID: {args.youtube_url_id})")
        data = await get_transcript_from_supabase(args.youtube_url_id)
        if data:
            content = data.get("subtitles") or data.get("transcript")
            title = data.get("title") or title
        else:
            return 1

    elif args.text_file:
        # Read from file
        file_path = Path(args.text_file)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return 1
        content = file_path.read_text(encoding="utf-8")
        title = args.title or file_path.stem

    elif args.text:
        # Direct text input
        content = args.text

    else:
        logger.error("No input specified. Use --youtube-url-id, --text-file, or --text")
        return 1

    if not content:
        logger.error("No content to process")
        return 1

    logger.info(f"Processing: {title} ({len(content)} chars)")

    # Setup output directory
    output_dir = Path(args.output) if args.output else Path("output/notebooklm")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Configure client
    config = NotebookLMConfig(
        headless=args.headless,
        output_dir=output_dir,
        audio_dir=output_dir / "audio"
    )

    # Run automation
    results = {
        "notebook_title": title,
        "status": "started",
        "outputs": {}
    }

    try:
        async with NotebookLMClient(config) as client:
            # Ensure authenticated
            logger.info("Checking authentication...")
            if not await client.ensure_authenticated():
                logger.error("Authentication failed. Please sign in manually.")
                results["status"] = "auth_failed"
                return 1

            # Create notebook and add content
            manager = NotebookManager(client)
            notebook = await manager.create_notebook(title)
            logger.info(f"Created notebook: {notebook.url}")

            # Add content as source
            await manager.add_text_source(notebook, content, title=title)
            logger.info("Content added to notebook")

            # Generate requested content types
            extractor = ContentExtractor(client)
            downloader = AudioDownloader(client)

            # FAQ
            if args.faq or args.all:
                logger.info("Generating FAQ...")
                faq = await extractor.extract_faq(notebook)
                if faq:
                    faq_path = output_dir / f"{title}_faq.md"
                    faq_path.write_text(faq.content, encoding="utf-8")
                    results["outputs"]["faq"] = str(faq_path)
                    logger.info(f"FAQ saved: {faq_path}")

            # Study Guide
            if args.study_guide or args.all:
                logger.info("Generating Study Guide...")
                guide = await extractor.extract_study_guide(notebook)
                if guide:
                    guide_path = output_dir / f"{title}_study_guide.md"
                    guide_path.write_text(guide.content, encoding="utf-8")
                    results["outputs"]["study_guide"] = str(guide_path)
                    logger.info(f"Study Guide saved: {guide_path}")

            # Briefing Doc
            if args.briefing or args.all:
                logger.info("Generating Briefing Doc...")
                briefing = await extractor.extract_briefing_doc(notebook)
                if briefing:
                    briefing_path = output_dir / f"{title}_briefing.md"
                    briefing_path.write_text(briefing.content, encoding="utf-8")
                    results["outputs"]["briefing"] = str(briefing_path)
                    logger.info(f"Briefing saved: {briefing_path}")

            # Timeline
            if args.timeline or args.all:
                logger.info("Generating Timeline...")
                timeline = await extractor.extract_timeline(notebook)
                if timeline:
                    timeline_path = output_dir / f"{title}_timeline.md"
                    timeline_path.write_text(timeline.content, encoding="utf-8")
                    results["outputs"]["timeline"] = str(timeline_path)
                    logger.info(f"Timeline saved: {timeline_path}")

            # Audio Overview (Podcast)
            if args.audio or args.all:
                logger.info("Generating Audio Overview (this may take several minutes)...")
                audio = await downloader.generate_and_download(notebook)
                if audio.file_path:
                    results["outputs"]["audio"] = str(audio.file_path)
                    results["audio_duration"] = audio.duration_seconds
                    logger.info(f"Audio saved: {audio.file_path}")
                else:
                    logger.warning("Audio generation failed")

            # Export all as markdown
            if args.export_markdown:
                data = await extractor.extract_all(notebook)
                md_content = await extractor.export_to_markdown(data)
                md_path = output_dir / f"{title}_complete.md"
                md_path.write_text(md_content, encoding="utf-8")
                results["outputs"]["markdown"] = str(md_path)

            # Cleanup notebook if requested
            if args.cleanup:
                await manager.delete_notebook(notebook)
                logger.info("Notebook deleted")

            results["status"] = "success"
            results["notebook_url"] = notebook.url

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        results["status"] = "failed"
        results["error"] = str(e)
        return 1

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"NotebookLM Processing Complete")
        print(f"{'='*50}")
        print(f"Title: {results['notebook_title']}")
        print(f"Status: {results['status']}")
        if results.get('notebook_url'):
            print(f"Notebook URL: {results['notebook_url']}")
        print(f"\nOutputs:")
        for key, path in results.get('outputs', {}).items():
            print(f"  - {key}: {path}")

    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="NotebookLM Automation CLI - Generate E-Learning content from text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From Supabase YouTube transcript
  python -m src.adapters.notebooklm.cli --youtube-url-id 2454 --all

  # From text file with specific outputs
  python -m src.adapters.notebooklm.cli --text-file transcript.txt --audio --faq

  # Quick test with direct text
  python -m src.adapters.notebooklm.cli --text "AI is transforming education..." --study-guide
        """
    )

    # Input sources
    input_group = parser.add_argument_group("Input Sources (choose one)")
    input_group.add_argument(
        "--youtube-url-id", "-y",
        type=int,
        help="YouTube URL ID from Supabase youtube_urls table"
    )
    input_group.add_argument(
        "--text-file", "-f",
        type=str,
        help="Path to text file with content"
    )
    input_group.add_argument(
        "--text", "-t",
        type=str,
        help="Direct text content to process"
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory (default: output/notebooklm)"
    )
    output_group.add_argument(
        "--title",
        type=str,
        help="Title for the notebook"
    )

    # Content types to generate
    content_group = parser.add_argument_group("Content Types")
    content_group.add_argument(
        "--all", "-a",
        action="store_true",
        help="Generate all content types"
    )
    content_group.add_argument(
        "--audio",
        action="store_true",
        help="Generate Audio Overview (podcast)"
    )
    content_group.add_argument(
        "--faq",
        action="store_true",
        help="Generate FAQ"
    )
    content_group.add_argument(
        "--study-guide",
        action="store_true",
        help="Generate Study Guide"
    )
    content_group.add_argument(
        "--briefing",
        action="store_true",
        help="Generate Briefing Document"
    )
    content_group.add_argument(
        "--timeline",
        action="store_true",
        help="Generate Timeline"
    )
    content_group.add_argument(
        "--export-markdown",
        action="store_true",
        help="Export all content to single Markdown file"
    )

    # Behavior options
    behavior_group = parser.add_argument_group("Behavior Options")
    behavior_group.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (not recommended for first run)"
    )
    behavior_group.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete notebook after extraction"
    )
    behavior_group.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    behavior_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if any content type is requested
    if not any([args.all, args.audio, args.faq, args.study_guide, args.briefing, args.timeline]):
        logger.warning("No content type specified. Use --all or specific types like --audio, --faq")
        args.all = True  # Default to all

    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)
