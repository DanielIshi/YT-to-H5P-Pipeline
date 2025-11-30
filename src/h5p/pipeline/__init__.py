"""
3-Stufen H5P Generation Pipeline

Stufe 1: Transcript → Strukturiertes Skript (stage1_summarizer)
Stufe 2: Skript → Lernpfad-Plan (stage2_planner)
Stufe 3: Plan → H5P Content (stage3_generator)
"""

from .stage1_summarizer import summarize_transcript
from .stage2_planner import plan_learning_path
from .stage3_generator import generate_h5p_content

__all__ = [
    "summarize_transcript",
    "plan_learning_path",
    "generate_h5p_content",
]
