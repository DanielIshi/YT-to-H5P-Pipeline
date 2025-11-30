"""
NotebookLM Mindmap Extractor - Extract mindmaps as SVG and JSON structure

Based on: https://github.com/rootsongjc/notebookllm-mindmap-exporter
"""

import asyncio
import logging
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from .client import NotebookLMClient
from .notebook_manager import Notebook
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
            mindmap = await extractor.extract_mindmap(notebook)
    """

    def __init__(self, client: NotebookLMClient):
        self.client = client

    async def extract_mindmap(self, notebook: Notebook) -> MindmapData:
        """
        Extract mindmap from a notebook.

        Args:
            notebook: Target notebook

        Returns:
            MindmapData with SVG and node structure
        """
        logger.info(f"Extracting mindmap from notebook: {notebook.id}")

        data = MindmapData(
            notebook_id=notebook.id or "",
            notebook_title=notebook.title
        )

        page = self.client.page

        try:
            # Navigate to notebook if needed
            await self._ensure_notebook_open(notebook)

            # Click Mind map tab
            logger.info("Opening Mind map tab...")
            await page.click(Selectors.MINDMAP_TAB, timeout=10000)
            await asyncio.sleep(2)

            # Wait for mindmap to render
            await self._wait_for_mindmap_render()

            # Expand all nodes (important for complete extraction!)
            await self._expand_all_nodes()

            # Extract SVG content
            data.svg_content = await self._extract_svg()

            # Parse node structure
            data.nodes = await self._extract_nodes()
            data.connections = await self._extract_connections()

            # Build hierarchy
            if data.nodes:
                data.root_node = self._build_hierarchy(data.nodes, data.connections)

            logger.info(f"Mindmap extracted: {len(data.nodes)} nodes")
            return data

        except Exception as e:
            logger.error(f"Mindmap extraction failed: {e}")
            return data

    async def _ensure_notebook_open(self, notebook: Notebook) -> None:
        """Navigate to notebook if not already open"""
        current_url = await self.client.get_current_url()
        if notebook.url and notebook.url not in current_url:
            await self.client.page.goto(notebook.url)
            await self.client.wait_for_loading()

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
        """Expand all mindmap nodes for complete extraction"""
        page = self.client.page
        logger.info("Expanding all mindmap nodes...")

        try:
            # Try "Expand all" button first
            expand_btn = await page.query_selector(Selectors.MINDMAP_EXPAND_ALL)
            if expand_btn and await expand_btn.is_visible():
                await expand_btn.click()
                await asyncio.sleep(2)
                return

            # Fallback: Click each expandable node
            max_iterations = 10
            for _ in range(max_iterations):
                # Find nodes with expand indicators
                expandable = await page.query_selector_all(
                    '[class*="expand"], [class*="collapsed"], [data-expandable="true"]'
                )

                if not expandable:
                    break

                clicked = False
                for node in expandable:
                    try:
                        if await node.is_visible():
                            await node.click()
                            clicked = True
                            await asyncio.sleep(0.3)
                    except Exception:
                        pass

                if not clicked:
                    break

                await asyncio.sleep(0.5)

        except Exception as e:
            logger.warning(f"Expand nodes: {e}")

    async def _extract_svg(self) -> Optional[str]:
        """Extract raw SVG content from DOM"""
        page = self.client.page
        logger.info("Extracting SVG content...")

        try:
            # Find SVG element
            svg_element = await page.query_selector(Selectors.MINDMAP_SVG)
            if svg_element:
                # Get outer HTML (includes SVG tag)
                svg_content = await svg_element.evaluate("el => el.outerHTML")
                return svg_content

            # Fallback: Try container
            container = await page.query_selector(Selectors.MINDMAP_CONTAINER)
            if container:
                svg_in_container = await container.query_selector("svg")
                if svg_in_container:
                    return await svg_in_container.evaluate("el => el.outerHTML")

        except Exception as e:
            logger.error(f"SVG extraction failed: {e}")

        return None

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
        # Assume root is at center/left, children expand right
        level = max(0, int(x / base_offset))
        return level

    def _build_hierarchy(
        self,
        nodes: List[MindmapNode],
        connections: List[Dict[str, str]]
    ) -> Optional[MindmapNode]:
        """Build hierarchical structure from flat nodes and connections"""
        if not nodes:
            return None

        # If we have connection data, use it
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

        # Fallback: Use x-coordinate for hierarchy
        # Sort by x (leftmost = root)
        sorted_nodes = sorted(nodes, key=lambda n: n.x or 0)
        if sorted_nodes:
            root = sorted_nodes[0]
            root.level = 0

            # Simple assignment based on x
            for node in sorted_nodes[1:]:
                node.level = self._estimate_level_from_x(node.x or 0)

            return root

        return None

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
