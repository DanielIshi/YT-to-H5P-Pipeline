"""
H5P Blanks Builder

Fill in the blanks text exercise.
"""
from typing import Dict, Any

from .base import create_h5p_package, COMMON_DEPENDENCIES


def build_blanks_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.Blanks package (Fill in the blanks).

    WICHTIG: H5P.Blanks erwartet:
    - "questions": Liste von HTML-Strings mit *Lücken* (NICHT "text"!)
    - "text": Optionale Aufgabenbeschreibung

    Args:
        data: Dict with keys:
            - title: Activity title
            - text: Text with *blanks* marked by asterisks (can be string or list)
            - description: Optional task description
            - auto_check: Optional bool - auto-check on input (no submit button)
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package
    """
    # Get the text with blanks - can be single string or list
    text_input = data.get("text", "Das *Wort* fehlt.")

    # Convert to questions list (H5P.Blanks requires "questions" as a list!)
    if isinstance(text_input, list):
        questions = [f"<p>{t}</p>\n" if not t.startswith("<p>") else t for t in text_input]
    else:
        # Single text becomes single-item list
        questions = [f"<p>{text_input}</p>\n"]

    # Auto-check: sofortige Prüfung ohne Submit-Button
    auto_check = data.get("auto_check", False)

    content_json = {
        # "questions" ist das Hauptfeld für den Lückentext (NICHT "text"!)
        "questions": questions,
        # "text" ist nur die optionale Aufgabenbeschreibung
        "text": f"<p>{data.get('description', 'Fülle die Lücken aus.')}</p>\n",
        "overallFeedback": [{"from": 0, "to": 100, "feedback": "Gut gemacht!"}],
        "showSolutions": "Lösung anzeigen",
        "tryAgain": "Wiederholen",
        "checkAnswer": "Überprüfen",
        "submitAnswer": "Absenden",
        "notFilledOut": "Bitte fülle alle Lücken aus.",
        "answerIsCorrect": "':ans' ist korrekt",
        "answerIsWrong": "':ans' ist falsch",
        "answeredCorrectly": "Korrekt beantwortet",
        "answeredIncorrectly": "Falsch beantwortet",
        "solutionLabel": "Korrekte Antwort:",
        "inputLabel": "Lücke @num von @total",
        "inputHasTipLabel": "Tipp verfügbar",
        "tipLabel": "Tipp anzeigen",
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "enableCheckButton": not auto_check,  # Hide if auto_check
            "autoCheck": auto_check,  # Enable auto-check
            "caseSensitive": False,
            "showSolutionsRequiresInput": True,
            "separateLines": False,
            "confirmCheckDialog": False,
            "confirmRetryDialog": False,
            "acceptSpellingErrors": False
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
        },
        "scoreBarLabel": "Du hast :num von :total Punkten erreicht.",
        "a11yCheck": "Überprüfen",
        "a11yShowSolution": "Lösung anzeigen",
        "a11yRetry": "Wiederholen",
        "a11yCheckingModeHeader": "Überprüfungsmodus"
    }

    h5p_json = {
        "title": data.get("title", "Lückentext"),
        "language": "de",
        "mainLibrary": "H5P.Blanks",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.Blanks", "majorVersion": 1, "minorVersion": 14},
            COMMON_DEPENDENCIES["joubelui"],
            COMMON_DEPENDENCIES["question"],
            COMMON_DEPENDENCIES["transition"],
            COMMON_DEPENDENCIES["textutilities"],
            COMMON_DEPENDENCIES["fonticons"],
            COMMON_DEPENDENCIES["fontawesome"]
        ]
    }

    return create_h5p_package(content_json, h5p_json, output_path)
