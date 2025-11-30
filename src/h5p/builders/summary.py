"""
H5P Summary Builder

Summary with statement selection for reflection.
"""
import uuid
from typing import Dict, Any

from .base import create_h5p_package, COMMON_DEPENDENCIES


def build_summary_params(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform stage3 output into H5P.Summary params (content.json payload)."""
    statements = data.get("statements", [])
    summary_items = []

    for stmt in statements:
        correct = stmt.get("correct", "Korrekte Aussage")
        wrong_list = stmt.get("wrong", ["Falsche Alternative"])

        options = [f"<p>{correct}</p>\n"]
        options.extend([f"<p>{w}</p>\n" for w in wrong_list])

        summary_items.append({
            "summary": options,
            "tip": stmt.get("tip", ""),
            "subContentId": str(uuid.uuid4())
        })

    return {
        "intro": data.get("intro", "Wähle die korrekten Aussagen:"),
        "summaries": summary_items,
        "solvedLabel": "Fortschritt:",
        "scoreLabel": "Falsche Versuche:",
        "resultLabel": "Dein Ergebnis",
        "labelCorrect": "Richtig!",
        "labelIncorrect": "Falsch! Versuche es nochmal.",
        "alternativeIncorrectLabel": "Falsch",
        "labelCorrectAnswers": "Korrekte Antworten.",
        "tipButtonLabel": "Tipp anzeigen",
        "scoreBarLabel": "Du hast @score von @total Punkten.",
        "progressText": "Fortschritt @progress von @total",
        "behaviour": {
            "enableRetry": True
        },
        "overallFeedback": [{"from": 0, "to": 100, "feedback": "Gut gemacht!"}]
    }


def build_summary_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.Summary package.

    WICHTIG: H5P.Summary erwartet:
    - summaries[].summary: Liste von HTML-Strings (erster ist korrekt!)
    - summaries[].tip: Optionaler Tipp-String
    - summaries[].subContentId: UUID für jeden Summary-Block

    Args:
        data: Dict with keys:
            - title: Activity title
            - intro: Introduction text
            - statements: List of {correct, wrong} dicts
                - correct: The correct statement (string)
                - wrong: List of wrong statements (strings)
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package
    """
    content_json = build_summary_params(data)

    h5p_json = {
        "title": data.get("title", "Zusammenfassung"),
        "language": "de",
        "mainLibrary": "H5P.Summary",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.Summary", "majorVersion": 1, "minorVersion": 10},
            COMMON_DEPENDENCIES["joubelui"],
            COMMON_DEPENDENCIES["question"],
            COMMON_DEPENDENCIES["transition"],
            COMMON_DEPENDENCIES["fonticons"],
            COMMON_DEPENDENCIES["fontawesome"]
        ]
    }

    return create_h5p_package(content_json, h5p_json, output_path)
