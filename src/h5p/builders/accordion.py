"""
H5P Accordion Builder

Collapsible panels for structured explanations.
"""
from typing import Dict, Any

from .base import create_h5p_package, COMMON_DEPENDENCIES


def build_accordion_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.Accordion package.

    Args:
        data: Dict with keys:
            - title: Activity title
            - panels: List of {title, content} dicts
                - title: Panel header
                - content: Panel content (can be HTML)
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package
    """
    panels = data.get("panels", [])
    accordion_panels = []

    for i, panel in enumerate(panels):
        accordion_panels.append({
            "title": panel.get("title", "Titel"),
            "content": {
                "params": {
                    "text": panel.get("content", "<p>Inhalt</p>")
                },
                "library": "H5P.AdvancedText 1.1",
                "subContentId": f"panel-{i}"
            }
        })

    content_json = {
        "panels": accordion_panels,
        "hTag": "h2"
    }

    h5p_json = {
        "title": data.get("title", "Accordion"),
        "language": "de",
        "mainLibrary": "H5P.Accordion",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.Accordion", "majorVersion": 1, "minorVersion": 0},
            COMMON_DEPENDENCIES["advancedtext"]
        ]
    }

    return create_h5p_package(content_json, h5p_json, output_path)
