"""
Tests for Mindmap Animator

Tests timeline creation and keyword matching without browser.
"""

import pytest
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.notebooklm.mindmap_animator import (
    MindmapAnimator,
    AnimationTimeline,
    AnimationStep,
    AudioSegment,
)
from src.adapters.notebooklm.mindmap_extractor import MindmapData, MindmapNode


class MockClient:
    """Mock client for testing without browser"""
    class Config:
        video_dir = Path("output/test")

    config = Config()


def create_test_mindmap() -> MindmapData:
    """Create a test mindmap structure"""
    root = MindmapNode(
        id="node_0",
        text="Private & Corporate LLM Masterclass",
        level=0,
        x=0,
        y=0
    )

    children = [
        MindmapNode(id="node_1", text="Einführung & Notwendigkeit", level=1, x=460, y=-160),
        MindmapNode(id="node_2", text="Grundlagen & Definitionen", level=1, x=460, y=-80),
        MindmapNode(id="node_3", text="Technische Basis & Hardware", level=1, x=460, y=0),
        MindmapNode(id="node_4", text="Praktische Use Cases", level=1, x=460, y=80),
        MindmapNode(id="node_5", text="Geschäftliche Chancen", level=1, x=460, y=160),
    ]

    for child in children:
        child.parent_id = root.id
        root.children.append(child)

    return MindmapData(
        notebook_id="test-123",
        notebook_title="Test Mindmap",
        root_node=root,
        nodes=[root] + children
    )


class TestSequentialTimeline:
    """Tests for sequential timeline creation"""

    def test_create_sequential_timeline(self):
        """Test basic sequential timeline creation"""
        animator = MindmapAnimator(MockClient())
        mindmap = create_test_mindmap()

        timeline = animator.create_sequential_timeline(mindmap, pause_per_node=2.0)

        # Should have 6 steps (root + 5 children)
        assert len(timeline.steps) == 6

        # First step should be root
        assert timeline.steps[0].node_text == "Private & Corporate LLM Masterclass"
        assert timeline.steps[0].action == "expand"
        assert timeline.steps[0].timestamp == 0.0

        # Duration should be 6 * 2.0 = 12 seconds
        assert timeline.total_duration == 12.0

    def test_sequential_timeline_timestamps(self):
        """Test that timestamps are sequential"""
        animator = MindmapAnimator(MockClient())
        mindmap = create_test_mindmap()

        timeline = animator.create_sequential_timeline(mindmap, pause_per_node=3.0)

        # Check timestamps are sequential
        expected_times = [0.0, 3.0, 6.0, 9.0, 12.0, 15.0]
        for step, expected_time in zip(timeline.steps, expected_times):
            assert step.timestamp == expected_time

    def test_empty_mindmap(self):
        """Test timeline with empty mindmap"""
        animator = MindmapAnimator(MockClient())

        empty_mindmap = MindmapData(
            notebook_id="empty",
            notebook_title="Empty",
            root_node=None,
            nodes=[]
        )

        timeline = animator.create_sequential_timeline(empty_mindmap)
        assert len(timeline.steps) == 0
        assert timeline.total_duration == 0.0


class TestKeywordExtraction:
    """Tests for keyword extraction"""

    def test_extract_keywords_basic(self):
        """Test basic keyword extraction"""
        animator = MindmapAnimator(MockClient())

        keywords = animator._extract_keywords("Technische Basis und Hardware")

        assert "technische" in keywords
        assert "basis" in keywords
        assert "hardware" in keywords
        # "und" should be filtered as stop word
        assert "und" not in keywords

    def test_extract_keywords_english(self):
        """Test English keyword extraction"""
        animator = MindmapAnimator(MockClient())

        keywords = animator._extract_keywords("The quick brown fox and the lazy dog")

        assert "quick" in keywords
        assert "brown" in keywords
        assert "fox" in keywords
        # Stop words filtered
        assert "the" not in keywords
        assert "and" not in keywords

    def test_extract_keywords_empty(self):
        """Test empty string"""
        animator = MindmapAnimator(MockClient())

        assert animator._extract_keywords("") == []
        assert animator._extract_keywords(None) == []


class TestMatchScore:
    """Tests for keyword match scoring"""

    def test_perfect_match(self):
        """Test perfect keyword match"""
        animator = MindmapAnimator(MockClient())

        score = animator._calculate_match_score(
            ["hardware", "basis", "technische"],
            ["hardware", "basis", "technische"]
        )

        assert score == 1.0

    def test_partial_match(self):
        """Test partial keyword match"""
        animator = MindmapAnimator(MockClient())

        score = animator._calculate_match_score(
            ["hardware", "software", "system"],
            ["hardware", "basis", "technische"]
        )

        # 1 match (hardware) out of 5 unique words
        assert 0 < score < 1

    def test_no_match(self):
        """Test no keyword match"""
        animator = MindmapAnimator(MockClient())

        score = animator._calculate_match_score(
            ["apple", "banana", "cherry"],
            ["dog", "cat", "mouse"]
        )

        assert score == 0.0

    def test_empty_keywords(self):
        """Test empty keyword lists"""
        animator = MindmapAnimator(MockClient())

        assert animator._calculate_match_score([], ["word"]) == 0.0
        assert animator._calculate_match_score(["word"], []) == 0.0
        assert animator._calculate_match_score([], []) == 0.0


class TestTranscriptTimeline:
    """Tests for transcript-synced timeline"""

    def test_create_timeline_from_transcript(self):
        """Test timeline creation from audio segments"""
        animator = MindmapAnimator(MockClient())
        mindmap = create_test_mindmap()

        segments = [
            AudioSegment(
                start_time=0.0,
                end_time=5.0,
                text="Willkommen zur Einführung in Corporate LLMs"
            ),
            AudioSegment(
                start_time=5.0,
                end_time=10.0,
                text="Zuerst sprechen wir über die Notwendigkeit"
            ),
            AudioSegment(
                start_time=10.0,
                end_time=15.0,
                text="Dann schauen wir uns die Hardware und technische Basis an"
            ),
        ]

        timeline = animator.create_timeline_from_transcript(
            mindmap,
            segments,
            min_match_score=0.1  # Lower threshold for testing
        )

        # Should have some steps
        assert len(timeline.steps) > 0

        # Steps should have valid timestamps
        for step in timeline.steps:
            assert step.timestamp >= 0

    def test_empty_transcript(self):
        """Test with empty transcript"""
        animator = MindmapAnimator(MockClient())
        mindmap = create_test_mindmap()

        timeline = animator.create_timeline_from_transcript(mindmap, [])

        assert len(timeline.steps) == 0


class TestAnimationStep:
    """Tests for AnimationStep dataclass"""

    def test_animation_step_creation(self):
        """Test step creation"""
        step = AnimationStep(
            timestamp=5.0,
            action="expand",
            node_id="node_1",
            node_text="Test Node",
            duration=3.0
        )

        assert step.timestamp == 5.0
        assert step.action == "expand"
        assert step.node_id == "node_1"
        assert step.duration == 3.0


class TestAnimationTimeline:
    """Tests for AnimationTimeline dataclass"""

    def test_timeline_creation(self):
        """Test timeline creation"""
        timeline = AnimationTimeline()

        timeline.steps.append(AnimationStep(
            timestamp=0.0,
            action="expand",
            node_id="node_0",
            node_text="Root"
        ))

        timeline.total_duration = 3.0

        assert len(timeline.steps) == 1
        assert timeline.total_duration == 3.0
        assert timeline.created_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
