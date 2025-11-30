"""
H5P MultiChoice Builder

Multiple choice quiz with single correct answer.
"""
from typing import Dict, Any

from .base import create_h5p_package, COMMON_DEPENDENCIES


def build_multichoice_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.MultiChoice package.

    Args:
        data: Dict with keys:
            - title: Quiz title
            - question: The question text
            - answers: List of {text, correct, feedback}
            - auto_check: Optional bool - auto-check on selection (no submit button)
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package
    """
    answers = []
    for a in data.get("answers", []):
        answers.append({
            "text": f"<div>{a['text']}</div>",
            "correct": a.get("correct", False),
            "tpiSpecific": {
                "choosenFeedback": f"<div>{a.get('feedback', '')}</div>"
            }
        })

    # Auto-check: sofortige Prüfung ohne Submit-Button
    auto_check = data.get("auto_check", False)

    content_json = {
        "question": f"<p>{data.get('question', 'Frage?')}</p>",
        "answers": answers,
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "enableCheckButton": not auto_check,  # Hide if auto_check
            "autoCheck": auto_check,  # Enable auto-check
            "randomAnswers": True,
            "singlePoint": False,
            "showSolutionsRequiresInput": True,
            "confirmCheckDialog": False,
            "passPercentage": 100
        },
        "UI": {
            "checkAnswerButton": "Überprüfen",
            "showSolutionButton": "Lösung anzeigen",
            "tryAgainButton": "Wiederholen"
        },
        "singleAnswer": True
    }

    h5p_json = {
        "title": data.get("title", "Quiz"),
        "language": "de",
        "mainLibrary": "H5P.MultiChoice",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 16},
            COMMON_DEPENDENCIES["joubelui"],
            COMMON_DEPENDENCIES["question"],
            COMMON_DEPENDENCIES["transition"],
            COMMON_DEPENDENCIES["fontawesome"]
        ]
    }

    return create_h5p_package(content_json, h5p_json, output_path)
