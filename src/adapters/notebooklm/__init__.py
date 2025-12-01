"""
NotebookLM Adapter - Browser automation for Google NotebookLM

Architecture: Trigger + Harvester Pattern
- NotebookTrigger: Creates notebook and triggers all 8 artifact generations
- NotebookHarvester: Downloads ready artifacts (Audio, Video, Mindmap, etc.)

Usage:
    # 1. Trigger all artifacts
    python -m src.adapters.notebooklm.notebook_trigger --url "https://notebooklm.google.com/notebook/ABC"

    # 2. Harvest ready artifacts (run after generation completes)
    python -m src.adapters.notebooklm.notebook_harvester --url "https://notebooklm.google.com/notebook/ABC"

Artifacts (8 types):
- Audio Overview (Podcast-style summary)
- Video Overview (AI-generated educational video)
- Mindmap (Visual concept map)
- Berichte (Reports/Summaries)
- Karteikarten (Flashcards)
- Quiz (Multiple choice questions)
- Infografik (Infographic)
- Präsentation (Presentation slides)
"""

from .client import NotebookLMClient
from .config import NotebookLMConfig, Selectors
from .notebook_trigger import NotebookTrigger, TriggerResult
from .notebook_harvester import NotebookHarvester, HarvestResult
from .mindmap_extractor import MindmapExtractor, MindmapData, MindmapNode
from .mindmap_animator import (
    MindmapAnimator,
    AudioTranscriber,
    AnimationTimeline,
    AnimationStep,
    AudioSegment,
)

__all__ = [
    "NotebookLMClient",
    "NotebookLMConfig",
    "Selectors",
    "NotebookTrigger",
    "TriggerResult",
    "NotebookHarvester",
    "HarvestResult",
    "MindmapExtractor",
    "MindmapData",
    "MindmapNode",
    "MindmapAnimator",
    "AudioTranscriber",
    "AnimationTimeline",
    "AnimationStep",
    "AudioSegment",
]
