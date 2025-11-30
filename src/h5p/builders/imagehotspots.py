"""
H5P ImageHotspots Builder

Interactive image with clickable hotspots.
"""
from typing import Dict, Any

from .base import create_h5p_package, COMMON_DEPENDENCIES


def build_imagehotspots_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.ImageHotspots package.

    Args:
        data: Dict with keys:
            - title: Activity title
            - image_url: URL to the image
            - hotspots: List of hotspot dicts:
                - x: Percentage from left (0-100)
                - y: Percentage from top (0-100)
                - header: Hotspot popup header
                - content: Hotspot popup content
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package

    Raises:
        ValueError: If image_url is missing
    """
    image_url = data.get("image_url", "")
    if not image_url:
        raise ValueError("ImageHotspots requires image_url")

    hotspots = data.get("hotspots", [])
    h5p_hotspots = []

    for i, hs in enumerate(hotspots):
        h5p_hotspots.append({
            "position": {
                "x": hs.get("x", 50),
                "y": hs.get("y", 50)
            },
            "header": hs.get("header", f"Punkt {i+1}"),
            "content": [
                {
                    "library": "H5P.Text 1.1",
                    "params": {
                        "text": f"<p>{hs.get('content', '')}</p>"
                    },
                    "subContentId": f"hotspot-text-{i}"
                }
            ],
            "alwaysFullscreen": False,
            "iconType": "icon",
            "icon": "plus"
        })

    content_json = {
        "image": {
            "path": image_url,
            "mime": "image/jpeg",
            "copyright": {"license": "U"},
            "width": 1280,
            "height": 720
        },
        "hotspots": h5p_hotspots,
        "hotspotNumberLabel": "Hotspot #num",
        "closeButtonLabel": "Schließen",
        "iconType": "icon",
        "icon": "plus",
        "color": "#981d99"
    }

    h5p_json = {
        "title": data.get("title", "Interaktives Bild"),
        "language": "de",
        "mainLibrary": "H5P.ImageHotspots",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.ImageHotspots", "majorVersion": 1, "minorVersion": 10},
            COMMON_DEPENDENCIES["text"],
            COMMON_DEPENDENCIES["fontawesome"]
        ]
    }

    return create_h5p_package(content_json, h5p_json, output_path)
