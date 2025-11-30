"""
H5P Content Builders

Modular builders for each H5P content type.
Each builder creates a valid H5P package from structured data.
"""
from typing import Dict, Any, Callable

from .base import create_h5p_package, COMMON_DEPENDENCIES, get_base_h5p_json
from .multichoice import build_multichoice_h5p
from .truefalse import build_truefalse_h5p
from .blanks import build_blanks_h5p
from .dragtext import build_dragtext_h5p
from .summary import build_summary_h5p
from .dialogcards import build_dialogcards_h5p
from .accordion import build_accordion_h5p
from .interactivevideo import build_interactivevideo_h5p
from .imagehotspots import build_imagehotspots_h5p
from .column import build_column_h5p, prepare_activity_for_column


# Builder registry - maps content type names to builder functions
BUILDERS: Dict[str, Callable[[Dict[str, Any], str], str]] = {
    # MVP Content Types (7)
    "multichoice": build_multichoice_h5p,
    "truefalse": build_truefalse_h5p,
    "blanks": build_blanks_h5p,
    "dragtext": build_dragtext_h5p,
    "summary": build_summary_h5p,
    "dialogcards": build_dialogcards_h5p,
    "accordion": build_accordion_h5p,
    # Media Content Types (Post-MVP 1.2)
    "interactivevideo": build_interactivevideo_h5p,
    "imagehotspots": build_imagehotspots_h5p,
    # Container Types
    "column": build_column_h5p,
    # Aliases for legacy compatibility
    "draganddrop": build_dragtext_h5p,  # Legacy name
}


def get_builder(content_type: str) -> Callable[[Dict[str, Any], str], str]:
    """
    Get the builder function for a content type.

    Args:
        content_type: Name of the content type (case-insensitive)

    Returns:
        Builder function that takes (data, output_path) and returns path

    Raises:
        ValueError: If content type is not supported
    """
    ct_lower = content_type.lower()
    if ct_lower not in BUILDERS:
        available = ", ".join(sorted(BUILDERS.keys()))
        raise ValueError(f"Unknown content type '{content_type}'. Available: {available}")
    return BUILDERS[ct_lower]


def build_h5p(content_type: str, data: Dict[str, Any], output_path: str) -> str:
    """
    Build an H5P package for any supported content type.

    Args:
        content_type: Name of the content type
        data: Content data dict (type-specific fields)
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package
    """
    builder = get_builder(content_type)
    return builder(data, output_path)


__all__ = [
    # Main API
    "BUILDERS",
    "get_builder",
    "build_h5p",
    # Individual builders
    "build_multichoice_h5p",
    "build_truefalse_h5p",
    "build_blanks_h5p",
    "build_dragtext_h5p",
    "build_summary_h5p",
    "build_dialogcards_h5p",
    "build_accordion_h5p",
    "build_interactivevideo_h5p",
    "build_imagehotspots_h5p",
    # Container builders
    "build_column_h5p",
    "prepare_activity_for_column",
    # Utilities
    "create_h5p_package",
    "COMMON_DEPENDENCIES",
    "get_base_h5p_json",
]
