"""
H5P Dialogcards Builder

Flashcards for terms and definitions.
"""
from typing import Dict, Any

from .base import create_h5p_package, COMMON_DEPENDENCIES


def build_dialogcards_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.Dialogcards package (Flashcards).

    Args:
        data: Dict with keys:
            - title: Activity title
            - cards: List of {front, back} dicts
                - front: Front side text (term/question)
                - back: Back side text (definition/answer)
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package
    """
    cards = data.get("cards", [])
    dialogs = []

    for card in cards:
        dialogs.append({
            "text": f"<p>{card.get('front', 'Vorderseite')}</p>",
            "answer": f"<p>{card.get('back', 'Rückseite')}</p>"
        })

    content_json = {
        "dialogs": dialogs,
        "behaviour": {
            "enableRetry": True,
            "disableBackwardsNavigation": False,
            "scaleTextNotCard": False,
            "randomCards": False,
            "maxProficiency": 5,
            "quickProgression": False
        },
        "title": data.get("title", "Karteikarten"),
        "description": "Klicke auf die Karte um die Antwort zu sehen.",
        "prev": "Zurück",
        "next": "Weiter",
        "retry": "Wiederholen",
        "correctAnswer": "Ich wusste es!",
        "incorrectAnswer": "Ich wusste es nicht",
        "round": "Runde @round",
        "cardsLeft": "Karten übrig: @number",
        "nextRound": "Nächste Runde",
        "startOver": "Von vorne",
        "showSummary": "Nächste Runde",
        "summary": "Zusammenfassung",
        "summaryCardsRight": "Karten gewusst:",
        "summaryCardsWrong": "Karten nicht gewusst:",
        "summaryCardsNotShown": "Karten nicht gesehen:",
        "summaryOverallScore": "Gesamtpunktzahl",
        "summaryCardsCompleted": "Abgeschlossene Karten:",
        "summaryCompletedRounds": "Abgeschlossene Runden:",
        "summaryAllDone": "Gut gemacht! Du hast alle Karten @cards mal richtig beantwortet!",
        "progressText": "Karte @card von @total",
        "cardFrontLabel": "Kartenvorderseite",
        "cardBackLabel": "Kartenrückseite",
        "tipButtonLabel": "Tipp anzeigen",
        "audioNotSupported": "Dein Browser unterstützt kein Audio.",
        "confirmStartingOver": {
            "header": "Von vorne beginnen?",
            "body": "Dein Fortschritt wird zurückgesetzt.",
            "cancelLabel": "Abbrechen",
            "confirmLabel": "Von vorne"
        }
    }

    h5p_json = {
        "title": data.get("title", "Karteikarten"),
        "language": "de",
        "mainLibrary": "H5P.Dialogcards",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.Dialogcards", "majorVersion": 1, "minorVersion": 9},
            COMMON_DEPENDENCIES["joubelui"],
            COMMON_DEPENDENCIES["transition"],
            COMMON_DEPENDENCIES["fontawesome"]
        ]
    }

    return create_h5p_package(content_json, h5p_json, output_path)
