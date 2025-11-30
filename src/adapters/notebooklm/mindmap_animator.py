"""
NotebookLM Mindmap Animator - Animate mindmap exploration synchronized with audio

This module provides functionality to:
1. Navigate through mindmap nodes based on audio content
2. Expand/collapse nodes to create a storytelling flow
3. Record the animation as video
4. Sync with audio timeline
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from playwright.async_api import Page

from .client import NotebookLMClient
from .mindmap_extractor import MindmapData, MindmapNode
from .config import Selectors
from .browser_manager import BrowserManager
from .recorder import Recorder

logger = logging.getLogger(__name__)


class AnimationState(Enum):
    """State of animation playback"""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


@dataclass
class AudioSegment:
    """A segment of audio with timing and content info"""
    start_time: float  # seconds
    end_time: float  # seconds
    text: str  # transcript text for this segment
    keywords: List[str] = field(default_factory=list)  # extracted keywords
    matched_node_id: Optional[str] = None  # matched mindmap node


@dataclass
class AnimationStep:
    """A single step in the animation sequence"""
    timestamp: float  # when to execute (seconds)
    action: str  # "expand", "collapse", "highlight", "focus"
    node_id: str
    node_text: str
    duration: float = 3.0  # how long to show this state


@dataclass
class AnimationTimeline:
    """Complete animation timeline"""
    steps: List[AnimationStep] = field(default_factory=list)
    total_duration: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


class MindmapAnimator:
    """
    Animates mindmap exploration based on audio timeline.

    The animation follows this flow:
    1. Start with all nodes collapsed (only root visible)
    2. As audio progresses, expand relevant nodes
    3. Collapse previous nodes to keep focus
    4. At the end, show full expanded view

    Usage:
        async with NotebookLMClient() as client:
            animator = MindmapAnimator(client)

            # Option 1: Automatic sync with audio transcript
            timeline = animator.create_timeline_from_transcript(
                mindmap_data,
                audio_segments
            )

            # Option 2: Manual timeline
            timeline = animator.create_sequential_timeline(mindmap_data)

            # Execute animation (with optional recording)
            video_path = await animator.animate(
                mindmap_data,
                timeline,
                record=True
            )
    """

    def __init__(self, client: NotebookLMClient):
        self.client = client
        self.state = AnimationState.IDLE
        self._expanded_nodes: List[str] = []  # Currently expanded node IDs
        self.page: Optional[Page] = None

    async def animate(
        self,
        mindmap_data: MindmapData,
        timeline: AnimationTimeline,
        record: bool = False,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Execute animation based on timeline.

        Args:
            mindmap_data: Mindmap structure
            timeline: Animation steps with timing
            record: Whether to record video
            output_path: Where to save recording

        Returns:
            Path to recorded video if record=True
        """
        logger.info(f"Starting animation with {len(timeline.steps)} steps")
        self.state = AnimationState.PLAYING

        self.page = await BrowserManager.new_page()
        video_path = None
        recorder = None

        try:
            # Start recording if requested
            if record:
                video_path = output_path or self._default_video_path(mindmap_data)
                recorder = Recorder(output_dir=str(video_path.parent))
                recorder.start()

            # Go to the mindmap url - client should have it
            await self.page.goto(self.client.get_current_url())

            # Collapse all nodes first
            await self._collapse_all_nodes()
            await asyncio.sleep(1)
            if recorder:
                recorder.capture_frame("Initial state: all collapsed")

            # Execute each animation step
            current_time = 0.0
            for step in timeline.steps:
                # Wait until step timestamp
                wait_time = step.timestamp - current_time
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

                # Execute the action
                await self._execute_step(step)
                current_time = step.timestamp + step.duration
                
                if recorder:
                    recorder.capture_frame(f"{step.action} {step.node_text}")

                # Brief pause for visual effect
                await asyncio.sleep(step.duration)

            # Final view: expand all
            await self._expand_all_nodes()
            await asyncio.sleep(2)
            if recorder:
                recorder.capture_frame("Final state: all expanded")


            self.state = AnimationState.FINISHED

        except Exception as e:
            logger.error(f"Animation failed: {e}")
            self.state = AnimationState.IDLE
            raise

        finally:
            # Stop recording
            if recorder:
                recorder.stop()
                recorder.create_video(video_filename=video_path.name)
            
            await BrowserManager.close_browser()


        logger.info(f"Animation complete. Video: {video_path}")
        return video_path

    async def _execute_step(self, step: AnimationStep) -> None:
        """Execute a single animation step"""
        logger.debug(f"Step: {step.action} on '{step.node_text}'")

        if step.action == "expand":
            await self._expand_node(step.node_id, step.node_text)
        elif step.action == "collapse":
            await self._collapse_node(step.node_id, step.node_text)
        elif step.action == "highlight":
            await self._highlight_node(step.node_id, step.node_text)
        elif step.action == "focus":
            await self._focus_node(step.node_id, step.node_text)

    async def _expand_node(self, node_id: str, node_text: str) -> None:
        """Expand a specific node by clicking it"""
        if not self.page:
            return

        try:
            # Find node by text content
            # NotebookLM nodes have class="node" and contain text in class="node-name"
            node_selector = f'g.node:has(text.node-name:text("{node_text[:30]}"))'

            # Try to click the expand circle/button
            expand_btn = await self.page.query_selector(
                f'{node_selector} circle, {node_selector} text.expand-symbol'
            )

            if expand_btn:
                await expand_btn.click()
                self._expanded_nodes.append(node_id)
                logger.debug(f"Expanded: {node_text}")
                await asyncio.sleep(0.5)  # Animation time
            else:
                # Fallback: click the node rect
                node_rect = await self.page.query_selector(f'{node_selector} rect')
                if node_rect:
                    await node_rect.click()
                    self._expanded_nodes.append(node_id)

        except Exception as e:
            logger.warning(f"Could not expand node '{node_text}': {e}")

    async def _collapse_node(self, node_id: str, node_text: str) -> None:
        """Collapse a specific node"""
        if not self.page:
            return

        try:
            # Find already-expanded node (expand-symbol shows "<")
            node_selector = f'g.node:has(text.node-name:text("{node_text[:30]}"))'
            expand_symbol = await self.page.query_selector(f'{node_selector} text.expand-symbol')

            if expand_symbol:
                symbol_text = await expand_symbol.text_content()
                if symbol_text and "<" in symbol_text:  # Node is expanded
                    circle = await self.page.query_selector(f'{node_selector} circle')
                    if circle:
                        await circle.click()
                        if node_id in self._expanded_nodes:
                            self._expanded_nodes.remove(node_id)
                        logger.debug(f"Collapsed: {node_text}")
                        await asyncio.sleep(0.5)

        except Exception as e:
            logger.warning(f"Could not collapse node '{node_text}': {e}")

    async def _highlight_node(self, node_id: str, node_text: str) -> None:
        """Highlight a node (visual emphasis without expand/collapse)"""
        # Could inject CSS or use JavaScript to highlight
        # For now, just focus on the node
        await self._focus_node(node_id, node_text)

    async def _focus_node(self, node_id: str, node_text: str) -> None:
        """Scroll/pan to center a node in view"""
        if not self.page:
            return

        try:
            node_selector = f'g.node:has(text.node-name:text("{node_text[:30]}"))'
            node = await self.page.query_selector(node_selector)

            if node:
                await node.scroll_into_view_if_needed()

        except Exception as e:
            logger.debug(f"Could not focus node: {e}")

    async def _collapse_all_nodes(self) -> None:
        """Collapse all expanded nodes"""
        if not self.page:
            return
        logger.info("Collapsing all nodes...")

        try:
            # Click "Collapse all" button if available
            collapse_btn = await self.page.query_selector(Selectors.MINDMAP_COLLAPSE_ALL)
            if collapse_btn and await collapse_btn.is_visible():
                await collapse_btn.click()
                await asyncio.sleep(1)
                self._expanded_nodes.clear()
                return

            # Fallback: click all expanded nodes (those showing "<")
            max_iterations = 20
            for _ in range(max_iterations):
                expanded_symbols = await self.page.query_selector_all('text.expand-symbol')

                clicked = False
                for symbol in expanded_symbols:
                    text = await symbol.text_content()
                    if text and "<" in text:  # Expanded node
                        # Find parent circle and click
                        parent_g = await symbol.evaluate_handle("el => el.closest('g.node')")
                        if parent_g:
                            circle = await parent_g.query_selector('circle')
                            if circle:
                                await circle.click()
                                clicked = True
                                await asyncio.sleep(0.3)
                                break

                if not clicked:
                    break

            self._expanded_nodes.clear()

        except Exception as e:
            logger.warning(f"Collapse all failed: {e}")

    async def _expand_all_nodes(self) -> None:
        """Expand all nodes for final overview"""
        if not self.page:
            return
        logger.info("Expanding all nodes...")

        try:
            # Click "Expand all" button if available
            expand_btn = await self.page.query_selector(Selectors.MINDMAP_EXPAND_ALL)
            if expand_btn and await expand_btn.is_visible():
                await expand_btn.click()
                await asyncio.sleep(2)
                return

            # Fallback: click all collapsed nodes (those showing ">")
            max_iterations = 20
            for _ in range(max_iterations):
                collapsed_symbols = await self.page.query_selector_all('text.expand-symbol')

                clicked = False
                for symbol in collapsed_symbols:
                    text = await symbol.text_content()
                    if text and ">" in text:  # Collapsed node with children
                        parent_g = await symbol.evaluate_handle("el => el.closest('g.node')")
                        if parent_g:
                            circle = await parent_g.query_selector('circle')
                            if circle:
                                await circle.click()
                                clicked = True
                                await asyncio.sleep(0.3)
                                break

                if not clicked:
                    break

        except Exception as e:
            logger.warning(f"Expand all failed: {e}")

    def create_sequential_timeline(
        self,
        mindmap_data: MindmapData,
        pause_per_node: float = 3.0,
        include_collapse: bool = True
    ) -> AnimationTimeline:
        """
        Create a simple sequential timeline that visits each node.

        Args:
            mindmap_data: Mindmap structure
            pause_per_node: Seconds to pause on each node
            include_collapse: Whether to collapse previous nodes

        Returns:
            AnimationTimeline with sequential expansion
        """
        timeline = AnimationTimeline()
        current_time = 0.0

        if not mindmap_data.root_node:
            return timeline

        # BFS traversal to create natural reading order
        queue = [(mindmap_data.root_node, None)]  # (node, parent)
        visited = set()

        while queue:
            node, parent = queue.pop(0)

            if node.id in visited:
                continue
            visited.add(node.id)

            # Collapse previous sibling nodes (optional)
            if include_collapse and parent and len(self._expanded_nodes) > 2:
                # Collapse nodes that are not ancestors of current
                for expanded_id in self._expanded_nodes[:-1]:
                    # Simple heuristic: collapse if not parent
                    pass  # TODO: implement smart collapse

            # Add expand step for this node
            step = AnimationStep(
                timestamp=current_time,
                action="expand",
                node_id=node.id,
                node_text=node.text,
                duration=pause_per_node
            )
            timeline.steps.append(step)
            current_time += pause_per_node

            # Add children to queue
            for child in node.children:
                queue.append((child, node))

        timeline.total_duration = current_time
        logger.info(f"Created sequential timeline: {len(timeline.steps)} steps, {current_time}s total")

        return timeline

    def create_timeline_from_transcript(
        self,
        mindmap_data: MindmapData,
        audio_segments: List[AudioSegment],
        min_match_score: float = 0.3
    ) -> AnimationTimeline:
        """
        Create timeline by matching audio transcript to mindmap nodes.

        Args:
            mindmap_data: Mindmap structure
            audio_segments: Transcript segments with timestamps
            min_match_score: Minimum keyword match score (0-1)

        Returns:
            AnimationTimeline synced with audio
        """
        timeline = AnimationTimeline()

        if not mindmap_data.nodes or not audio_segments:
            return timeline

        # Build keyword index for nodes
        node_keywords = self._extract_node_keywords(mindmap_data.nodes)

        # Match each segment to best node
        current_node_id = None

        for segment in audio_segments:
            # Extract keywords from segment text
            segment_keywords = self._extract_keywords(segment.text)

            # Find best matching node
            best_node = None
            best_score = 0.0

            for node in mindmap_data.nodes:
                score = self._calculate_match_score(
                    segment_keywords,
                    node_keywords.get(node.id, [])
                )

                if score > best_score and score >= min_match_score:
                    best_score = score
                    best_node = node

            # Add step if we found a match and it's different from current
            if best_node and best_node.id != current_node_id:
                # Collapse previous if different
                if current_node_id:
                    timeline.steps.append(AnimationStep(
                        timestamp=segment.start_time - 0.5,
                        action="collapse",
                        node_id=current_node_id,
                        node_text="",  # Will be filled
                        duration=0.5
                    ))

                # Expand new node
                timeline.steps.append(AnimationStep(
                    timestamp=segment.start_time,
                    action="expand",
                    node_id=best_node.id,
                    node_text=best_node.text,
                    duration=segment.end_time - segment.start_time
                ))

                current_node_id = best_node.id
                segment.matched_node_id = best_node.id

        if audio_segments:
            timeline.total_duration = audio_segments[-1].end_time

        logger.info(f"Created transcript-synced timeline: {len(timeline.steps)} steps")
        return timeline

    def _extract_node_keywords(self, nodes: List[MindmapNode]) -> Dict[str, List[str]]:
        """Extract keywords from each node's text"""
        result = {}
        for node in nodes:
            result[node.id] = self._extract_keywords(node.text)
        return result

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        if not text:
            return []

        # Convert to lowercase
        text = text.lower()

        # Remove common German/English stop words
        stop_words = {
            'der', 'die', 'das', 'und', 'in', 'zu', 'den', 'für', 'mit', 'von',
            'ist', 'sind', 'ein', 'eine', 'als', 'auf', 'auch', 'bei', 'oder',
            'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
            'wie', 'was', 'wir', 'sie', 'es', 'kann', 'können', 'werden'
        }

        # Split on non-word characters
        words = re.findall(r'\b\w+\b', text)

        # Filter and return
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        return keywords

    def _calculate_match_score(
        self,
        segment_keywords: List[str],
        node_keywords: List[str]
    ) -> float:
        """Calculate match score between segment and node keywords"""
        if not segment_keywords or not node_keywords:
            return 0.0

        # Count matching keywords
        segment_set = set(segment_keywords)
        node_set = set(node_keywords)

        intersection = segment_set & node_set
        union = segment_set | node_set

        if not union:
            return 0.0

        # Jaccard similarity
        return len(intersection) / len(union)

    def _default_video_path(self, mindmap_data: MindmapData) -> Path:
        """Generate default output path for video"""
        safe_title = "".join(
            c if c.isalnum() or c in " -_" else "_"
            for c in mindmap_data.notebook_title
        )
        safe_title = safe_title[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_animation_{timestamp}.mp4"

        return self.client.config.video_dir / filename


class AudioTranscriber:
    """
    Transcribe audio to get timestamps for animation sync.

    Uses OpenAI Whisper for speech-to-text with word-level timestamps.
    """

    def __init__(self, model_name: str = "base"):
        """
        Initialize transcriber.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        """Lazy-load Whisper model"""
        if self._model is None:
            try:
                import whisper
                logger.info(f"Loading Whisper model: {self.model_name}")
                self._model = whisper.load_model(self.model_name)
            except ImportError:
                logger.error("Whisper not installed. Run: pip install openai-whisper")
                raise

    def transcribe(self, audio_path: Path) -> List[AudioSegment]:
        """
        Transcribe audio file to segments with timestamps.

        Args:
            audio_path: Path to audio file (mp3, wav, etc.)

        Returns:
            List of AudioSegments with timing info
        """
        self._load_model()

        logger.info(f"Transcribing: {audio_path}")

        result = self._model.transcribe(
            str(audio_path),
            word_timestamps=True,
            language="de"  # German - adjust as needed
        )

        segments = []
        for seg in result.get("segments", []):
            segment = AudioSegment(
                start_time=seg.get("start", 0),
                end_time=seg.get("end", 0),
                text=seg.get("text", "").strip()
            )
            segments.append(segment)

        logger.info(f"Transcribed {len(segments)} segments")
        return segments
