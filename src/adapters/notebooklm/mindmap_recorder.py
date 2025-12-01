"""
NotebookLM Mindmap Recorder - CLI for recording mindmap animations

Records mindmap navigation synchronized with audio timestamps and outputs
a final video with the NotebookLM audio overlay.

Workflow:
1. Open notebook with mindmap
2. Extract mindmap structure (nodes, hierarchy)
3. Transcribe audio with Whisper (if provided)
4. Create animation timeline (timestamp-synced or sequential)
5. Animate mindmap (expand/collapse nodes)
6. Record screen during animation
7. Merge with audio for final video

Usage:
    # With audio file (timestamp-synced animation):
    python -m src.adapters.notebooklm.mindmap_recorder \
        --notebook-url "https://notebooklm.google.com/notebook/ABC" \
        --audio-path "audio.mp3" \
        --output "animation.mp4"

    # Without audio (sequential animation):
    python -m src.adapters.notebooklm.mindmap_recorder \
        --notebook-url "https://notebooklm.google.com/notebook/ABC" \
        --output "animation.mp4"

    # Live-sync mode (play audio during recording):
    python -m src.adapters.notebooklm.mindmap_recorder \
        --notebook-url "https://notebooklm.google.com/notebook/ABC" \
        --audio-path "audio.mp3" \
        --live-sync \
        --output "animation.mp4"
"""

import asyncio
import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from .client import NotebookLMClient
from .config import NotebookLMConfig
from .mindmap_extractor import MindmapExtractor
from .mindmap_animator import MindmapAnimator, AudioTranscriber, AnimationTimeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def record_mindmap_animation(
    notebook_url: str,
    output_path: Path,
    audio_path: Optional[Path] = None,
    live_sync: bool = False,
    cdp_port: int = 9223,
    pause_per_node: float = 3.0
) -> Optional[Path]:
    """
    Record mindmap animation synchronized with audio.

    Args:
        notebook_url: NotebookLM notebook URL
        output_path: Where to save the final video
        audio_path: Optional NotebookLM audio file for sync
        live_sync: Play audio live during recording (vs post-merge)
        cdp_port: Chrome CDP port for browser automation
        pause_per_node: Seconds to pause on each node (sequential mode)

    Returns:
        Path to final video, or None on failure
    """
    config = NotebookLMConfig(cdp_url=f"http://localhost:{cdp_port}")

    async with NotebookLMClient(config) as client:
        page = client.page

        # 1. Navigate to notebook
        logger.info(f"Opening notebook: {notebook_url}")
        await page.goto(notebook_url)
        await asyncio.sleep(5)  # Wait for page load

        # 2. Extract mindmap structure
        logger.info("Extracting mindmap structure...")
        extractor = MindmapExtractor(client)
        mindmap_data = await extractor.extract_mindmap_from_page()

        if not mindmap_data or not mindmap_data.nodes:
            logger.error("Failed to extract mindmap - no nodes found")
            return None

        logger.info(f"Extracted {len(mindmap_data.nodes)} nodes from mindmap")

        # 3. Create animator
        animator = MindmapAnimator(client, output_dir=output_path.parent)

        # 4. Create timeline
        if audio_path and audio_path.exists():
            logger.info(f"Creating timeline from audio: {audio_path}")
            transcriber = AudioTranscriber(model_name="base")
            audio_segments = transcriber.transcribe(audio_path)
            timeline = animator.create_timeline_from_transcript(
                mindmap_data,
                audio_segments,
                min_match_score=0.3
            )
        else:
            logger.info("Creating sequential timeline (no audio)")
            timeline = animator.create_sequential_timeline(
                mindmap_data,
                pause_per_node=pause_per_node,
                include_collapse=True
            )

        logger.info(f"Timeline: {len(timeline.steps)} steps, {timeline.total_duration:.1f}s")

        # 5. Animate with recording
        logger.info("Starting animation with recording...")
        video_path = await animator.animate(
            mindmap_data,
            timeline,
            record=True,
            output_path=output_path
        )

        if not video_path or not video_path.exists():
            logger.error("Recording failed - no video produced")
            return None

        # 6. Merge with audio (if provided and not live-sync)
        if audio_path and audio_path.exists() and not live_sync:
            logger.info("Merging video with audio...")
            final_path = await animator.merge_audio(video_path, audio_path)
            return final_path
        else:
            return video_path


async def main():
    parser = argparse.ArgumentParser(
        description="NotebookLM Mindmap Recorder - Record animated mindmap navigation"
    )
    parser.add_argument(
        "--notebook-url",
        required=True,
        help="NotebookLM notebook URL"
    )
    parser.add_argument(
        "--audio-path",
        type=Path,
        help="Path to NotebookLM audio file for sync (MP3)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/output/recordings/mindmap_animation.mp4"),
        help="Output video path"
    )
    parser.add_argument(
        "--live-sync",
        action="store_true",
        help="Play audio live during recording (vs post-merge)"
    )
    parser.add_argument(
        "--cdp-port",
        type=int,
        default=9223,
        help="Chrome CDP port (default: 9223)"
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=3.0,
        help="Seconds to pause per node in sequential mode (default: 3.0)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        # Suppress numba JIT debug output
        logging.getLogger('numba').setLevel(logging.WARNING)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    try:
        final_path = await record_mindmap_animation(
            notebook_url=args.notebook_url,
            output_path=args.output,
            audio_path=args.audio_path,
            live_sync=args.live_sync,
            cdp_port=args.cdp_port,
            pause_per_node=args.pause
        )

        if final_path:
            print(f"\n=== SUCCESS ===")
            print(f"Video saved: {final_path}")
            print(json.dumps({
                "status": "success",
                "output": str(final_path)
            }, indent=2))
        else:
            print(f"\n=== FAILED ===")
            print(json.dumps({
                "status": "error",
                "message": "Recording failed"
            }, indent=2))
            exit(1)

    except Exception as e:
        logger.exception(f"Recording failed: {e}")
        print(json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2))
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
