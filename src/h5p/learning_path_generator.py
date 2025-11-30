#!/usr/bin/env python3
"""
Learning Path Generator: Creates diverse H5P activities for structured learning
Supports 9 Content Types: MultiChoice, TrueFalse, Blanks, Dialogcards, Accordion, Summary,
                          InteractiveVideo, ImageHotspots, DragAndDrop
"""
import json
import os
import sys
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional
import httpx

# ============================================================================
# LLM PROMPT - Generates complete learning path with all content types
# ============================================================================

LEARNING_PATH_PROMPT = """Du bist ein E-Learning Experte. Erstelle aus dem Video-Transkript einen
strukturierten Lernpfad mit verschiedenen H5P-Aktivitäten.

VERFÜGBARE CONTENT-TYPEN:
1. dialogcards - Karteikarten für Begriffe/Definitionen
2. accordion - Aufklappbare Sektionen für Erklärungen
3. multichoice - Multiple Choice Quiz
4. truefalse - Wahr/Falsch Aussagen
5. blanks - Lückentext zum Ausfüllen
6. summary - Zusammenfassung mit Aussagen-Auswahl
7. draganddrop - Begriffe in Kategorien ziehen
8. interactivevideo - YouTube-Video mit eingebetteten Quizfragen (NUR wenn video_url vorhanden!)
9. imagehotspots - Interaktives Bild mit klickbaren Hotspots (NUR wenn image_url vorhanden!)

OUTPUT FORMAT (JSON):
{
  "module_title": "Übergeordneter Modultitel",
  "activities": [
    {
      "order": 1,
      "type": "imagehotspots",
      "title": "1. Themenübersicht",
      "image_url": "{{IMAGE_URL}}",
      "hotspots": [
        {"x": 20, "y": 30, "header": "Thema A", "content": "Kurze Erklärung zu Thema A..."},
        {"x": 60, "y": 50, "header": "Thema B", "content": "Kurze Erklärung zu Thema B..."},
        {"x": 80, "y": 70, "header": "Thema C", "content": "Kurze Erklärung zu Thema C..."}
      ]
    },
    {
      "order": 2,
      "type": "dialogcards",
      "title": "2. Wichtige Begriffe",
      "cards": [
        {"front": "Begriff 1", "back": "Definition/Erklärung zu Begriff 1"},
        {"front": "Begriff 2", "back": "Definition/Erklärung zu Begriff 2"}
      ]
    },
    {
      "order": 3,
      "type": "accordion",
      "title": "3. Kernaussagen",
      "panels": [
        {"title": "Kernaussage 1", "content": "<p>Detaillierte Erklärung zur ersten Kernaussage...</p>"},
        {"title": "Kernaussage 2", "content": "<p>Detaillierte Erklärung zur zweiten Kernaussage...</p>"}
      ]
    },
    {
      "order": 4,
      "type": "interactivevideo",
      "title": "4. Video mit Quizfragen",
      "video_url": "{{VIDEO_URL}}",
      "interactions": [
        {
          "time": 60,
          "type": "multichoice",
          "label": "Verständnisfrage",
          "question": "Was wurde gerade erklärt?",
          "answers": [
            {"text": "Korrekte Antwort", "correct": true, "feedback": "Genau!"},
            {"text": "Falsche Option", "correct": false, "feedback": "Nicht ganz..."}
          ]
        },
        {
          "time": 180,
          "type": "truefalse",
          "label": "Faktencheck",
          "statement": "Diese Aussage ist korrekt.",
          "correct": true
        },
        {
          "time": 300,
          "type": "text",
          "label": "Wichtiger Hinweis",
          "text": "Achte auf diesen wichtigen Punkt..."
        }
      ]
    },
    {
      "order": 5,
      "type": "multichoice",
      "title": "5. Verständnischeck",
      "question": "Was ist die Hauptaussage des Videos?",
      "answers": [
        {"text": "Korrekte Antwort", "correct": true, "feedback": "Genau richtig!"},
        {"text": "Falsche Option A", "correct": false, "feedback": "Nicht ganz, weil..."},
        {"text": "Falsche Option B", "correct": false, "feedback": "Leider nein, denn..."},
        {"text": "Falsche Option C", "correct": false, "feedback": "Das stimmt nicht, weil..."}
      ]
    },
    {
      "order": 6,
      "type": "blanks",
      "title": "6. Lückentext",
      "text": "Das wichtigste Konzept ist *Antwort1*. Es wird verwendet für *Antwort2*."
    },
    {
      "order": 7,
      "type": "truefalse",
      "title": "7. Faktencheck",
      "statement": "Diese Aussage aus dem Video ist korrekt.",
      "correct": true,
      "feedback_correct": "Richtig! Diese Aussage stimmt weil...",
      "feedback_wrong": "Falsch! Diese Aussage ist korrekt weil..."
    },
    {
      "order": 8,
      "type": "draganddrop",
      "title": "8. Zuordnung",
      "task": "Ordne die Begriffe den richtigen Kategorien zu.",
      "categories": ["Kategorie A", "Kategorie B"],
      "items": [
        {"text": "Begriff 1", "category": 0},
        {"text": "Begriff 2", "category": 1},
        {"text": "Begriff 3", "category": 0}
      ]
    },
    {
      "order": 9,
      "type": "summary",
      "title": "9. Zusammenfassung",
      "intro": "Wähle die korrekten Aussagen:",
      "statements": [
        {
          "correct": "Die korrekte Zusammenfassung des ersten Punktes.",
          "wrong": ["Falsche Alternative A", "Falsche Alternative B"]
        },
        {
          "correct": "Die korrekte Zusammenfassung des zweiten Punktes.",
          "wrong": ["Falsche Alternative C", "Falsche Alternative D"]
        }
      ]
    }
  ]
}

REGELN:
- Erstelle 8-12 Aktivitäten in didaktischer Reihenfolge
- Beginne mit ImageHotspots als Themenübersicht (NUR wenn {{IMAGE_URL}} vorhanden)
- Dann passive Elemente (Dialogcards, Accordion) zur Wissensvermittlung
- InteractiveVideo in der Mitte platzieren (NUR wenn {{VIDEO_URL}} vorhanden)
- Dann aktive Elemente (MultiChoice, Blanks, TrueFalse, DragAndDrop) zur Überprüfung
- Ende mit Summary als Abschluss
- Nummeriere alle Titel (1., 2., 3., ...)
- Sprache: Deutsch
- Keine Emojis
- Bei blanks: Markiere Lücken mit *Antwort*
- Bei draganddrop: category ist der Index (0, 1, 2...)
- Bei interactivevideo: time in Sekunden, verteile 3-5 Interaktionen über das Video
- Bei imagehotspots: x/y sind Prozentwerte (0-100), verteile 3-5 Hotspots sinnvoll
- Verwende mindestens 5 verschiedene Content-Typen
- WICHTIG: Ersetze {{VIDEO_URL}} und {{IMAGE_URL}} durch die tatsächlichen URLs unten!

VIDEO-TRANSKRIPT:
"""


def call_openai_learning_path(transcript: str, title: str = "Lernmodul", video_url: str = "") -> Dict[str, Any]:
    """Call OpenAI API to generate complete learning path"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    # Truncate very long transcripts
    if len(transcript) > 18000:
        transcript = transcript[:18000] + "... [gekürzt]"

    # Build prompt with URL placeholders replaced
    prompt = LEARNING_PATH_PROMPT

    # Extract video ID and generate thumbnail URL
    image_url = ""
    if video_url:
        # Import here to avoid circular dependency issues
        import re
        video_id_match = re.search(
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            video_url
        )
        if video_id_match:
            video_id = video_id_match.group(1)
            image_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    # Replace placeholders or remove related examples if URLs not available
    if video_url:
        prompt = prompt.replace("{{VIDEO_URL}}", video_url)
    else:
        # Remove interactivevideo example if no video URL
        prompt = prompt.replace(
            '8. interactivevideo - YouTube-Video mit eingebetteten Quizfragen (NUR wenn video_url vorhanden!)',
            '8. interactivevideo - (NICHT VERWENDEN - keine video_url vorhanden)'
        )

    if image_url:
        prompt = prompt.replace("{{IMAGE_URL}}", image_url)
    else:
        # Remove imagehotspots example if no image URL
        prompt = prompt.replace(
            '9. imagehotspots - Interaktives Bild mit klickbaren Hotspots (NUR wenn image_url vorhanden!)',
            '9. imagehotspots - (NICHT VERWENDEN - keine image_url vorhanden)'
        )

    prompt = prompt + transcript

    # Add URL context at the end
    if video_url or image_url:
        prompt += f"\n\nVERFÜGBARE URLs:\n"
        if video_url:
            prompt += f"- VIDEO_URL: {video_url}\n"
        if image_url:
            prompt += f"- IMAGE_URL: {image_url}\n"

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Du antwortest ausschliesslich mit validem JSON."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 5000,  # Increased for more content types
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        },
        timeout=120.0  # Increased timeout for longer responses
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


# ============================================================================
# H5P BUILDER FUNCTIONS - One for each content type
# ============================================================================

def _create_h5p_package(content_json: Dict, h5p_json: Dict, output_path: str) -> str:
    """Helper to create H5P zip package"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        content_dir = tmppath / "content"
        content_dir.mkdir()

        with open(content_dir / "content.json", "w", encoding="utf-8") as f:
            json.dump(content_json, f, ensure_ascii=False, indent=2)

        with open(tmppath / "h5p.json", "w", encoding="utf-8") as f:
            json.dump(h5p_json, f, ensure_ascii=False, indent=2)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmppath / "h5p.json", "h5p.json")
            zf.write(content_dir / "content.json", "content/content.json")

    return output_path


def build_multichoice_h5p(data: Dict[str, Any], output_path: str) -> str:
    """Build H5P.MultiChoice package"""
    answers = []
    for a in data.get("answers", []):
        answers.append({
            "text": f"<div>{a['text']}</div>",
            "correct": a.get("correct", False),
            "tpiSpecific": {
                "choosenFeedback": f"<div>{a.get('feedback', '')}</div>"
            }
        })

    content_json = {
        "question": f"<p>{data.get('question', 'Frage?')}</p>",
        "answers": answers,
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "enableCheckButton": True,
            "randomAnswers": True,
            "singlePoint": False,
            "showSolutionsRequiresInput": True,
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
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.Transition", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }

    return _create_h5p_package(content_json, h5p_json, output_path)


def build_truefalse_h5p(data: Dict[str, Any], output_path: str) -> str:
    """Build H5P.TrueFalse package

    WICHTIG: H5P.TrueFalse erwartet:
    - "question": HTML-String mit der Aussage
    - "correct": "true" oder "false" als STRING (nicht boolean!)
    - Vollständige l10n mit a11y-Feldern
    """
    content_json = {
        "question": f"<p>{data.get('statement', 'Aussage')}</p>",
        "correct": "true" if data.get("correct", True) else "false",
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "enableCheckButton": True,
            "confirmCheckDialog": False,
            "confirmRetryDialog": False,
            "autoCheck": False
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
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.Transition", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "H5P.FontIcons", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }

    return _create_h5p_package(content_json, h5p_json, output_path)


def build_blanks_h5p(data: Dict[str, Any], output_path: str) -> str:
    """Build H5P.Blanks package (Fill in the blanks)

    WICHTIG: H5P.Blanks erwartet:
    - "questions": Liste von HTML-Strings mit *Lücken* (NICHT "text"!)
    - "text": Optionale Aufgabenbeschreibung
    """
    # Get the text with blanks - can be single string or list
    text_input = data.get("text", "Das *Wort* fehlt.")

    # Convert to questions list (H5P.Blanks requires "questions" as a list!)
    if isinstance(text_input, list):
        questions = [f"<p>{t}</p>\n" if not t.startswith("<p>") else t for t in text_input]
    else:
        # Single text becomes single-item list
        questions = [f"<p>{text_input}</p>\n"]

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
            "enableCheckButton": True,
            "autoCheck": False,
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
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.Transition", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "H5P.TextUtilities", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "H5P.FontIcons", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }

    return _create_h5p_package(content_json, h5p_json, output_path)


def build_dialogcards_h5p(data: Dict[str, Any], output_path: str) -> str:
    """Build H5P.Dialogcards package (Flashcards)"""
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
        "confirmStartingOver": {"header": "Von vorne beginnen?", "body": "Dein Fortschritt wird zurückgesetzt.", "cancelLabel": "Abbrechen", "confirmLabel": "Von vorne"}
    }

    h5p_json = {
        "title": data.get("title", "Karteikarten"),
        "language": "de",
        "mainLibrary": "H5P.Dialogcards",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.Dialogcards", "majorVersion": 1, "minorVersion": 9},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "H5P.Transition", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }

    return _create_h5p_package(content_json, h5p_json, output_path)


def build_accordion_h5p(data: Dict[str, Any], output_path: str) -> str:
    """Build H5P.Accordion package"""
    panels = data.get("panels", [])
    accordion_panels = []
    for panel in panels:
        accordion_panels.append({
            "title": panel.get("title", "Titel"),
            "content": {
                "params": {
                    "text": panel.get("content", "<p>Inhalt</p>")
                },
                "library": "H5P.AdvancedText 1.1",
                "subContentId": f"panel-{len(accordion_panels)}"
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
            {"machineName": "H5P.AdvancedText", "majorVersion": 1, "minorVersion": 1}
        ]
    }

    return _create_h5p_package(content_json, h5p_json, output_path)


def build_summary_h5p(data: Dict[str, Any], output_path: str) -> str:
    """Build H5P.Summary package

    WICHTIG: H5P.Summary erwartet:
    - summaries[].summary: Liste von HTML-Strings (erster ist korrekt!)
    - summaries[].tip: Optionaler Tipp-String
    - summaries[].subContentId: UUID für jeden Summary-Block
    """
    import uuid

    statements = data.get("statements", [])
    summary_items = []
    for i, stmt in enumerate(statements):
        # Each statement has one correct and multiple wrong options
        # First option MUST be the correct one!
        correct = stmt.get("correct", "Korrekte Aussage")
        wrong_list = stmt.get("wrong", ["Falsche Alternative"])

        # Format as HTML paragraphs
        options = [f"<p>{correct}</p>\n"]
        options.extend([f"<p>{w}</p>\n" for w in wrong_list])

        summary_items.append({
            "summary": options,
            "tip": stmt.get("tip", ""),
            "subContentId": str(uuid.uuid4())
        })

    content_json = {
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

    h5p_json = {
        "title": data.get("title", "Zusammenfassung"),
        "language": "de",
        "mainLibrary": "H5P.Summary",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.Summary", "majorVersion": 1, "minorVersion": 10},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.Transition", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "H5P.FontIcons", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }

    return _create_h5p_package(content_json, h5p_json, output_path)


def build_draganddrop_h5p(data: Dict[str, Any], output_path: str) -> str:
    """Build H5P.DragText package (simpler drag-and-drop for text)

    WICHTIG: H5P.DragText erwartet:
    - "taskDescription": Aufgabenbeschreibung (optional)
    - "textField": Der Text mit *Lücken* die gefüllt werden sollen
    - Vollständige a11y-Felder für Accessibility
    """
    # Convert to DragText format: "Drag the *word* to complete the sentence"
    categories = data.get("categories", ["Kategorie A", "Kategorie B"])
    items = data.get("items", [])

    # Build drag text with categories
    text_lines = []
    for i, cat in enumerate(categories):
        cat_items = [item["text"] for item in items if item.get("category", 0) == i]
        if cat_items:
            # Format: Category: *item1* *item2*
            items_str = " ".join([f"*{item}*" for item in cat_items])
            text_lines.append(f"{cat}: {items_str}")

    content_json = {
        "taskDescription": f"<p>{data.get('task', 'Ordne die Begriffe den richtigen Kategorien zu.')}</p>",
        "textField": "\n".join(text_lines),
        "distractors": "",
        "overallFeedback": [{"from": 0, "to": 100, "feedback": "Gut gemacht!"}],
        "checkAnswer": "Überprüfen",
        "submitAnswer": "Absenden",
        "tryAgain": "Wiederholen",
        "showSolution": "Lösung anzeigen",
        "dropZoneIndex": "Dropzone @index.",
        "empty": "Dropzone @index ist leer.",
        "contains": "Dropzone @index enthält @draggable.",
        "ariaDraggableIndex": "@index von @count Ziehbaren.",
        "tipLabel": "Tipp anzeigen",
        "correctText": "Richtig!",
        "incorrectText": "Falsch!",
        "resetDropTitle": "Dropzone zurücksetzen",
        "resetDropDescription": "Bist du sicher, dass du die Dropzone zurücksetzen möchtest?",
        "grabbed": "Ziehbar aufgenommen.",
        "cancelledDragging": "Ziehen abgebrochen.",
        "correctAnswer": "Korrekte Antwort:",
        "feedbackHeader": "Feedback",
        "scoreBarLabel": "Du hast @score von @total Punkten erreicht.",
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "enableCheckButton": True,
            "instantFeedback": False
        },
        "a11yCheck": "Überprüfe die Antworten. Die Antworten werden als richtig, falsch oder unbeantwortet markiert.",
        "a11yShowSolution": "Zeige die Lösung. Die Aufgabe wird mit der korrekten Lösung markiert.",
        "a11yRetry": "Wiederhole die Aufgabe. Setze alle Antworten zurück und beginne von vorne."
    }

    h5p_json = {
        "title": data.get("title", "Zuordnung"),
        "language": "de",
        "mainLibrary": "H5P.DragText",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.DragText", "majorVersion": 1, "minorVersion": 10},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.Transition", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "jQuery.ui", "majorVersion": 1, "minorVersion": 10},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }

    return _create_h5p_package(content_json, h5p_json, output_path)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL"""
    import re
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_timestamps_from_subtitles(subtitles: str) -> list:
    """
    Extract timestamps from YouTube subtitles.
    Supports formats:
    - "00:01:30 Text..." (YouTube auto-generated)
    - "[00:01:30] Text..." (bracketed)
    - "1:30 Text..." (short format)

    Returns list of (seconds, text) tuples
    """
    import re
    timestamps = []

    # Pattern for HH:MM:SS or MM:SS or M:SS
    patterns = [
        r'(?:\[)?(\d{1,2}):(\d{2}):(\d{2})(?:\])?\s*(.+?)(?=(?:\[)?\d{1,2}:\d{2}|\Z)',  # HH:MM:SS
        r'(?:\[)?(\d{1,2}):(\d{2})(?:\])?\s*(.+?)(?=(?:\[)?\d{1,2}:\d{2}|\Z)',  # MM:SS
    ]

    # Try HH:MM:SS format first
    matches = re.findall(r'(?:\[)?(\d{1,2}):(\d{2}):(\d{2})(?:\])?\s*([^\[\n]+)', subtitles)
    if matches:
        for h, m, s, text in matches:
            seconds = int(h) * 3600 + int(m) * 60 + int(s)
            timestamps.append((seconds, text.strip()))
    else:
        # Try MM:SS format
        matches = re.findall(r'(?:\[)?(\d{1,2}):(\d{2})(?:\])?\s*([^\[\n]+)', subtitles)
        for m, s, text in matches:
            seconds = int(m) * 60 + int(s)
            timestamps.append((seconds, text.strip()))

    return timestamps


def get_youtube_thumbnail(video_id: str) -> str:
    """Get YouTube thumbnail URL from video ID"""
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"


# ============================================================================
# INTERACTIVE VIDEO BUILDER
# ============================================================================

def build_interactive_video_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.InteractiveVideo package

    Expected data format:
    {
        "type": "interactivevideo",
        "title": "Video mit Quizfragen",
        "video_url": "https://www.youtube.com/watch?v=...",
        "interactions": [
            {
                "time": 30,  # seconds
                "type": "multichoice",
                "question": "Was wurde erklärt?",
                "answers": [
                    {"text": "Antwort A", "correct": true},
                    {"text": "Antwort B", "correct": false}
                ]
            },
            {
                "time": 120,
                "type": "truefalse",
                "statement": "Diese Aussage ist korrekt.",
                "correct": true
            },
            {
                "time": 180,
                "type": "text",
                "label": "Wichtiger Hinweis",
                "text": "Hier passiert etwas Wichtiges..."
            }
        ]
    }
    """
    video_url = data.get("video_url", "")
    if not video_url:
        raise ValueError("InteractiveVideo requires video_url")

    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from: {video_url}")

    interactions = data.get("interactions", [])
    h5p_interactions = []

    for i, interaction in enumerate(interactions):
        time_sec = interaction.get("time", 0)
        int_type = interaction.get("type", "text").lower()

        # Base interaction structure
        h5p_int = {
            "x": 45 + (i % 3) * 5,  # Slightly vary position
            "y": 40 + (i % 2) * 10,
            "width": 10,
            "height": 10,
            "duration": {
                "from": time_sec,
                "to": time_sec + 10  # Show for 10 seconds
            },
            "pause": True,  # Pause video when interaction appears
            "displayType": "poster",  # Show as overlay
            "label": f"<p>{interaction.get('label', f'Frage {i+1}')}</p>"
        }

        if int_type == "multichoice":
            answers = []
            for ans in interaction.get("answers", []):
                answers.append({
                    "text": f"<div>{ans.get('text', '')}</div>",
                    "correct": ans.get("correct", False),
                    "tipsAndFeedback": {
                        "chosenFeedback": f"<div>{ans.get('feedback', '')}</div>",
                        "notChosenFeedback": ""
                    }
                })

            h5p_int["action"] = {
                "library": "H5P.MultiChoice 1.16",
                "params": {
                    "question": f"<p>{interaction.get('question', 'Frage?')}</p>",
                    "answers": answers,
                    "behaviour": {
                        "enableRetry": True,
                        "enableSolutionsButton": True,
                        "singlePoint": True,
                        "randomAnswers": True
                    },
                    "UI": {
                        "checkAnswerButton": "Überprüfen",
                        "showSolutionButton": "Lösung anzeigen",
                        "tryAgainButton": "Wiederholen"
                    }
                },
                "subContentId": f"mc-{i}-{time_sec}"
            }

        elif int_type == "truefalse":
            h5p_int["action"] = {
                "library": "H5P.TrueFalse 1.8",
                "params": {
                    "question": f"<p>{interaction.get('statement', 'Aussage')}</p>",
                    "correct": "true" if interaction.get("correct", True) else "false",
                    "behaviour": {
                        "enableRetry": True,
                        "enableSolutionsButton": True
                    },
                    "l10n": {
                        "trueText": "Wahr",
                        "falseText": "Falsch",
                        "checkAnswer": "Überprüfen",
                        "showSolutionButton": "Lösung anzeigen",
                        "tryAgain": "Wiederholen"
                    }
                },
                "subContentId": f"tf-{i}-{time_sec}"
            }

        else:  # text/label
            h5p_int["action"] = {
                "library": "H5P.Text 1.1",
                "params": {
                    "text": f"<p><strong>{interaction.get('label', 'Info')}</strong></p><p>{interaction.get('text', '')}</p>"
                },
                "subContentId": f"txt-{i}-{time_sec}"
            }
            h5p_int["pause"] = False  # Don't pause for text

        h5p_interactions.append(h5p_int)

    content_json = {
        "interactiveVideo": {
            "video": {
                "startScreenOptions": {
                    "title": data.get("title", "Interaktives Video"),
                    "hideStartTitle": False
                },
                "textTracks": {
                    "videoTrack": []
                },
                "files": [
                    {
                        "path": f"https://www.youtube.com/watch?v={video_id}",
                        "mime": "video/YouTube",
                        "copyright": {"license": "U"}
                    }
                ]
            },
            "assets": {
                "interactions": h5p_interactions,
                "bookmarks": [],
                "endscreens": []
            },
            "summary": {
                "task": {
                    "library": "H5P.Summary 1.10",
                    "params": {
                        "intro": "Zusammenfassung",
                        "summaries": [],
                        "overallFeedback": [{"from": 0, "to": 100, "feedback": "Gut gemacht!"}]
                    }
                },
                "displayAt": 3
            }
        },
        "override": {
            "autoplay": False,
            "loop": False,
            "showBookmarksmenuOnLoad": False,
            "showRewind10": True,
            "preventSkipping": False,
            "deactivateSound": False
        },
        "l10n": {
            "interaction": "Interaktion",
            "play": "Abspielen",
            "pause": "Pause",
            "mute": "Stumm",
            "unmute": "Ton an",
            "quality": "Qualität",
            "captions": "Untertitel",
            "close": "Schließen",
            "fullscreen": "Vollbild",
            "exitFullscreen": "Vollbild beenden",
            "summary": "Zusammenfassung",
            "bookmarks": "Lesezeichen",
            "defaultAdaptivitySeekLabel": "Weiter",
            "continueWithVideo": "Video fortsetzen",
            "playbackRate": "Geschwindigkeit",
            "rewind10": "10 Sekunden zurück",
            "navDisabled": "Navigation deaktiviert",
            "sndDisabled": "Ton deaktiviert",
            "requiresCompletionWarning": "Du musst alle Interaktionen abschließen.",
            "back": "Zurück",
            "hours": "Stunden",
            "minutes": "Minuten",
            "seconds": "Sekunden",
            "currentTime": "Aktuelle Zeit:",
            "totalTime": "Gesamtzeit:",
            "singleInteractionAnnouncement": "Interaktion erschienen",
            "multipleInteractionsAnnouncement": "@count Interaktionen erschienen",
            "videoPausedAnnouncement": "Video pausiert",
            "content": "Inhalt"
        }
    }

    h5p_json = {
        "title": data.get("title", "Interaktives Video"),
        "language": "de",
        "mainLibrary": "H5P.InteractiveVideo",
        "embedTypes": ["iframe"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.InteractiveVideo", "majorVersion": 1, "minorVersion": 26},
            {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 16},
            {"machineName": "H5P.TrueFalse", "majorVersion": 1, "minorVersion": 8},
            {"machineName": "H5P.Text", "majorVersion": 1, "minorVersion": 1},
            {"machineName": "H5P.Summary", "majorVersion": 1, "minorVersion": 10},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.Video", "majorVersion": 1, "minorVersion": 6},
            {"machineName": "H5P.Transition", "majorVersion": 1, "minorVersion": 0},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }

    return _create_h5p_package(content_json, h5p_json, output_path)


# ============================================================================
# IMAGE HOTSPOTS BUILDER
# ============================================================================

def build_image_hotspots_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.ImageHotspots package

    Expected data format:
    {
        "type": "imagehotspots",
        "title": "Themen-Übersicht",
        "image_url": "https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg",
        "hotspots": [
            {
                "x": 25,  # percentage from left
                "y": 40,  # percentage from top
                "header": "Thema A",
                "content": "Erklärung zu Thema A..."
            },
            {
                "x": 70,
                "y": 60,
                "header": "Thema B",
                "content": "Erklärung zu Thema B..."
            }
        ]
    }
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
            {"machineName": "H5P.Text", "majorVersion": 1, "minorVersion": 1},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }

    return _create_h5p_package(content_json, h5p_json, output_path)


# ============================================================================
# DISPATCHER - Maps content type to builder function
# ============================================================================

BUILDERS = {
    "multichoice": build_multichoice_h5p,
    "truefalse": build_truefalse_h5p,
    "blanks": build_blanks_h5p,
    "dialogcards": build_dialogcards_h5p,
    "accordion": build_accordion_h5p,
    "summary": build_summary_h5p,
    "draganddrop": build_draganddrop_h5p,
    "interactivevideo": build_interactive_video_h5p,
    "imagehotspots": build_image_hotspots_h5p,
}


def import_h5p_to_moodle(h5p_path: str, courseid: int, title: str) -> Dict[str, Any]:
    """Import H5P to Moodle via PHP script"""
    subprocess.run(["docker", "cp", h5p_path, "moodle-app:/tmp/generated.h5p"],
                   check=True, capture_output=True)

    cmd = ["docker", "exec", "moodle-app", "php", "/opt/bitnami/moodle/local/import_h5p.php",
           f"--file=/tmp/generated.h5p", f"--title={title}", f"--course={courseid}"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    for line in result.stdout.split("\n"):
        if line.startswith("{"):
            return json.loads(line)

    return {"status": "error", "message": result.stderr or result.stdout}


def generate_learning_path(
    transcript: str,
    title: str,
    courseid: int,
    output_dir: str = "/tmp/h5p_learning_path",
    video_url: Optional[str] = None
) -> Dict[str, Any]:
    """Generate complete learning path with diverse H5P activities"""
    os.makedirs(output_dir, exist_ok=True)

    # Generate learning path via LLM
    print(json.dumps({"status": "info", "message": "Generating learning path via LLM..."}),
          file=sys.stderr)

    path_data = call_openai_learning_path(transcript, title, video_url or "")
    activities = path_data.get("activities", [])

    if not activities:
        return {"status": "error", "message": "No activities generated"}

    print(json.dumps({
        "status": "info",
        "message": f"Generated {len(activities)} activities",
        "types": [a.get("type") for a in activities]
    }), file=sys.stderr)

    # Build and import each activity
    results = []
    for activity in activities:
        act_type = activity.get("type", "").lower()
        act_title = activity.get("title", f"Activity {activity.get('order', 0)}")
        h5p_path = os.path.join(output_dir, f"activity_{activity.get('order', 0)}_{act_type}.h5p")

        try:
            builder = BUILDERS.get(act_type)
            if not builder:
                results.append({
                    "order": activity.get("order"),
                    "type": act_type,
                    "title": act_title,
                    "error": f"Unknown content type: {act_type}"
                })
                continue

            # Build H5P package
            builder(activity, h5p_path)

            # Import to Moodle
            moodle_result = import_h5p_to_moodle(h5p_path, courseid, act_title)

            results.append({
                "order": activity.get("order"),
                "type": act_type,
                "title": act_title,
                "h5p_path": h5p_path,
                "moodle": moodle_result
            })

            print(json.dumps({
                "status": "progress",
                "message": f"Created {act_type}: {act_title}",
                "activity_id": moodle_result.get("activity_id")
            }), file=sys.stderr)

        except NotImplementedError as e:
            results.append({
                "order": activity.get("order"),
                "type": act_type,
                "title": act_title,
                "skipped": str(e)
            })
        except Exception as e:
            results.append({
                "order": activity.get("order"),
                "type": act_type,
                "title": act_title,
                "error": str(e)
            })

    successful = sum(1 for r in results if "moodle" in r and r["moodle"].get("status") == "success")

    return {
        "status": "success" if successful > 0 else "error",
        "module_title": path_data.get("module_title", title),
        "total_activities": len(activities),
        "successful_imports": successful,
        "activities": results
    }


def fetch_youtube_data(youtube_url_id: int) -> Dict[str, Any]:
    """Fetch YouTube data from Supabase by ID"""
    supabase_url = os.environ.get("SUPABASE_URL", "http://148.230.71.150:8000")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))

    url = f"{supabase_url}/rest/v1/youtube_urls?id=eq.{youtube_url_id}&select=id,title,subtitles,url"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }

    with httpx.Client() as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if not data:
        raise ValueError(f"YouTube URL with ID {youtube_url_id} not found")

    return data[0]


if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv

    # Load environment
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate H5P Learning Path from transcript")
    parser.add_argument("--youtube-url-id", type=int, help="YouTube URL ID from Supabase (fetches subtitles)")
    parser.add_argument("--transcript", help="Video transcript text")
    parser.add_argument("--transcript-file", help="File containing transcript")
    parser.add_argument("--title", help="Module title (overrides DB title)")
    parser.add_argument("--courseid", type=int, help="Moodle course ID for import")
    parser.add_argument("--createcourse", action="store_true", help="Create new Moodle course")
    parser.add_argument("--coursename", help="Name for new course (if --createcourse)")
    parser.add_argument("--output-dir", default="/tmp/h5p_learning_path", help="Output directory")
    parser.add_argument("--no-import", action="store_true", help="Skip Moodle import (just generate H5P files)")

    args = parser.parse_args()

    # Get transcript - prefer youtube-url-id
    transcript = ""
    title = args.title or "Lernmodul"
    video_url = ""

    if args.youtube_url_id:
        try:
            yt_data = fetch_youtube_data(args.youtube_url_id)
            transcript = yt_data.get("subtitles", "")
            if not args.title:
                title = yt_data.get("title") or "Video Lernmodul"
            video_url = yt_data.get("url", "")
            print(json.dumps({"status": "info", "message": f"Fetched subtitles: {len(transcript)} chars for: {title}"}), file=sys.stderr)
        except Exception as e:
            print(json.dumps({"status": "error", "message": f"Failed to fetch from Supabase: {e}"}))
            sys.exit(1)
    elif args.transcript:
        transcript = args.transcript
    elif args.transcript_file:
        with open(args.transcript_file, "r", encoding="utf-8") as f:
            transcript = f.read()

    if not transcript:
        print(json.dumps({"status": "error", "message": "Provide --youtube-url-id, --transcript, or --transcript-file"}))
        sys.exit(1)

    if not args.courseid and not args.createcourse:
        print(json.dumps({"status": "error", "message": "Provide --courseid or --createcourse"}))
        sys.exit(1)

    result = generate_learning_path(
        transcript,
        title,
        args.courseid or 0,
        args.output_dir,
        video_url
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
