"""
NotebookLM Adapter - Browser automation for Google NotebookLM

Generates E-Learning content from text/documents:
- Audio Overviews (Podcast-style summaries)
- Video Overviews (AI-generated educational videos)
- Mindmaps (SVG + JSON structure)
- Mindmap Animations (synced with audio)
- FAQs
- Study Guides
- Briefing Documents
- Summaries
"""

from .client import NotebookLMClient
from .notebook_manager import NotebookManager
from .content_extractor import ContentExtractor
from .audio_downloader import AudioDownloader
from .video_downloader import VideoDownloader, VideoFormat, VideoStyle
from .mindmap_extractor import MindmapExtractor, MindmapData, MindmapNode
from .mindmap_animator import (
    MindmapAnimator,
    AnimationTimeline,
    AnimationStep,
    AudioSegment,
    AudioTranscriber,
)

__all__ = [
    "NotebookLMClient",
    "NotebookManager",
    "ContentExtractor",
    "AudioDownloader",
    "VideoDownloader",
    "VideoFormat",
    "VideoStyle",
    "MindmapExtractor",
    "MindmapData",
    "MindmapNode",
    "MindmapAnimator",
    "AnimationTimeline",
    "AnimationStep",
    "AudioSegment",
    "AudioTranscriber",
]
