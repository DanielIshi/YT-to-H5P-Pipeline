"""
NotebookLM Mindmap Extractor - Extract mindmaps as SVG and JSON structure

Based on: https://github.com/rootsongjc/notebookllm-mindmap-exporter
"""

import asyncio
import logging
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, DefaultDict
from dataclasses import dataclass, field
from datetime import datetime

from .client import NotebookLMClient
from .config import Selectors

logger = logging.getLogger(__name__)


@dataclass
class MindmapNode:
    """A node in the mindmap"""
    id: str
    text: str
    level: int
    children: List["MindmapNode"] = field(default_factory=list)
    x: Optional[float] = None
    y: Optional[float] = None
    parent_id: Optional[str] = None


@dataclass
class MindmapData:
    """Complete mindmap data"""
    notebook_id: str
    notebook_title: str
    root_node: Optional[MindmapNode] = None
    svg_content: Optional[str] = None
    nodes: List[MindmapNode] = field(default_factory=list)
    connections: List[Dict[str, str]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


class MindmapExtractor:
    """
    Extracts mindmaps from NotebookLM notebooks.

    The mindmap is rendered as SVG in the browser DOM.
    We extract the SVG and parse the node structure.

    Usage:
        async with NotebookLMClient() as client:
            extractor = MindmapExtractor(client)
            # Page must already be on notebook with mindmap visible
            mindmap = await extractor.extract_mindmap_from_page()
    """

    def __init__(self, client: NotebookLMClient):
        self.client = client

    async def extract_mindmap_from_page(self) -> MindmapData:
        """
        Extract mindmap from the current page.

        Assumes the page is already on a NotebookLM notebook.

        Returns:
            MindmapData with SVG and node structure
        """
        page = self.client.page
        current_url = page.url

        # Extract notebook ID and title from URL
        notebook_id = ""
        notebook_title = "NotebookLM Mindmap"

        if "notebook/" in current_url:
            notebook_id = current_url.split("notebook/")[-1].split("/")[0].split("?")[0]

        # Try to get title from page
        try:
            title_elem = await page.query_selector('h1, [class*="title"]')
            if title_elem:
                title_text = await title_elem.text_content()
                if title_text:
                    notebook_title = title_text.strip()[:100]
        except Exception:
            pass

        logger.info(f"Extracting mindmap from current page: {notebook_id}")

        data = MindmapData(
            notebook_id=notebook_id,
            notebook_title=notebook_title
        )

        try:
            # Try to find existing mindmap in Studio panel (Nov 2025 UI)
            mindmap_opened = await self._open_mindmap_from_studio()

            if not mindmap_opened:
                # Fallback: Click Mind map tab/button
                logger.info("Opening Mind map via button...")
                try:
                    await page.click(Selectors.MINDMAP_TAB, timeout=10000)
                    await asyncio.sleep(2)
                except Exception:
                    logger.warning("Mindmap tab not found, assuming mindmap is already visible")

            # Wait for mindmap to render
            await self._wait_for_mindmap_render()

            # Expand all nodes temporarily to get complete structure
            await self._expand_all_nodes()

            # Extract SVG content (look for large SVG)
            data.svg_content = await self._extract_svg()

            # Collapse all nodes back to initial state (only root visible)
            # This is important for the animation workflow where nodes
            # are expanded progressively as the audio narrates them
            await self._collapse_all_nodes()

            # Parse node structure from SVG text elements
            data.nodes = self._extract_nodes_from_svg(data.svg_content)

            # Build hierarchy from nodes
            if data.nodes:
                data.root_node = self._build_hierarchy(data.nodes, [])

            logger.info(f"Mindmap extracted: {len(data.nodes)} nodes")
            return data

        except Exception as e:
            logger.error(f"Mindmap extraction failed: {e}")
            return data

    async def extract_mindmap(self, notebook_id: str = None, notebook_title: str = None) -> MindmapData:
        """
        Extract mindmap from a notebook (legacy method, wraps extract_mindmap_from_page).

        Args:
            notebook_id: Optional notebook ID (extracted from URL if not provided)
            notebook_title: Optional notebook title (extracted from page if not provided)

        Returns:
            MindmapData with SVG and node structure
        """
        # Just delegate to extract_mindmap_from_page
        return await self.extract_mindmap_from_page()

    async def _open_mindmap_from_studio(self) -> bool:
        """Try to open existing mindmap from Studio panel (Nov 2025 UI)"""
        page = self.client.page

        try:
            logger.info("Looking for mindmap card in Studio panel...")

            # First try: Look for completed mindmap (has 'Quelle' but NOT 'wird erstellt')
            buttons = await page.query_selector_all('button')
            for btn in buttons:
                text = await btn.text_content()
                if not text:
                    continue
                text_lower = text.lower()

                # Skip mindmaps that are still being generated
                if 'wird erstellt' in text_lower or 'generating' in text_lower:
                    logger.debug(f"Skipping in-progress mindmap: {text[:40]}")
                    continue

                # Look for completed mindmap with 'flowchart' and 'quelle'
                if 'flowchart' in text_lower and 'quelle' in text_lower:
                    await btn.click()
                    logger.info(f"Clicked completed mindmap: {text[:50]}")
                    await asyncio.sleep(3)
                    return True

            # Second try: Wait for mindmap generation (max 30 seconds)
            logger.info("No completed mindmap found, waiting for generation...")
            max_wait = 30
            for _ in range(max_wait // 2):
                buttons = await page.query_selector_all('button')
                for btn in buttons:
                    text = await btn.text_content()
                    if not text:
                        continue
                    text_lower = text.lower()

                    # Skip still-generating mindmaps
                    if 'wird erstellt' in text_lower:
                        continue

                    if 'flowchart' in text_lower and 'quelle' in text_lower:
                        await btn.click()
                        logger.info(f"Clicked mindmap card: {text[:50]}")
                        await asyncio.sleep(3)
                        return True
                await asyncio.sleep(2)

            return False

        except Exception as e:
            logger.debug(f"Studio mindmap open failed: {e}")
            return False

    async def _wait_for_mindmap_render(self, timeout: int = 30000) -> None:
        """Wait for mindmap to render in DOM"""
        page = self.client.page
        logger.info("Waiting for mindmap to render...")

        try:
            # Wait for SVG element
            await page.wait_for_selector(
                Selectors.MINDMAP_SVG,
                timeout=timeout,
                state="visible"
            )
            # Extra time for animation
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"Mindmap render wait: {e}")

    async def _expand_all_nodes(self) -> None:
        """Expand all mindmap nodes for complete extraction.

        NotebookLM mindmap nodes have:
        - <circle> with expand indicator
        - <text class="expand-symbol"> showing ">" (collapsed) or "<" (expanded)

        We use JavaScript to click on SVG elements since Playwright can't
        directly interact with SVG internal elements.
        """
        page = self.client.page
        logger.info("Expanding all mindmap nodes...")

        try:
            # Use JavaScript to click on all collapsed nodes (those with ">")
            # This is more reliable than trying to use Playwright selectors on SVG elements
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

                logger.debug(f"Iteration {iteration + 1}: expanded {expanded} nodes")
                await asyncio.sleep(0.5)  # Wait for animation

        except Exception as e:
            logger.warning(f"Expand nodes: {e}")

    async def _collapse_all_nodes(self) -> None:
        """Collapse all mindmap nodes back to initial state (only root visible).

        This is the inverse of _expand_all_nodes(). After extracting the full
        structure, we collapse everything so the animation can progressively
        reveal nodes as the audio narrates them.

        Nodes with "<" expand-symbol are expanded and need to be clicked to collapse.
        """
        page = self.client.page
        logger.info("Collapsing all mindmap nodes to initial state...")

        try:
            # Use JavaScript to click on all expanded nodes (those with "<")
            # We collapse from deepest level first (reverse order)
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

        except Exception as e:
            logger.warning(f"Collapse nodes: {e}")

    async def _extract_svg(self) -> Optional[str]:
        """Extract raw SVG content from DOM - find the mindmap SVG"""
        page = self.client.page
        logger.info("Extracting SVG content...")

        try:
            # NotebookLM mindmap SVG characteristics:
            # - Has width="100%" height="100%"
            # - Contains <g class="node"> elements
            # - Contains <path class="link"> elements
            # - Does NOT have class="gb_F" (Google UI icon)
            # - Does NOT have focusable="false" (toolbar icons)

            # Strategy 1: Find SVG with mindmap-specific content
            all_svgs = await page.query_selector_all('svg')
            mindmap_svg = None
            mindmap_size = 0

            for svg in all_svgs:
                try:
                    # Get SVG HTML
                    html = await svg.evaluate("el => el.outerHTML")

                    # Skip Google UI icons
                    if 'class="gb_F"' in html or 'focusable="false"' in html:
                        continue

                    # Check for mindmap-specific markers
                    has_nodes = 'class="node"' in html
                    has_links = 'class="link"' in html
                    has_node_name = 'class="node-name"' in html

                    if has_nodes and (has_links or has_node_name):
                        # This is likely the mindmap!
                        if len(html) > mindmap_size:
                            mindmap_size = len(html)
                            mindmap_svg = html
                            logger.info(f"Found mindmap SVG candidate: {len(html)} chars, has nodes: {has_nodes}")

                except Exception as e:
                    logger.debug(f"SVG evaluation failed: {e}")
                    continue

            if mindmap_svg:
                logger.info(f"Selected mindmap SVG: {mindmap_size} chars")
                return mindmap_svg

            # Strategy 2: Fallback - find largest SVG that's not an icon
            logger.warning("No mindmap-specific SVG found, falling back to size-based selection")
            largest_svg = None
            largest_size = 0

            for svg in all_svgs:
                try:
                    html = await svg.evaluate("el => el.outerHTML")

                    # Skip small icons and Google UI
                    if len(html) < 2000:
                        continue
                    if 'class="gb_F"' in html or 'focusable="false"' in html:
                        continue

                    if len(html) > largest_size:
                        largest_size = len(html)
                        largest_svg = html

                except Exception:
                    continue

            if largest_svg and largest_size > 5000:
                logger.info(f"Found large SVG (fallback): {largest_size} chars")
                return largest_svg

            logger.error("No suitable mindmap SVG found")
            return None

        except Exception as e:
            logger.error(f"SVG extraction failed: {e}")
            return None

    def _extract_nodes_from_svg(self, svg_content: Optional[str]) -> List[MindmapNode]:
        """Extract nodes from SVG text elements"""
        nodes = []

        if not svg_content:
            return nodes

        try:
            # NotebookLM mindmap structure (Nov 2025):
            # <g class="node" transform="translate(x, y)">
            #   <rect ...>
            #   <text class="node-name" ...>Node Text</text>
            #   <circle ...>
            #   <text class="expand-symbol">< or ></text>
            # </g>

            # Pattern to match entire node groups with their transforms
            # This captures: transform coords AND node-name text
            node_group_pattern = r'<g class="node" transform="translate\(([^,]+),\s*([^)]+)\)"[^>]*>.*?<text class="node-name"[^>]*>([^<]+)</text>'

            matches = re.findall(node_group_pattern, svg_content, re.DOTALL)

            for i, (x_str, y_str, text) in enumerate(matches):
                text = text.strip()
                # Decode HTML entities
                text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                text = text.replace('&quot;', '"')

                if len(text) < 2:
                    continue

                x = float(x_str)
                y = float(y_str)

                # Estimate level from x-coordinate
                # Root is typically at x=0, Level 1 at x~460, Level 2 at x~750, etc.
                level = 0
                if x < 100:
                    level = 0  # Root
                elif x < 500:
                    level = 1  # First children
                elif x < 800:
                    level = 2  # Second level
                else:
                    level = 3  # Deeper levels

                node = MindmapNode(
                    id=f"node_{i}",
                    text=text,
                    level=level,
                    x=x,
                    y=y
                )
                nodes.append(node)

            logger.info(f"Extracted {len(nodes)} nodes from SVG")

            # Log node details for debugging
            if nodes:
                logger.debug(f"Root node: {nodes[0].text}")
                for node in nodes[1:]:
                    logger.debug(f"  Level {node.level}: {node.text} at ({node.x}, {node.y})")

        except Exception as e:
            logger.error(f"Node extraction from SVG failed: {e}")

        return nodes

    async def _extract_nodes(self) -> List[MindmapNode]:
        """Extract node information from SVG"""
        page = self.client.page
        nodes = []

        try:
            # Find all node groups
            node_elements = await page.query_selector_all(Selectors.MINDMAP_NODE)

            for i, elem in enumerate(node_elements):
                try:
                    # Get node text
                    text_elem = await elem.query_selector(Selectors.MINDMAP_NODE_TEXT)
                    text = ""
                    if text_elem:
                        text = await text_elem.text_content() or ""

                    # Get position (for hierarchy detection)
                    transform = await elem.get_attribute("transform") or ""
                    x, y = self._parse_transform(transform)

                    # Estimate level from x-coordinate (left = higher level)
                    level = self._estimate_level_from_x(x) if x is not None else 0

                    node = MindmapNode(
                        id=f"node_{i}",
                        text=text.strip(),
                        level=level,
                        x=x,
                        y=y
                    )
                    nodes.append(node)

                except Exception as e:
                    logger.debug(f"Node extraction error: {e}")

        except Exception as e:
            logger.error(f"Nodes extraction failed: {e}")

        return nodes

    async def _extract_connections(self) -> List[Dict[str, str]]:
        """Extract connection/link information"""
        page = self.client.page
        connections = []

        try:
            # Find all path/line elements (connections)
            link_elements = await page.query_selector_all(Selectors.MINDMAP_CONNECTION)

            for elem in link_elements:
                try:
                    # Try to get source/target from data attributes
                    source = await elem.get_attribute("data-source")
                    target = await elem.get_attribute("data-target")

                    if source and target:
                        connections.append({
                            "source": source,
                            "target": target
                        })

                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"Connections extraction: {e}")

        return connections

    def _parse_transform(self, transform: str) -> tuple:
        """Parse SVG transform attribute to get x, y coordinates"""
        x, y = None, None

        # Pattern: translate(x, y) or translate(x,y)
        match = re.search(r'translate\s*\(\s*([-\d.]+)\s*,?\s*([-\d.]+)?\s*\)', transform)
        if match:
            x = float(match.group(1))
            y = float(match.group(2)) if match.group(2) else 0

        return x, y

    def _estimate_level_from_x(self, x: float, base_offset: float = 100) -> int:
        """Estimate hierarchy level from x-coordinate"""
        if x is None:
            return 0
        # NotebookLM mindmap layout:
        # - Root at x=0
        # - Level 1 at x~460
        # - Level 2 at x~750+
        # - etc.
        if x < 100:
            return 0  # Root
        elif x < 500:
            return 1  # First children
        elif x < 800:
            return 2  # Second level
        else:
            return 3  # Deeper levels

    def _build_hierarchy(
        self,
        nodes: List[MindmapNode],
        connections: List[Dict[str, str]]
    ) -> Optional[MindmapNode]:
        """Build hierarchical structure from flat nodes and connections"""
        if not nodes:
            return None

        # If we have explicit connection data, use it
        if connections:
            node_map = {n.id: n for n in nodes}
            for conn in connections:
                source = node_map.get(conn["source"])
                target = node_map.get(conn["target"])
                if source and target:
                    target.parent_id = source.id
                    source.children.append(target)

            # Find root (no parent)
            for node in nodes:
                if node.parent_id is None:
                    return node

        # Build hierarchy from coordinates
        # NotebookLM mindmap layout:
        # - Root at x=0
        # - Children at x~460
        # - Grandchildren at x~750
        # - Y coordinate determines vertical position within level

        # Sort by x to find root (leftmost)
        sorted_by_x = sorted(nodes, key=lambda n: n.x or 0)
        if not sorted_by_x:
            return None

        root = sorted_by_x[0]
        root.level = 0
        root.children = []  # Reset children

        # Group nodes by level based on x-coordinate
        level_groups: Dict[int, List[MindmapNode]] = {0: [root]}

        for node in sorted_by_x[1:]:
            level = self._estimate_level_from_x(node.x or 0)
            node.level = level
            node.children = []  # Reset children

            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(node)

        # Build parent-child relationships
        # For each level, assign nodes to their nearest parent in the previous level
        for level in range(1, max(level_groups.keys()) + 1):
            if level not in level_groups or (level - 1) not in level_groups:
                continue

            current_level_nodes = sorted(level_groups[level], key=lambda n: n.y or 0)
            parent_level_nodes = sorted(level_groups[level - 1], key=lambda n: n.y or 0)

            for node in current_level_nodes:
                # Find the nearest parent by y-coordinate
                best_parent = None
                best_distance = float('inf')

                for parent in parent_level_nodes:
                    if node.y is not None and parent.y is not None:
                        distance = abs(node.y - parent.y)
                        if distance < best_distance:
                            best_distance = distance
                            best_parent = parent

                if best_parent:
                    node.parent_id = best_parent.id
                    best_parent.children.append(node)

        logger.info(f"Built hierarchy: root='{root.text}' with {len(root.children)} direct children")
        return root

    async def save_mindmap(
        self,
        data: MindmapData,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Path]:
        """
        Save mindmap to files.

        Args:
            data: Mindmap data to save
            output_dir: Directory to save files

        Returns:
            Dict with file paths
        """
        output_dir = output_dir or self.client.config.mindmap_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in data.notebook_title)
        safe_title = safe_title[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{safe_title}_{timestamp}"

        paths = {}

        # Save SVG
        if data.svg_content:
            svg_path = output_dir / f"{base_name}.svg"
            svg_path.write_text(data.svg_content, encoding="utf-8")
            paths["svg"] = svg_path
            logger.info(f"SVG saved: {svg_path}")

        # Save JSON structure
        json_data = {
            "notebook_id": data.notebook_id,
            "notebook_title": data.notebook_title,
            "generated_at": data.generated_at.isoformat(),
            "nodes": [self._node_to_dict(n) for n in data.nodes],
            "connections": data.connections,
            "hierarchy": self._node_to_dict(data.root_node) if data.root_node else None
        }
        json_path = output_dir / f"{base_name}.json"
        json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
        paths["json"] = json_path
        logger.info(f"JSON saved: {json_path}")

        return paths

    def _node_to_dict(self, node: MindmapNode) -> Dict[str, Any]:
        """Convert MindmapNode to dict for JSON serialization"""
        return {
            "id": node.id,
            "text": node.text,
            "level": node.level,
            "x": node.x,
            "y": node.y,
            "parent_id": node.parent_id,
            "children": [self._node_to_dict(c) for c in node.children]
        }

    def export_to_markdown(self, data: MindmapData) -> str:
        """Export mindmap structure as Markdown"""
        lines = [
            f"# {data.notebook_title} - Mindmap",
            f"\n*Generated: {data.generated_at.isoformat()}*\n",
        ]

        if data.root_node:
            lines.append(self._node_to_markdown(data.root_node, 0))
        elif data.nodes:
            # Flat list
            for node in sorted(data.nodes, key=lambda n: (n.level, n.y or 0)):
                indent = "  " * node.level
                lines.append(f"{indent}- {node.text}")

        return "\n".join(lines)

    def _node_to_markdown(self, node: MindmapNode, depth: int) -> str:
        """Recursively convert node to Markdown list"""
        indent = "  " * depth
        line = f"{indent}- {node.text}"

        child_lines = [self._node_to_markdown(c, depth + 1) for c in node.children]
        if child_lines:
            return line + "\n" + "\n".join(child_lines)
        return line
