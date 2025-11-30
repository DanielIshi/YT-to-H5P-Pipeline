"""
NotebookLM Adapter - Browser automation for Google NotebookLM

Generates E-Learning content from text/documents:
- Audio Overviews (Podcast-style summaries)
- Mindmaps
- FAQs
- Study Guides
- Summaries
"""

from .client import NotebookLMClient
from .notebook_manager import NotebookManager
from .content_extractor import ContentExtractor
from .audio_downloader import AudioDownloader

__all__ = [
    "NotebookLMClient",
    "NotebookManager",
    "ContentExtractor",
    "AudioDownloader",
]
