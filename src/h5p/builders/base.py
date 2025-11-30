"""
Base H5P Builder Utilities

Shared helper functions for all H5P content type builders.
"""
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any


def create_h5p_package(content_json: Dict[str, Any], h5p_json: Dict[str, Any], output_path: str) -> str:
    """
    Create H5P ZIP package from content and manifest.

    Args:
        content_json: The content.json data for the H5P package
        h5p_json: The h5p.json manifest data
        output_path: Path where the .h5p file should be saved

    Returns:
        Path to the created H5P package
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        content_dir = tmppath / "content"
        content_dir.mkdir()

        # Write content.json
        with open(content_dir / "content.json", "w", encoding="utf-8") as f:
            json.dump(content_json, f, ensure_ascii=False, indent=2)

        # Write h5p.json manifest
        with open(tmppath / "h5p.json", "w", encoding="utf-8") as f:
            json.dump(h5p_json, f, ensure_ascii=False, indent=2)

        # Create ZIP package
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmppath / "h5p.json", "h5p.json")
            zf.write(content_dir / "content.json", "content/content.json")

    return output_path


# Common H5P dependencies used by multiple content types
COMMON_DEPENDENCIES = {
    "joubelui": {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
    "question": {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
    "transition": {"machineName": "H5P.Transition", "majorVersion": 1, "minorVersion": 0},
    "fonticons": {"machineName": "H5P.FontIcons", "majorVersion": 1, "minorVersion": 0},
    "fontawesome": {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5},
    "textutilities": {"machineName": "H5P.TextUtilities", "majorVersion": 1, "minorVersion": 3},
    "jqueryui": {"machineName": "jQuery.ui", "majorVersion": 1, "minorVersion": 10},
    "advancedtext": {"machineName": "H5P.AdvancedText", "majorVersion": 1, "minorVersion": 1},
    "text": {"machineName": "H5P.Text", "majorVersion": 1, "minorVersion": 1},
}


def get_base_h5p_json(title: str, main_library: str, dependencies: list) -> Dict[str, Any]:
    """
    Create base h5p.json manifest structure.

    Args:
        title: Title of the H5P content
        main_library: Main library machine name (e.g., "H5P.MultiChoice")
        dependencies: List of dependency dicts

    Returns:
        h5p.json manifest dict
    """
    return {
        "title": title,
        "language": "de",
        "mainLibrary": main_library,
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": dependencies
    }
