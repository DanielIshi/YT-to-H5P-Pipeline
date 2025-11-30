
import asyncio
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock

from src.adapters.notebooklm.mindmap_animator import MindmapAnimator, AnimationTimeline, AnimationStep
from src.adapters.notebooklm.mindmap_extractor import MindmapData, MindmapNode
from src.adapters.notebooklm.client import NotebookLMClient
from src.adapters.notebooklm.config import NotebookLMConfig

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
        MindmapNode(id="child1", text="Child 1"),
        MindmapNode(id="child2", text="Child 2"),
    ])
    return MindmapData(
        notebook_id="test_notebook",
        notebook_title="Test Notebook",
        root_node=root,
        nodes=[root, root.children[0], root.children[1]]
    )

@pytest.fixture
def sample_timeline():
    """Fixture to create a sample animation timeline."""
    return AnimationTimeline(steps=[
        AnimationStep(timestamp=0.0, action="expand", node_id="root", node_text="Root Node", duration=1.0),
        AnimationStep(timestamp=1.0, action="expand", node_id="child1", node_text="Child 1", duration=1.0),
    ])

@pytest.mark.asyncio
async def test_animate_with_recording(mock_client, sample_mindmap_data, sample_timeline, tmp_path):
    """
    Test that the animate method creates a video file when record=True.
    """
    # Arrange
    output_dir = tmp_path / "videos"
    output_dir.mkdir()
    video_path = output_dir / "test_animation.mp4"

    animator = MindmapAnimator(mock_client)
    
    # Mock the page interactions
    animator.page = AsyncMock()
    animator.page.query_selector = AsyncMock(return_value=AsyncMock())
    animator.page.query_selector_all = AsyncMock(return_value=[AsyncMock()])


    # Act
    result_path = await animator.animate(
        mindmap_data=sample_mindmap_data,
        timeline=sample_timeline,
        record=True,
        output_path=video_path
    )

    # Assert
    assert result_path is not None
    assert result_path == video_path
    
    # Check that the video file was created (or at least attempted to be created)
    # The actual video creation depends on opencv and ffmpeg, so we check for the timeline file
    # which is created by the recorder.
    timeline_files = list(video_path.parent.glob("timeline_*.json"))
    assert len(timeline_files) > 0

    # Also check for frames
    frames_dir = video_path.parent / "frames"
    assert frames_dir.exists()
    frame_files = list(frames_dir.glob("frame_*.png"))
    assert len(frame_files) > 0


if __name__ == "__main__":
    pytest.main([__file__])
