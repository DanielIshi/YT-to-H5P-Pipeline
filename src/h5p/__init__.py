"""
H5P Course Generation Service

This module provides tools to generate multimodal H5P courses from video content
using LLM-based content generation.
"""

# Legacy imports (for backward compatibility)
from .content_types import Answer, MultiChoiceContent, SlideElement, Slide, CoursePresentationContent
from .generator import H5PGenerator, generate_multichoice_h5p, generate_course_presentation_h5p

# New LLM-based course generation
from .course_schema import (
    CoursePresentation,
    CourseMetadata,
    MultiChoiceQuestion,
    TrueFalseQuestion,
    FillInBlanksQuestion,
    DragTextQuestion,
    TextContent,
    ImageContent,
    VideoContent,
    AccordionContent,
    DialogCardsContent,
    SummaryContent,
    LLM_SYSTEM_PROMPT,
    LLM_USER_PROMPT_TEMPLATE,
)
from .course_schema import Slide as CourseSlide  # Renamed to avoid conflict

from .package_builder import (
    H5PPackageBuilder,
    build_h5p_from_json,
)

__all__ = [
    # Legacy
    "Answer",
    "MultiChoiceContent",
    "SlideElement",
    "Slide",
    "CoursePresentationContent",
    "H5PGenerator",
    "generate_multichoice_h5p",
    "generate_course_presentation_h5p",
    # New schema classes
    "CoursePresentation",
    "CourseMetadata",
    "CourseSlide",
    "MultiChoiceQuestion",
    "TrueFalseQuestion",
    "FillInBlanksQuestion",
    "DragTextQuestion",
    "TextContent",
    "ImageContent",
    "VideoContent",
    "AccordionContent",
    "DialogCardsContent",
    "SummaryContent",
    # Prompts
    "LLM_SYSTEM_PROMPT",
    "LLM_USER_PROMPT_TEMPLATE",
    # Builder
    "H5PPackageBuilder",
    "build_h5p_from_json",
]
