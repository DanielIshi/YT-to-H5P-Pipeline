"""
H5P Column Builder

Kombiniert mehrere H5P Content-Types in einem vertikalen Layout.
Ein Column = Ein Moodle-Menüpunkt mit mehreren Aktivitäten.
"""
from typing import Dict, Any, List
import uuid

from .base import create_h5p_package, COMMON_DEPENDENCIES
from .accordion import build_accordion_params
from .blanks import build_blanks_params
from .dialogcards import build_dialogcards_params
from .dragtext import build_dragtext_params
from .multichoice import build_multichoice_params
from .summary import build_summary_params
from .truefalse import build_truefalse_params


# Library-Versionen für Column-Inhalte
COLUMN_CONTENT_LIBRARIES = {
    "dialogcards": "H5P.Dialogcards 1.9",
    "accordion": "H5P.Accordion 1.0",
    "multichoice": "H5P.MultiChoice 1.16",
    "truefalse": "H5P.TrueFalse 1.8",
    "blanks": "H5P.Blanks 1.14",
    "dragtext": "H5P.DragText 1.10",
    "summary": "H5P.Summary 1.10",
}

# Dependencies für jede Library
LIBRARY_DEPENDENCIES = {
    "dialogcards": [
        {"machineName": "H5P.Dialogcards", "majorVersion": 1, "minorVersion": 9},
        COMMON_DEPENDENCIES["joubelui"],
        COMMON_DEPENDENCIES["transition"],
        COMMON_DEPENDENCIES["fontawesome"],
    ],
    "accordion": [
        {"machineName": "H5P.Accordion", "majorVersion": 1, "minorVersion": 0},
        COMMON_DEPENDENCIES["advancedtext"],
    ],
    "multichoice": [
        {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 16},
        COMMON_DEPENDENCIES["joubelui"],
        COMMON_DEPENDENCIES["question"],
        COMMON_DEPENDENCIES["transition"],
        COMMON_DEPENDENCIES["fontawesome"],
    ],
    "truefalse": [
        {"machineName": "H5P.TrueFalse", "majorVersion": 1, "minorVersion": 8},
        COMMON_DEPENDENCIES["joubelui"],
        COMMON_DEPENDENCIES["question"],
        COMMON_DEPENDENCIES["transition"],
        COMMON_DEPENDENCIES["fonticons"],
        COMMON_DEPENDENCIES["fontawesome"],
    ],
    "blanks": [
        {"machineName": "H5P.Blanks", "majorVersion": 1, "minorVersion": 14},
        COMMON_DEPENDENCIES["joubelui"],
        COMMON_DEPENDENCIES["question"],
        COMMON_DEPENDENCIES["transition"],
        COMMON_DEPENDENCIES["textutilities"],
        COMMON_DEPENDENCIES["fonticons"],
        COMMON_DEPENDENCIES["fontawesome"],
    ],
    "dragtext": [
        {"machineName": "H5P.DragText", "majorVersion": 1, "minorVersion": 10},
        COMMON_DEPENDENCIES["joubelui"],
        COMMON_DEPENDENCIES["question"],
        COMMON_DEPENDENCIES["transition"],
        COMMON_DEPENDENCIES["jqueryui"],
        COMMON_DEPENDENCIES["fontawesome"],
    ],
    "summary": [
        {"machineName": "H5P.Summary", "majorVersion": 1, "minorVersion": 10},
        COMMON_DEPENDENCIES["joubelui"],
        COMMON_DEPENDENCIES["transition"],
        COMMON_DEPENDENCIES["fontawesome"],
    ],
}

# Map content types to their param builders (stage3 output -> H5P params)
CONTENT_PARAM_BUILDERS = {
    "accordion": lambda content, auto: build_accordion_params(content),
    "dialogcards": lambda content, auto: build_dialogcards_params(content),
    "multichoice": lambda content, auto: build_multichoice_params(content, auto_check=auto),
    "truefalse": lambda content, auto: build_truefalse_params(content, auto_check=auto),
    "blanks": lambda content, auto: build_blanks_params(content, auto_check=auto),
    "dragtext": lambda content, auto: build_dragtext_params(content),
    "summary": lambda content, auto: build_summary_params(content),
}

# Phase mapping to enforce alternation inside a Column
PHASE_BY_TYPE = {
    "dialogcards": "passive",
    "accordion": "passive",
    "multichoice": "active",
    "truefalse": "active",
    "blanks": "active",
    "dragtext": "active",
    "summary": "reflect",
}

SEPARATOR_HTML = '<hr style="margin:16px 0;border:0;border-top:2px solid #222;">'


def order_column_activities(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Alterniert Aktivitäten innerhalb einer Column: passiv -> aktiv -> passiv -> aktiv.
    Reflektions-Elemente (summary) werden ans Ende gestellt.
    Reihenfolge innerhalb jeder Gruppe bleibt stabil.
    """
    passive = [a for a in activities if PHASE_BY_TYPE.get(a.get("content_type", "").lower()) == "passive"]
    active = [a for a in activities if PHASE_BY_TYPE.get(a.get("content_type", "").lower()) == "active"]
    reflect = [a for a in activities if PHASE_BY_TYPE.get(a.get("content_type", "").lower()) == "reflect"]
    neutral = [a for a in activities if PHASE_BY_TYPE.get(a.get("content_type", "").lower()) is None]

    ordered: List[Dict[str, Any]] = []
    while passive or active:
        if passive:
            ordered.append(passive.pop(0))
        if active:
            ordered.append(active.pop(0))

    ordered.extend(passive)
    ordered.extend(active)
    ordered.extend(neutral)
    ordered.extend(reflect)

    return ordered


def build_separator_item(index: int, html: str = SEPARATOR_HTML) -> Dict[str, Any]:
    """Create a visual separator block using AdvancedText."""
    return {
        "content": {
            "library": "H5P.AdvancedText 1.1",
            "params": {"text": html},
            "subContentId": f"separator-{index}",
            "metadata": {
                "contentType": "H5P.AdvancedText",
                "license": "U",
                "title": f"Separator {index + 1}"
            }
        },
        "useSeparator": "auto"
    }


def build_column_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.Column package combining multiple content types.

    Args:
        data: Dict with keys:
            - title: Column title (displayed in Moodle)
            - activities: List of activity dicts, each with:
                - content_type: Type name (dialogcards, multichoice, etc.)
                - content: The content JSON for that type
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package
    """
    activities = order_column_activities(data.get("activities", []))
    if not activities:
        raise ValueError("Column requires at least one activity")

    # Build content array for Column
    column_content = []
    all_dependencies = set()

    # Always add Column library
    all_dependencies.add(("H5P.Column", 1, 16))

    for i, activity in enumerate(activities):
        content_type = activity.get("content_type", "").lower()
        content = activity.get("content", {})

        if content_type not in COLUMN_CONTENT_LIBRARIES:
            raise ValueError(f"Unsupported content type for Column: {content_type}")

        library = COLUMN_CONTENT_LIBRARIES[content_type]

        # Add dependencies for this content type
        for dep in LIBRARY_DEPENDENCIES.get(content_type, []):
            all_dependencies.add((
                dep["machineName"],
                dep["majorVersion"],
                dep["minorVersion"]
            ))

        # Create column content item
        column_content.append({
            "content": {
                "library": library,
                "params": content,
                "subContentId": str(uuid.uuid4()),
                "metadata": {
                    "contentType": library.split()[0],
                    "license": "U",
                    "title": activity.get("title", f"Activity {i+1}")
                }
            },
            "useSeparator": "auto"
        })

        # Optional visual separator between activities
        if i < len(activities) - 1:
            column_content.append(build_separator_item(i))
            all_dependencies.add((COMMON_DEPENDENCIES["advancedtext"]["machineName"],
                                  COMMON_DEPENDENCIES["advancedtext"]["majorVersion"],
                                  COMMON_DEPENDENCIES["advancedtext"]["minorVersion"]))

    # Build content.json for Column
    content_json = {
        "content": column_content
    }

    # Build h5p.json with all dependencies
    dependencies_list = [
        {"machineName": name, "majorVersion": major, "minorVersion": minor}
        for name, major, minor in sorted(all_dependencies)
    ]

    h5p_json = {
        "title": data.get("title", "Lernmodul"),
        "language": "de",
        "mainLibrary": "H5P.Column",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": dependencies_list
    }

    return create_h5p_package(content_json, h5p_json, output_path)


def prepare_activity_for_column(content_type: str, content: Dict[str, Any], auto_check: bool = False) -> Dict[str, Any]:
    """
    Bereitet eine Aktivität für die Einbettung in Column vor.

    Wendet ggf. autoCheck an und formatiert das content-Dict korrekt.

    Args:
        content_type: Der Content-Type (multichoice, truefalse, etc.)
        content: Das generierte Content-Dict von Stage 3
        auto_check: Ob autoCheck aktiviert werden soll

    Returns:
        Fertiges Activity-Dict für build_column_h5p
    """
    ct = content_type.lower()
    builder_fn = CONTENT_PARAM_BUILDERS.get(ct)
    if not builder_fn:
        raise ValueError(f"Unsupported content type for Column: {content_type}")

    prepared = builder_fn(dict(content), auto_check)

    title = (
        content.get("title")
        or content.get("question")
        or content.get("statement")
        or ct
    )

    return {
        "content_type": ct,
        "content": prepared,
        "title": title
    }
