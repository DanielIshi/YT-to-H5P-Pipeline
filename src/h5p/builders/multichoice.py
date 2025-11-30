"""
H5P MultiChoice Builder

Multiple choice quiz with single correct answer.
"""
from typing import Dict, Any

from .base import create_h5p_package, COMMON_DEPENDENCIES


def build_multichoice_params(data: Dict[str, Any], auto_check: bool | None = None) -> Dict[str, Any]:
    """
    Transform stage3 output into H5P.MultiChoice params (content.json payload).

    Args:
        data: Dict with keys:
            - question: The question text
            - answers: List of {text, correct, feedback}
            - auto_check: Optional bool - auto-check on selection (no submit button)
        auto_check: Optional override for auto-check behaviour
    """
    answers = []
    for answer in data.get("answers", []):
        answers.append({
            "text": f"<div>{answer['text']}</div>",
            "correct": answer.get("correct", False),
            "tpiSpecific": {
                "choosenFeedback": f"<div>{answer.get('feedback', '')}</div>"
            }
        })

    # Default: auto-check enabled to avoid extra clicks unless explicitly disabled
    auto = data.get("auto_check", True) if auto_check is None else auto_check

    return {
        "question": f"<p>{data.get('question', 'Frage?')}</p>",
        "answers": answers,
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "enableCheckButton": not auto,  # Hide if auto_check
            "autoCheck": auto,  # Enable auto-check
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
    content_json = build_multichoice_params(data)

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
