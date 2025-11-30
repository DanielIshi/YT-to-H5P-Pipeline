"""
H5P TrueFalse Builder

True/False statement for quick fact checking.
"""
from typing import Dict, Any

from .base import create_h5p_package, COMMON_DEPENDENCIES


def build_truefalse_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.TrueFalse package.

    WICHTIG: H5P.TrueFalse erwartet:
    - "question": HTML-String mit der Aussage
    - "correct": "true" oder "false" als STRING (nicht boolean!)
    - Vollständige l10n mit a11y-Feldern

    Args:
        data: Dict with keys:
            - title: Activity title
            - statement: The statement to evaluate
            - correct: Boolean - true if statement is correct
            - feedback_correct: Feedback for correct answer
            - feedback_wrong: Feedback for wrong answer
            - auto_check: Optional bool - auto-check on selection (no submit button)
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package
    """
    # Auto-check: sofortige Prüfung ohne Submit-Button
    auto_check = data.get("auto_check", False)

    content_json = {
        "question": f"<p>{data.get('statement', 'Aussage')}</p>",
        "correct": "true" if data.get("correct", True) else "false",
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "enableCheckButton": not auto_check,  # Hide if auto_check
            "confirmCheckDialog": False,
            "confirmRetryDialog": False,
            "autoCheck": auto_check  # Enable auto-check
        },
        "l10n": {
            "trueText": "Wahr",
            "falseText": "Falsch",
            "checkAnswer": "Überprüfen",
            "submitAnswer": "Absenden",
            "showSolutionButton": "Lösung anzeigen",
            "tryAgain": "Wiederholen",
            "score": "Du hast @score von @total Punkten.",
            "wrongAnswerMessage": data.get("feedback_wrong", "Das ist leider falsch."),
            "correctAnswerMessage": data.get("feedback_correct", "Das ist richtig!"),
            "scoreBarLabel": "Du hast :num von :total Punkten erreicht.",
            "a11yCheck": "Überprüfe die Antworten. Die Antworten werden als richtig, falsch oder unbeantwortet markiert.",
            "a11yShowSolution": "Zeige die Lösung. Die Aufgabe wird mit der korrekten Lösung markiert.",
            "a11yRetry": "Wiederhole die Aufgabe. Setze alle Antworten zurück und beginne von vorne."
        },
        "confirmCheck": {
            "header": "Beenden?",
            "body": "Bist du sicher?",
            "cancelLabel": "Abbrechen",
            "confirmLabel": "Beenden"
        },
        "confirmRetry": {
            "header": "Wiederholen?",
            "body": "Bist du sicher?",
            "cancelLabel": "Abbrechen",
            "confirmLabel": "Bestätigen"
        }
    }

    h5p_json = {
        "title": data.get("title", "Wahr oder Falsch"),
        "language": "de",
        "mainLibrary": "H5P.TrueFalse",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.TrueFalse", "majorVersion": 1, "minorVersion": 8},
            COMMON_DEPENDENCIES["joubelui"],
            COMMON_DEPENDENCIES["question"],
            COMMON_DEPENDENCIES["transition"],
            COMMON_DEPENDENCIES["fonticons"],
            COMMON_DEPENDENCIES["fontawesome"]
        ]
    }

    return create_h5p_package(content_json, h5p_json, output_path)
