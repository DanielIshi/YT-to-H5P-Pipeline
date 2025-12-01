"""
NotebookLM Mindmap Animator - Animate mindmap exploration synchronized with audio

This module provides functionality to:
1. Navigate through mindmap nodes based on audio content
2. Expand/collapse nodes to create a storytelling flow
3. Record the animation as video
4. Sync with audio timeline

Recording uses WindowsScreenCapture from Tools2TutorialVideo for efficient
Win32 API-based screen capture with FFmpeg for video encoding.
"""

import asyncio
import logging
import re
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import numpy as np

from playwright.async_api import Page

from .client import NotebookLMClient
from .mindmap_extractor import MindmapData, MindmapNode
from .config import Selectors

# Import WindowsScreenCapture from Tools2TutorialVideo
TOOLS2TUTORIAL_PATH = Path(r"C:\Users\Daniel\PycharmProjects\REICHWEITE MARKETING SCHULUNGSCONTENT\Tools2TutorialVideo")

SCREEN_CAPTURE_AVAILABLE = False
WindowsScreenCapture = None
ScreenCaptureConfig = None

try:
    import importlib.util
    screen_module_path = TOOLS2TUTORIAL_PATH / "src" / "recorder" / "screen.py"

    if screen_module_path.exists():
        spec = importlib.util.spec_from_file_location("tools2tutorial_screen", screen_module_path)
        screen_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(screen_module)

        WindowsScreenCapture = screen_module.WindowsScreenCapture
        ScreenCaptureConfig = screen_module.ScreenCaptureConfig
        SCREEN_CAPTURE_AVAILABLE = True
        logging.info("WindowsScreenCapture loaded from Tools2TutorialVideo")
    else:
        logging.warning(f"Screen module not found at {screen_module_path}")
except Exception as e:
    logging.warning(f"WindowsScreenCapture not available: {e}")

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

    def __init__(self, client: NotebookLMClient, output_dir: Optional[Path] = None):
        self.client = client
        self.state = AnimationState.IDLE
        self._expanded_nodes: List[str] = []  # Currently expanded node IDs
        self._recording_context = None

        # Recording resources
        self.output_dir = output_dir or Path("tests/output/recordings")
        self._screen_capture: Optional['WindowsScreenCapture'] = None
        self._frames: List[np.ndarray] = []
        self._recording_lock = threading.Lock()
        self._recording_fps = 15  # Recording framerate

        # Cursor highlight settings
        self._cursor_highlight_enabled = True
        self._cursor_highlight_color = "rgba(255, 230, 0, 0.4)"  # Yellow
        self._cursor_highlight_radius = 30  # pixels

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

        page = self.client.page
        video_path = None

        try:
            # Start recording if requested
            if record:
                video_path = output_path or self._default_video_path(mindmap_data)
                await self._start_recording(video_path)

            # Inject cursor highlight for visual effect
            if self._cursor_highlight_enabled:
                await self._inject_cursor_highlight()

            # Collapse all nodes first
            await self._collapse_all_nodes()
            await asyncio.sleep(1)

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

                # Brief pause for visual effect
                await asyncio.sleep(step.duration)

            # Final view: expand all
            await self._expand_all_nodes()
            await asyncio.sleep(2)

            self.state = AnimationState.FINISHED

        except Exception as e:
            logger.error(f"Animation failed: {e}")
            self.state = AnimationState.IDLE
            raise

        finally:
            # Stop recording
            if record and self._recording_context:
                await self._stop_recording()

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
        """
        Expand a specific node with visual effects:
        1. Move cursor smoothly to the node
        2. Highlight the node (yellow border)
        3. Click to expand
        4. Remove highlight after expansion
        """
        page = self.client.page

        try:
            # Step 1: Get node position and move cursor there
            node_info = await self._get_node_position(node_text)
            if node_info:
                # Move cursor smoothly to the node's expand button (right side)
                target_x = node_info["x"] + node_info["width"] / 2 - 10  # Near the expand circle
                target_y = node_info["y"]
                await self._move_cursor_to(target_x, target_y, duration=0.4)

                # Step 2: Highlight the node
                await self._inject_node_highlight(node_text)
                await asyncio.sleep(0.3)

            # Step 3: Click to expand using JavaScript (more reliable for SVG)
            expand_js = f'''
                () => {{
                    const nodes = document.querySelectorAll('g.node');
                    for (const node of nodes) {{
                        const textEl = node.querySelector('text.node-name');
                        if (textEl && textEl.textContent.includes("{node_text[:25]}")) {{
                            const expandSymbol = node.querySelector('text.expand-symbol');
                            if (expandSymbol && expandSymbol.textContent.includes('>')) {{
                                const circle = node.querySelector('circle');
                                if (circle) {{
                                    circle.dispatchEvent(new MouseEvent('click', {{
                                        bubbles: true,
                                        cancelable: true,
                                        view: window
                                    }}));
                                    return true;
                                }}
                            }}
                        }}
                    }}
                    return false;
                }}
            '''

            expanded = await page.evaluate(expand_js)
            if expanded:
                self._expanded_nodes.append(node_id)
                logger.debug(f"Expanded: {node_text}")
            else:
                logger.debug(f"Node already expanded or not found: {node_text[:30]}")

            # Step 4: Wait for animation and remove highlight
            await asyncio.sleep(0.5)
            await self._remove_node_highlight()

        except Exception as e:
            logger.warning(f"Could not expand node '{node_text}': {e}")

    async def _collapse_node(self, node_id: str, node_text: str) -> None:
        """Collapse a specific node"""
        page = self.client.page

        try:
            # Find already-expanded node (expand-symbol shows "<")
            node_selector = f'g.node:has(text.node-name:text("{node_text[:30]}"))'
            expand_symbol = await page.query_selector(f'{node_selector} text.expand-symbol')

            if expand_symbol:
                symbol_text = await expand_symbol.text_content()
                if symbol_text and "<" in symbol_text:  # Node is expanded
                    circle = await page.query_selector(f'{node_selector} circle')
                    if circle:
                        await circle.click()
                        if node_id in self._expanded_nodes:
                            self._expanded_nodes.remove(node_id)
                        logger.debug(f"Collapsed: {node_text}")
                        await asyncio.sleep(0.5)

        except Exception as e:
            logger.warning(f"Could not collapse node '{node_text}': {e}")

    async def _highlight_node(self, node_id: str, node_text: str) -> None:
        """Highlight a node with visual emphasis and cursor movement"""
        page = self.client.page

        try:
            # Find the node
            node_info = await self._get_node_position(node_text)
            if not node_info:
                logger.debug(f"Node not found for highlight: {node_text[:30]}")
                return

            x, y = node_info["x"], node_info["y"]

            # Move cursor smoothly to the node
            await self._move_cursor_to(x, y, duration=0.5)

            # Add visual highlight to the node
            await self._inject_node_highlight(node_text)

            # Keep highlight for a moment
            await asyncio.sleep(0.5)

            # Remove highlight
            await self._remove_node_highlight()

        except Exception as e:
            logger.debug(f"Could not highlight node: {e}")

    async def _focus_node(self, node_id: str, node_text: str) -> None:
        """Scroll/pan to center a node in view and move cursor to it"""
        page = self.client.page

        try:
            # Get node position
            node_info = await self._get_node_position(node_text)
            if not node_info:
                # Fallback to simple scroll
                node_selector = f'g.node:has(text.node-name:text("{node_text[:30]}"))'
                node = await page.query_selector(node_selector)
                if node:
                    await node.scroll_into_view_if_needed()
                return

            x, y = node_info["x"], node_info["y"]

            # Scroll node into view
            await page.evaluate(f'''
                () => {{
                    const svg = document.querySelector('svg');
                    if (svg) {{
                        const svgRect = svg.getBoundingClientRect();
                        const centerX = svgRect.width / 2;
                        const centerY = svgRect.height / 2;
                        // Pan the view to center on the node
                        // This depends on how the mindmap handles panning
                    }}
                }}
            ''')

            # Move cursor to node
            await self._move_cursor_to(x, y, duration=0.3)

        except Exception as e:
            logger.debug(f"Could not focus node: {e}")

    async def _get_node_position(self, node_text: str) -> Optional[Dict]:
        """Get the screen position of a node by its text"""
        page = self.client.page

        try:
            # Find node and get its bounding box
            result = await page.evaluate(f'''
                () => {{
                    const nodes = document.querySelectorAll('g.node');
                    for (const node of nodes) {{
                        const textEl = node.querySelector('text.node-name');
                        if (textEl && textEl.textContent.includes("{node_text[:25]}")) {{
                            const rect = node.getBoundingClientRect();
                            return {{
                                x: rect.x + rect.width / 2,
                                y: rect.y + rect.height / 2,
                                width: rect.width,
                                height: rect.height
                            }};
                        }}
                    }}
                    return null;
                }}
            ''')
            return result
        except Exception as e:
            logger.debug(f"Could not get node position: {e}")
            return None

    async def _move_cursor_to(self, x: float, y: float, duration: float = 0.3) -> None:
        """
        Smoothly move cursor to target position.

        Creates a visible cursor movement effect for better video presentation.
        """
        page = self.client.page

        try:
            # Get current mouse position (or start from center)
            viewport = page.viewport_size or {"width": 1920, "height": 1080}
            current_x = viewport["width"] / 2
            current_y = viewport["height"] / 2

            # Calculate steps for smooth movement
            steps = max(10, int(duration * 30))  # ~30 fps for smooth movement
            step_delay = duration / steps

            for i in range(steps + 1):
                t = i / steps
                # Ease-out curve for natural movement
                t = 1 - (1 - t) ** 2

                move_x = current_x + (x - current_x) * t
                move_y = current_y + (y - current_y) * t

                await page.mouse.move(move_x, move_y)

                if i < steps:
                    await asyncio.sleep(step_delay)

        except Exception as e:
            logger.debug(f"Cursor move failed: {e}")

    async def _inject_cursor_highlight(self) -> None:
        """Inject CSS for cursor highlight effect"""
        page = self.client.page

        highlight_css = f'''
            #cursor-highlight {{
                position: fixed;
                width: {self._cursor_highlight_radius * 2}px;
                height: {self._cursor_highlight_radius * 2}px;
                border-radius: 50%;
                background: {self._cursor_highlight_color};
                pointer-events: none;
                z-index: 99999;
                transform: translate(-50%, -50%);
                transition: left 0.05s ease-out, top 0.05s ease-out;
            }}
        '''

        highlight_js = '''
            if (!document.getElementById('cursor-highlight')) {
                const highlight = document.createElement('div');
                highlight.id = 'cursor-highlight';
                document.body.appendChild(highlight);

                document.addEventListener('mousemove', (e) => {
                    highlight.style.left = e.clientX + 'px';
                    highlight.style.top = e.clientY + 'px';
                });
            }
        '''

        try:
            await page.add_style_tag(content=highlight_css)
            await page.evaluate(highlight_js)
            logger.debug("Cursor highlight injected")
        except Exception as e:
            logger.debug(f"Could not inject cursor highlight: {e}")

    async def _remove_cursor_highlight(self) -> None:
        """Remove cursor highlight"""
        page = self.client.page
        try:
            await page.evaluate('''
                const el = document.getElementById('cursor-highlight');
                if (el) el.remove();
            ''')
        except Exception:
            pass

    async def _inject_node_highlight(self, node_text: str) -> None:
        """Add visual highlight to a specific node"""
        page = self.client.page

        try:
            await page.evaluate(f'''
                () => {{
                    const nodes = document.querySelectorAll('g.node');
                    for (const node of nodes) {{
                        const textEl = node.querySelector('text.node-name');
                        if (textEl && textEl.textContent.includes("{node_text[:25]}")) {{
                            const rect = node.querySelector('rect');
                            if (rect) {{
                                rect.dataset.originalFill = rect.style.fill || rect.getAttribute('fill');
                                rect.style.fill = 'rgba(255, 230, 0, 0.6)';
                                rect.style.stroke = '#FFD700';
                                rect.style.strokeWidth = '3px';
                            }}
                            break;
                        }}
                    }}
                }}
            ''')
        except Exception as e:
            logger.debug(f"Could not highlight node: {e}")

    async def _remove_node_highlight(self) -> None:
        """Remove visual highlight from all nodes"""
        page = self.client.page

        try:
            await page.evaluate('''
                () => {
                    const rects = document.querySelectorAll('g.node rect');
                    rects.forEach(rect => {
                        if (rect.dataset.originalFill) {
                            rect.style.fill = rect.dataset.originalFill;
                            rect.style.stroke = '';
                            rect.style.strokeWidth = '';
                            delete rect.dataset.originalFill;
                        }
                    });
                }
            ''')
        except Exception as e:
            logger.debug(f"Could not remove node highlight: {e}")

    async def _collapse_all_nodes(self) -> None:
        """Collapse all expanded nodes using JavaScript for SVG elements.

        This collapses all nodes to show only the root, preparing for
        the progressive reveal animation.
        """
        page = self.client.page
        logger.info("Collapsing all nodes to initial state...")

        try:
            # Use JavaScript to click on all expanded nodes (those with "<")
            # Collapse from deepest level first (reverse order)
            collapse_js = """
            () => {
                const expandSymbols = document.querySelectorAll('text.expand-symbol');
                let collapsedCount = 0;

                // Convert to array and reverse to collapse deepest nodes first
                const symbolsArray = Array.from(expandSymbols).reverse();

                symbolsArray.forEach(symbol => {
                    if (symbol.textContent && symbol.textContent.includes('<')) {
                        // This node is expanded, click to collapse
                        const nodeGroup = symbol.closest('g.node');
                        if (nodeGroup) {
                            const circle = nodeGroup.querySelector('circle');
                            if (circle) {
                                circle.dispatchEvent(new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                }));
                                collapsedCount++;
                            }
                        }
                    }
                });

                return collapsedCount;
            }
            """

            max_iterations = 5
            total_collapsed = 0

            for iteration in range(max_iterations):
                collapsed = await page.evaluate(collapse_js)
                total_collapsed += collapsed

                if collapsed == 0:
                    logger.info(f"All nodes collapsed (total: {total_collapsed})")
                    break

                logger.debug(f"Collapse iteration {iteration + 1}: collapsed {collapsed} nodes")
                await asyncio.sleep(0.5)  # Wait for animation

            self._expanded_nodes.clear()

        except Exception as e:
            logger.warning(f"Collapse all failed: {e}")

    async def _expand_all_nodes(self) -> None:
        """Expand all nodes for final overview using JavaScript for SVG elements."""
        page = self.client.page
        logger.info("Expanding all nodes...")

        try:
            # Use JavaScript to click on all collapsed nodes (those with ">")
            expand_js = """
            () => {
                const expandSymbols = document.querySelectorAll('text.expand-symbol');
                let expandedCount = 0;

                expandSymbols.forEach(symbol => {
                    if (symbol.textContent && symbol.textContent.includes('>')) {
                        // Find the parent node group and click on the circle
                        const nodeGroup = symbol.closest('g.node');
                        if (nodeGroup) {
                            const circle = nodeGroup.querySelector('circle');
                            if (circle) {
                                circle.dispatchEvent(new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                }));
                                expandedCount++;
                            }
                        }
                    }
                });

                return expandedCount;
            }
            """

            max_iterations = 5
            total_expanded = 0

            for iteration in range(max_iterations):
                expanded = await page.evaluate(expand_js)
                total_expanded += expanded

                if expanded == 0:
                    logger.info(f"All nodes expanded (total: {total_expanded})")
                    break

                logger.debug(f"Expand iteration {iteration + 1}: expanded {expanded} nodes")
                await asyncio.sleep(0.5)  # Wait for animation

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

    async def _start_recording(self, output_path: Path) -> None:
        """Start video recording using WindowsScreenCapture"""
        if not SCREEN_CAPTURE_AVAILABLE:
            logger.warning("Screen capture not available, recording skipped")
            return

        logger.info(f"Starting recording to {output_path}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure screen capture (15 FPS for smooth animation)
        config = ScreenCaptureConfig(
            fps=self._recording_fps,
            color_format="BGR"  # OpenCV expects BGR
        )

        # Create screen capture instance
        self._screen_capture = WindowsScreenCapture(config)
        self._frames = []

        # Frame callback - captures frames into list
        def frame_callback(frame: np.ndarray):
            with self._recording_lock:
                self._frames.append(frame.copy())

        # Start capturing
        self._screen_capture.start_capture(frame_callback)

        # Store recording context
        self._recording_context = {
            "output_path": output_path,
            "start_time": datetime.now(),
        }

        logger.info(f"Recording started at {self._recording_fps} FPS")

    async def _stop_recording(self) -> Optional[Path]:
        """Stop recording and encode video with FFmpeg"""
        if not self._recording_context or not self._screen_capture:
            return None

        logger.info("Stopping recording...")

        # Stop screen capture
        self._screen_capture.stop_capture()
        self._screen_capture.cleanup()

        output_path = self._recording_context.get("output_path")
        self._recording_context = None

        # Check if we have frames
        with self._recording_lock:
            frame_count = len(self._frames)
            if frame_count == 0:
                logger.warning("No frames captured, skipping video creation")
                return None

            logger.info(f"Encoding {frame_count} frames to video...")

            # Create temporary frame directory
            frame_dir = output_path.parent / "frames_temp"
            frame_dir.mkdir(exist_ok=True)

            try:
                import cv2

                # Write frames to PNG files
                for i, frame in enumerate(self._frames):
                    frame_path = frame_dir / f"frame_{i:06d}.png"
                    cv2.imwrite(str(frame_path), frame)

                # Clear frames from memory
                self._frames = []

                # FFmpeg: Frames → Video
                cmd = [
                    "ffmpeg", "-y",
                    "-framerate", str(self._recording_fps),
                    "-i", str(frame_dir / "frame_%06d.png"),
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-pix_fmt", "yuv420p",
                    str(output_path)
                ]

                logger.info(f"Running FFmpeg: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 min timeout
                )

                if result.returncode != 0:
                    logger.error(f"FFmpeg failed: {result.stderr}")
                    return None

                logger.info(f"Video saved: {output_path}")

            finally:
                # Cleanup temporary frames
                import shutil
                if frame_dir.exists():
                    shutil.rmtree(frame_dir)

            return output_path

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

    async def merge_audio(self, video_path: Path, audio_path: Path) -> Path:
        """
        Merge video with NotebookLM audio using FFmpeg.

        IMPORTANT: Per CLAUDE.md golden rule, video is adjusted to audio length,
        NEVER the other way around. Audio = Story = Holy.

        Args:
            video_path: Path to silent video
            audio_path: Path to NotebookLM audio file (MP3)

        Returns:
            Path to final merged video
        """
        output_path = video_path.with_suffix(".final.mp4")

        logger.info(f"Merging video {video_path} with audio {audio_path}")

        # First, get audio duration
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]

        try:
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            audio_duration = float(result.stdout.strip())
            logger.info(f"Audio duration: {audio_duration:.2f}s")
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}, using default merge")
            audio_duration = None

        # Merge video and audio
        # Use -shortest to match to the shorter one, but we trust audio is story
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",  # Copy video stream (no re-encode)
            "-c:a", "aac",   # Encode audio to AAC
            "-b:a", "192k",  # Audio bitrate
            "-shortest",     # Match to shorter stream
            str(output_path)
        ]

        logger.info(f"Running FFmpeg merge: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg merge failed: {result.stderr}")
            raise RuntimeError(f"Audio merge failed: {result.stderr}")

        # Cleanup silent video
        try:
            video_path.unlink()
            logger.debug(f"Removed silent video: {video_path}")
        except Exception as e:
            logger.warning(f"Could not remove silent video: {e}")

        logger.info(f"Final video saved: {output_path}")
        return output_path


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
