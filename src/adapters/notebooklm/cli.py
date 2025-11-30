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
from src.adapters.notebooklm.video_downloader import VideoDownloader, VideoFormat, VideoStyle
from src.adapters.notebooklm.mindmap_extractor import MindmapExtractor
from src.adapters.notebooklm.mindmap_animator import MindmapAnimator, AudioTranscriber

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
        cdp_url=args.cdp_url if hasattr(args, 'cdp_url') else None,
        headless=args.headless,
        output_dir=output_dir,
        audio_dir=output_dir / "audio",
        video_dir=output_dir / "video",
        mindmap_dir=output_dir / "mindmap"
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
            audio_downloader = AudioDownloader(client)
            video_downloader = VideoDownloader(client)
            mindmap_extractor = MindmapExtractor(client)

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
                audio = await audio_downloader.generate_and_download(notebook)
                if audio.file_path:
                    results["outputs"]["audio"] = str(audio.file_path)
                    results["audio_duration"] = audio.duration_seconds
                    logger.info(f"Audio saved: {audio.file_path}")
                else:
                    logger.warning("Audio generation failed")

            # Video Overview (AI-generated educational video)
            if args.video or args.all:
                logger.info("Generating Video Overview (this may take 5-10 minutes)...")
                # Determine video style
                video_style = VideoStyle.CLASSIC
                if args.video_style:
                    try:
                        video_style = VideoStyle(args.video_style.lower())
                    except ValueError:
                        logger.warning(f"Unknown video style: {args.video_style}, using Classic")

                # Determine video format
                video_format = VideoFormat.EXPLAINER
                if args.video_format:
                    try:
                        video_format = VideoFormat(args.video_format.lower())
                    except ValueError:
                        pass

                video = await video_downloader.generate_and_download(
                    notebook,
                    format=video_format,
                    style=video_style
                )
                if video.file_path:
                    results["outputs"]["video"] = str(video.file_path)
                    results["video_duration"] = video.duration_seconds
                    logger.info(f"Video saved: {video.file_path}")
                else:
                    logger.warning("Video generation failed")

            # Mindmap (SVG + JSON)
            mindmap = None
            if args.mindmap or args.animate or args.all:
                logger.info("Extracting Mindmap...")
                mindmap = await mindmap_extractor.extract_mindmap(notebook)
                if mindmap.svg_content:
                    paths = await mindmap_extractor.save_mindmap(mindmap, output_dir / "mindmap")
                    results["outputs"]["mindmap_svg"] = str(paths.get("svg", ""))
                    results["outputs"]["mindmap_json"] = str(paths.get("json", ""))
                    results["mindmap_nodes"] = len(mindmap.nodes)
                    logger.info(f"Mindmap saved: {len(mindmap.nodes)} nodes")

                    # Also save as markdown
                    md_content = mindmap_extractor.export_to_markdown(mindmap)
                    md_path = output_dir / "mindmap" / f"{title}_mindmap.md"
                    md_path.write_text(md_content, encoding="utf-8")
                    results["outputs"]["mindmap_md"] = str(md_path)
                else:
                    logger.warning("Mindmap extraction failed")

            # Mindmap Animation
            if args.animate and mindmap and mindmap.nodes:
                logger.info("Creating mindmap animation...")
                animator = MindmapAnimator(client)

                # Create timeline
                if args.sync_audio and results.get("outputs", {}).get("audio"):
                    # Sync with audio transcript
                    logger.info("Transcribing audio for sync...")
                    try:
                        transcriber = AudioTranscriber(model_name=args.whisper_model or "base")
                        audio_path = Path(results["outputs"]["audio"])
                        segments = transcriber.transcribe(audio_path)
                        timeline = animator.create_timeline_from_transcript(mindmap, segments)
                        results["animation_sync"] = "audio"
                    except Exception as e:
                        logger.warning(f"Audio sync failed: {e}, using sequential")
                        timeline = animator.create_sequential_timeline(
                            mindmap,
                            pause_per_node=args.node_pause or 3.0
                        )
                        results["animation_sync"] = "sequential"
                else:
                    # Sequential animation
                    timeline = animator.create_sequential_timeline(
                        mindmap,
                        pause_per_node=args.node_pause or 3.0
                    )
                    results["animation_sync"] = "sequential"

                # Execute animation
                video_path = await animator.animate(
                    mindmap,
                    timeline,
                    record=args.record_video
                )

                if video_path:
                    results["outputs"]["animation_video"] = str(video_path)
                    results["animation_steps"] = len(timeline.steps)
                    logger.info(f"Animation complete: {timeline.total_duration}s, {len(timeline.steps)} steps")

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
    content_group.add_argument(
        "--video",
        action="store_true",
        help="Generate Video Overview (AI-generated educational video, ~5-10 min)"
    )
    content_group.add_argument(
        "--mindmap",
        action="store_true",
        help="Extract Mindmap (SVG + JSON structure)"
    )
    content_group.add_argument(
        "--animate",
        action="store_true",
        help="Animate mindmap exploration (requires --mindmap)"
    )
    content_group.add_argument(
        "--record-video",
        action="store_true",
        help="Record animation as video (requires --animate)"
    )
    content_group.add_argument(
        "--sync-audio",
        action="store_true",
        help="Sync animation with audio transcript (requires --animate and --audio)"
    )

    # Video options
    video_group = parser.add_argument_group("Video Options")
    video_group.add_argument(
        "--video-style",
        type=str,
        choices=["classic", "whiteboard", "watercolor", "retro_print", "heritage", "papercraft", "kawaii", "anime"],
        default="classic",
        help="Visual style for video generation (default: classic)"
    )
    video_group.add_argument(
        "--video-format",
        type=str,
        choices=["explainer", "brief"],
        default="explainer",
        help="Video format: explainer (~5-10 min) or brief (~2-3 min)"
    )

    # Animation options
    animation_group = parser.add_argument_group("Animation Options")
    animation_group.add_argument(
        "--node-pause",
        type=float,
        default=3.0,
        help="Seconds to pause on each node during animation (default: 3.0)"
    )
    animation_group.add_argument(
        "--whisper-model",
        type=str,
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Whisper model size for audio transcription (default: base)"
    )

    # Behavior options
    behavior_group = parser.add_argument_group("Behavior Options")
    behavior_group.add_argument(
        "--cdp-url",
        type=str,
        default="http://localhost:9222",
        help="CDP URL for connecting to existing Chrome (default: http://localhost:9222)"
    )
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
    if not any([args.all, args.audio, args.faq, args.study_guide, args.briefing, args.timeline, args.video, args.mindmap]):
        logger.warning("No content type specified. Use --all or specific types like --audio, --faq, --video, --mindmap")
        args.all = True  # Default to all

    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)
