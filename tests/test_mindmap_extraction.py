"""
Tests for Mindmap Node Extraction

Tests the regex patterns and hierarchy building against real NotebookLM SVG data.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.notebooklm.mindmap_extractor import MindmapExtractor, MindmapNode, MindmapData


# Real SVG from NotebookLM (Nov 2025)
REAL_MINDMAP_SVG = '''<svg width="100%" height="100%" style="overflow: scroll;"><g transform="translate(-30.67090606689453,367.25) scale(0.9)"><path class="link" d="M 370.3797912597656 0
          C 406.3797912597656 0,
            406.3797912597656 -160,
            442.3797912597656 -160" style="fill: none; stroke: rgb(195, 202, 255); stroke-width: 2px;"></path><path class="link" d="M 370.3797912597656 0
          C 406.3797912597656 0,
            406.3797912597656 -79.99999999999999,
            442.3797912597656 -79.99999999999999" style="fill: none; stroke: rgb(195, 202, 255); stroke-width: 2px;"></path><path class="link" d="M 370.3797912597656 0
          C 406.3797912597656 0,
            406.3797912597656 0,
            442.3797912597656 0" style="fill: none; stroke: rgb(195, 202, 255); stroke-width: 2px;"></path><path class="link" d="M 370.3797912597656 0
          C 406.3797912597656 0,
            406.3797912597656 80,
            442.3797912597656 80" style="fill: none; stroke: rgb(195, 202, 255); stroke-width: 2px;"></path><path class="link" d="M 370.3797912597656 0
          C 406.3797912597656 0,
            406.3797912597656 160,
            442.3797912597656 160" style="fill: none; stroke: rgb(195, 202, 255); stroke-width: 2px;"></path><g class="node" transform="translate(0, 0)"><rect rx="8" ry="8" style="fill: rgb(195, 202, 255); cursor: pointer;" x="-18" y="-27.5" width="366.3797912597656" height="55"></rect><text class="node-name" style="text-anchor: start; font-size: 20px; font-family: &quot;Google Sans&quot;; dominant-baseline: middle; fill: rgb(0, 0, 0); pointer-events: none;">Private &amp; Corporate LLM Masterclass</text><circle r="12" fill-opacity="1" transform="translate(370.3797912597656, 0)" style="fill: rgb(195, 202, 255); cursor: pointer;"></circle><text class="expand-symbol" transform="translate(370.3797912597656, 0)" style="font-size: 20px; text-anchor: middle; font-family: &quot;Google Sans&quot;; fill: rgb(0, 0, 0); pointer-events: none; dominant-baseline: middle;">&lt;</text></g><g class="node" transform="translate(460.3797912597656, -160)"><rect rx="8" ry="8" style="fill: rgb(186, 211, 238); cursor: pointer;" x="-18" y="-27.5" width="286.53125" height="55"></rect><text class="node-name" style="text-anchor: start; font-size: 20px; font-family: &quot;Google Sans&quot;; dominant-baseline: middle; fill: rgb(0, 0, 0); pointer-events: none;">Einführung &amp; Notwendigkeit</text><circle r="12" fill-opacity="1" transform="translate(290.53125, 0)" style="fill: rgb(186, 211, 238); cursor: pointer;"></circle><text class="expand-symbol" transform="translate(290.53125, 0)" style="font-size: 20px; text-anchor: middle; font-family: &quot;Google Sans&quot;; fill: rgb(0, 0, 0); pointer-events: none; dominant-baseline: middle;">&gt;</text></g><g class="node" transform="translate(460.3797912597656, -80)"><rect rx="8" ry="8" style="fill: rgb(186, 211, 238); cursor: pointer;" x="-18" y="-27.5" width="273.75" height="55"></rect><text class="node-name" style="text-anchor: start; font-size: 20px; font-family: &quot;Google Sans&quot;; dominant-baseline: middle; fill: rgb(0, 0, 0); pointer-events: none;">Grundlagen &amp; Definitionen</text><circle r="12" fill-opacity="1" transform="translate(277.75, 0)" style="fill: rgb(186, 211, 238); cursor: pointer;"></circle><text class="expand-symbol" transform="translate(277.75, 0)" style="font-size: 20px; text-anchor: middle; font-family: &quot;Google Sans&quot;; fill: rgb(0, 0, 0); pointer-events: none; dominant-baseline: middle;">&gt;</text></g><g class="node" transform="translate(460.3797912597656, 0)"><rect rx="8" ry="8" style="fill: rgb(186, 211, 238); cursor: pointer;" x="-18" y="-27.5" width="296.609375" height="55"></rect><text class="node-name" style="text-anchor: start; font-size: 20px; font-family: &quot;Google Sans&quot;; dominant-baseline: middle; fill: rgb(0, 0, 0); pointer-events: none;">Technische Basis &amp; Hardware</text><circle r="12" fill-opacity="1" transform="translate(300.609375, 0)" style="fill: rgb(186, 211, 238); cursor: pointer;"></circle><text class="expand-symbol" transform="translate(300.609375, 0)" style="font-size: 20px; text-anchor: middle; font-family: &quot;Google Sans&quot;; fill: rgb(0, 0, 0); pointer-events: none; dominant-baseline: middle;">&gt;</text></g><g class="node" transform="translate(460.3797912597656, 80)"><rect rx="8" ry="8" style="fill: rgb(186, 211, 238); cursor: pointer;" x="-18" y="-27.5" width="228.25987243652344" height="55"></rect><text class="node-name" style="text-anchor: start; font-size: 20px; font-family: &quot;Google Sans&quot;; dominant-baseline: middle; fill: rgb(0, 0, 0); pointer-events: none;">Praktische Use Cases</text><circle r="12" fill-opacity="1" transform="translate(232.25987243652344, 0)" style="fill: rgb(186, 211, 238); cursor: pointer;"></circle><text class="expand-symbol" transform="translate(232.25987243652344, 0)" style="font-size: 20px; text-anchor: middle; font-family: &quot;Google Sans&quot;; fill: rgb(0, 0, 0); pointer-events: none; dominant-baseline: middle;">&gt;</text></g><g class="node" transform="translate(460.3797912597656, 160)"><rect rx="8" ry="8" style="fill: rgb(186, 211, 238); cursor: pointer;" x="-18" y="-27.5" width="246.203125" height="55"></rect><text class="node-name" style="text-anchor: start; font-size: 20px; font-family: &quot;Google Sans&quot;; dominant-baseline: middle; fill: rgb(0, 0, 0); pointer-events: none;">Geschäftliche Chancen</text><circle r="12" fill-opacity="1" transform="translate(250.203125, 0)" style="fill: rgb(186, 211, 238); cursor: pointer;"></circle><text class="expand-symbol" transform="translate(250.203125, 0)" style="font-size: 20px; text-anchor: middle; font-family: &quot;Google Sans&quot;; fill: rgb(0, 0, 0); pointer-events: none; dominant-baseline: middle;">&gt;</text></g></g></svg>'''


class MockClient:
    """Mock client for testing without browser"""
    pass


class TestMindmapNodeExtraction:
    """Tests for SVG node extraction"""

    def test_extract_nodes_from_real_svg(self):
        """Test extraction from real NotebookLM SVG"""
        extractor = MindmapExtractor(MockClient())
        nodes = extractor._extract_nodes_from_svg(REAL_MINDMAP_SVG)

        # Should find 6 nodes
        assert len(nodes) == 6, f"Expected 6 nodes, got {len(nodes)}"

        # Check root node
        root = nodes[0]
        assert root.text == "Private & Corporate LLM Masterclass"
        assert root.x == 0
        assert root.y == 0
        assert root.level == 0

        # Check child nodes
        child_texts = [n.text for n in nodes[1:]]
        assert "Einführung & Notwendigkeit" in child_texts
        assert "Grundlagen & Definitionen" in child_texts
        assert "Technische Basis & Hardware" in child_texts
        assert "Praktische Use Cases" in child_texts
        assert "Geschäftliche Chancen" in child_texts

        # All children should be level 1
        for node in nodes[1:]:
            assert node.level == 1, f"Node {node.text} should be level 1, got {node.level}"

    def test_extract_nodes_html_entity_decoding(self):
        """Test that HTML entities are properly decoded"""
        extractor = MindmapExtractor(MockClient())
        nodes = extractor._extract_nodes_from_svg(REAL_MINDMAP_SVG)

        # Check HTML entity decoding
        root = nodes[0]
        assert "&amp;" not in root.text
        assert "&" in root.text  # "Private & Corporate"

        # Check children
        for node in nodes:
            assert "&amp;" not in node.text
            assert "&lt;" not in node.text
            assert "&gt;" not in node.text

    def test_extract_nodes_coordinates(self):
        """Test that coordinates are correctly extracted"""
        extractor = MindmapExtractor(MockClient())
        nodes = extractor._extract_nodes_from_svg(REAL_MINDMAP_SVG)

        # Root at x=0, y=0
        root = nodes[0]
        assert root.x == 0
        assert root.y == 0

        # Children at x~460
        for node in nodes[1:]:
            assert node.x is not None
            assert 450 < node.x < 470, f"Child x should be ~460, got {node.x}"

        # Check y-coordinates are distinct
        y_coords = [n.y for n in nodes[1:]]
        assert len(set(y_coords)) == len(y_coords), "Y-coordinates should be unique"

    def test_extract_nodes_empty_svg(self):
        """Test extraction from empty/invalid SVG"""
        extractor = MindmapExtractor(MockClient())

        nodes = extractor._extract_nodes_from_svg(None)
        assert nodes == []

        nodes = extractor._extract_nodes_from_svg("")
        assert nodes == []

        nodes = extractor._extract_nodes_from_svg("<svg></svg>")
        assert nodes == []


class TestMindmapHierarchy:
    """Tests for hierarchy building"""

    def test_build_hierarchy_from_nodes(self):
        """Test hierarchy building from extracted nodes"""
        extractor = MindmapExtractor(MockClient())
        nodes = extractor._extract_nodes_from_svg(REAL_MINDMAP_SVG)

        root = extractor._build_hierarchy(nodes, [])

        assert root is not None
        assert root.text == "Private & Corporate LLM Masterclass"
        assert len(root.children) == 5

        # Check children are properly linked
        child_texts = [c.text for c in root.children]
        assert "Einführung & Notwendigkeit" in child_texts
        assert "Praktische Use Cases" in child_texts

        # Check parent_id is set
        for child in root.children:
            assert child.parent_id == root.id

    def test_hierarchy_empty_nodes(self):
        """Test hierarchy building with empty nodes"""
        extractor = MindmapExtractor(MockClient())

        result = extractor._build_hierarchy([], [])
        assert result is None


class TestMindmapMarkdownExport:
    """Tests for markdown export"""

    def test_export_to_markdown(self):
        """Test markdown export"""
        extractor = MindmapExtractor(MockClient())
        nodes = extractor._extract_nodes_from_svg(REAL_MINDMAP_SVG)
        root = extractor._build_hierarchy(nodes, [])

        data = MindmapData(
            notebook_id="test-123",
            notebook_title="Test Mindmap",
            root_node=root,
            nodes=nodes
        )

        md = extractor.export_to_markdown(data)

        assert "# Test Mindmap - Mindmap" in md
        assert "Private & Corporate LLM Masterclass" in md
        assert "Einführung & Notwendigkeit" in md
        assert "- " in md  # Should have bullet points


class TestMindmapJSONExport:
    """Tests for JSON serialization"""

    def test_node_to_dict(self):
        """Test node serialization"""
        extractor = MindmapExtractor(MockClient())

        node = MindmapNode(
            id="node_0",
            text="Test Node",
            level=0,
            x=100,
            y=200
        )
        child = MindmapNode(
            id="node_1",
            text="Child Node",
            level=1,
            x=300,
            y=200,
            parent_id="node_0"
        )
        node.children.append(child)

        result = extractor._node_to_dict(node)

        assert result["id"] == "node_0"
        assert result["text"] == "Test Node"
        assert result["level"] == 0
        assert result["x"] == 100
        assert result["y"] == 200
        assert len(result["children"]) == 1
        assert result["children"][0]["text"] == "Child Node"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
