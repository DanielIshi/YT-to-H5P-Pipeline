
import asyncio
import os
import wave
import struct
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock

from src.adapters.notebooklm.mindmap_animator import MindmapAnimator, AnimationTimeline, AnimationStep, AudioSegment
from src.adapters.notebooklm.mindmap_extractor import MindmapData, MindmapNode
from src.adapters.notebooklm.client import NotebookLMClient
from src.adapters.notebooklm.config import NotebookLMConfig

# Helper function to create a dummy WAV file
def create_dummy_wav(path: Path, duration: int = 5, sample_rate: int = 44100):
    """Creates a silent WAV file."""
    with wave.open(str(path), 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for _ in range(sample_rate * duration):
            f.writeframes(struct.pack('<h', 0))

@pytest.fixture
def mock_client():
    """Fixture to create a mock NotebookLMClient."""
    mock = MagicMock(spec=NotebookLMClient)
    mock.config = NotebookLMConfig()
    mock.get_current_url = MagicMock(return_value="about:blank")
    return mock

@pytest.fixture
def sample_mindmap_data():
    """Fixture to create sample mindmap data."""
    root = MindmapNode(id="root", text="Root Node", children=[
        MindmapNode(id="child1", text="Child 1", children=[
            MindmapNode(id="child1_1", text="Sub-child 1.1")
        ]),
        MindmapNode(id="child2", text="Child 2"),
    ])
    return MindmapData(
        notebook_id="e2e_test_notebook",
        notebook_title="E2E Test Notebook",
        root_node=root,
        nodes=[root, root.children[0], root.children[0].children[0], root.children[1]]
    )

@pytest.fixture
def sample_audio_segments():
    """Fixture to create sample audio segments, as if from a transcriber."""
    return [
        AudioSegment(start_time=0.0, end_time=1.5, text="Root Node"),
        AudioSegment(start_time=1.5, end_time=3.0, text="Child 1"),
        AudioSegment(start_time=3.0, end_time=4.5, text="Sub-child 1.1"),
    ]

@pytest.fixture
def dummy_audio_file(tmp_path):
    """Fixture to create a dummy audio file for the test."""
    audio_path = tmp_path / "dummy_audio.wav"
    create_dummy_wav(audio_path, duration=5)
    return audio_path

@pytest.mark.asyncio
async def test_full_mindmap_animation_pipeline(
    mock_client,
    sample_mindmap_data,
    sample_audio_segments,
    dummy_audio_file,
    tmp_path
):
    """
    Test the full pipeline from audio to animated video.
    """
    # Arrange
    output_dir = tmp_path / "e2e_output"
    output_dir.mkdir()
    video_path = output_dir / "e2e_animation.mp4"

    # 1. Initialize Animator
    animator = MindmapAnimator(mock_client)
    
    # Mock the page interactions
    animator.page = AsyncMock()
    animator.page.query_selector = AsyncMock(return_value=AsyncMock())
    animator.page.query_selector_all = AsyncMock(return_value=[AsyncMock()])

    # 2. Create timeline from "transcript"
    timeline = animator.create_timeline_from_transcript(
        mindmap_data=sample_mindmap_data,
        audio_segments=sample_audio_segments
    )

    # Act
    # 3. Run the animation and recording
    result_path = await animator.animate(
        mindmap_data=sample_mindmap_data,
        timeline=timeline,
        record=True,
        output_path=video_path
    )

    # Assert
    assert result_path is not None
    assert result_path == video_path
    assert video_path.exists()
    assert video_path.stat().st_size > 0, "The generated video file should not be empty."

    # Verify that the timeline and frames were created
    timeline_files = list(video_path.parent.glob("timeline_*.json"))
    assert len(timeline_files) > 0

    frames_dir = video_path.parent / "frames"
    assert frames_dir.exists()
    frame_files = list(frames_dir.glob("frame_*.png"))
    assert len(frame_files) > 0, "Should have captured at least one frame."

if __name__ == "__main__":
    pytest.main([__file__])
