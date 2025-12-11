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
import base64
import re
from pathlib import Path
from typing import Dict, Any, Optional
import httpx


# ============================================================================
# AI IMAGE GENERATION FOR IMAGEHOTSPOTS
# ============================================================================

def generate_infographic_image(transcript: str, hotspots: list, title: str = "") -> Optional[str]:
    """
    Generate a thematic infographic image using DALL-E based on transcript content.

    Returns: URL of the generated image, or None if generation fails
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print('{"status": "warning", "message": "No OPENAI_API_KEY for image generation"}')
        return None

    # Extract key topics from hotspots for the image prompt
    topics = [hs.get("header", "") for hs in hotspots if hs.get("header")]
    topics_text = ", ".join(topics[:5]) if topics else "key concepts"

    # Create a focused prompt for infographic-style image
    # Truncate transcript to first 500 chars for context
    context = transcript[:500] if transcript else ""

    image_prompt = f"""Create a clean, professional infographic-style illustration for an e-learning module.

Topic: {title or 'Educational Content'}
Key concepts to visualize: {topics_text}

Style requirements:
- Clean, flat design with a modern look
- Use a cohesive color palette (blues, teals, or professional colors)
- Include visual icons or simple graphics representing the key concepts
- Leave space for text overlays (hotspots will be added)
- No text or labels in the image itself
- Abstract/conceptual representation, not photorealistic
- Suitable as a background for interactive hotspots
- Resolution: 1280x720 (landscape)

The image should feel educational, professional, and inviting for learning."""

    try:
        response = httpx.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "dall-e-3",
                "prompt": image_prompt,
                "n": 1,
                "size": "1792x1024",  # Closest to 16:9 available
                "quality": "standard",
                "response_format": "url"
            },
            timeout=60.0
        )
        response.raise_for_status()

        image_url = response.json()["data"][0]["url"]
        print(f'{{"status": "info", "message": "Generated infographic image via DALL-E"}}')
        return image_url

    except Exception as e:
        print(f'{{"status": "warning", "message": "Image generation failed: {str(e)}"}}')
        return None


def download_and_encode_image(image_url: str) -> Optional[tuple]:
    """
    Download image and return base64-encoded data with mime type.
    H5P can embed images directly in the package.

    Returns: (base64_data, mime_type) or None
    """
    try:
        response = httpx.get(image_url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "image/png")
        if "jpeg" in content_type or "jpg" in content_type:
            mime = "image/jpeg"
            ext = "jpg"
        else:
            mime = "image/png"
            ext = "png"

        image_data = base64.b64encode(response.content).decode("utf-8")
        return (image_data, mime, ext, response.content)

    except Exception as e:
        print(f'{{"status": "warning", "message": "Image download failed: {str(e)}"}}')
        return None

# ============================================================================
# LLM PROMPT - Generates complete learning path with all content types
# ============================================================================

LEARNING_PATH_PROMPT = """Du bist ein erfahrener E-Learning-Designer. Erstelle aus dem Transcript einen
professionellen Lernpfad mit H5P-Aktivitäten. Der Kurs muss für Endkunden präsentabel sein!

== DIDAKTISCHES FRAMEWORK ==

GOLDENE REGEL: Nach jedem PASSIVEN Element (Wissensaufnahme) MUSS ein AKTIVES Element (Anwendung) folgen!

PASSIVE ELEMENTE (Wissen vermitteln):
- dialogcards: Karteikarten für 3-5 Kernbegriffe aus dem Transcript
- accordion: Aufklappbare Erklärungen zu 3-4 Hauptthemen

AKTIVE ELEMENTE (Wissen anwenden):
- multichoice: Quiz mit 4 Optionen zu den vermittelten Inhalten
- truefalse: Schneller Faktencheck zu einer konkreten Aussage aus dem Transcript
- blanks: Lückentext mit 2-4 Schlüsselbegriffen zum Ausfüllen
- draganddrop: Begriffe den richtigen Kategorien zuordnen
- summary: Kernaussagen identifizieren (IMMER als letztes Element!)

SPEZIELLE ELEMENTE (nur wenn URL vorhanden):
- interactivevideo: NUR wenn {{VIDEO_URL}} vorhanden - Video mit eingebetteten Fragen
- imagehotspots: NICHT verwenden (Bild passt selten zum Transcript-Inhalt)

== TITEL-REGELN (KRITISCH!) ==

FALSCH: "2. Wichtige Begriffe", "3. accordion", "5. Verständnischeck"
RICHTIG: Inhaltsbezogene Titel aus dem Transcript!

Beispiele für gute Titel:
- "KI-Modelle im Vergleich" statt "Wichtige Begriffe"
- "Wie funktioniert ein LLM?" statt "Kernaussagen"
- "Testen Sie Ihr Wissen zu Transformern" statt "Verständnischeck"

== STRUKTUR (8-10 Aktivitäten) ==

1. EINFÜHRUNG (Passiv): dialogcards mit 3-5 Kernbegriffen aus dem Transcript
2. VERSTÄNDNIS (Aktiv): multichoice zu den gerade gelernten Begriffen
3. VERTIEFUNG (Passiv): accordion mit 3-4 Hauptthemen/Erklärungen
4. ANWENDUNG (Aktiv): blanks mit wichtigen Sätzen aus dem Transcript
5. PRAXIS (Aktiv): draganddrop - Begriffe kategorisieren
6. FAKTENCHECK (Aktiv): truefalse zu einer spezifischen Aussage
7. ABSCHLUSS (Aktiv): summary mit 3-4 Kernaussagen zum Auswählen

Falls {{VIDEO_URL}} vorhanden: interactivevideo nach Aktivität 3 einfügen

== OUTPUT FORMAT (JSON) ==
{
  "module_title": "Spezifischer Titel aus dem Transcript-Thema",
  "activities": [
    {
      "order": 1,
      "type": "dialogcards",
      "title": "[Themenspezifischer Titel]",
      "cards": [
        {"front": "Was versteht man unter <span class='h5p-term'>[Begriff]</span>?", "back": "[Definition aus Transcript]"},
        {"front": "Erkläre <span class='h5p-term'>[Begriff]</span>.", "back": "[Erklärung aus Transcript]"}
      ]
    },
    {
      "order": 2,
      "type": "multichoice",
      "title": "[Inhaltsbezogene Frage]",
      "question": "[Konkrete Frage zum Transcript-Inhalt]",
      "answers": [
        {"text": "[Korrekte Antwort aus Transcript]", "correct": true, "feedback": "Richtig! [Erklärung]"},
        {"text": "[Plausible aber falsche Option]", "correct": false, "feedback": "[Warum falsch]"},
        {"text": "[Weitere falsche Option]", "correct": false, "feedback": "[Warum falsch]"},
        {"text": "[Weitere falsche Option]", "correct": false, "feedback": "[Warum falsch]"}
      ]
    },
    {
      "order": 3,
      "type": "accordion",
      "title": "[Thema der Vertiefung]",
      "panels": [
        {"title": "[Konkretes Unterthema]", "content": "<p>[Detaillierte Erklärung aus Transcript]</p>"},
        {"title": "[Weiteres Unterthema]", "content": "<p>[Weitere Erklärung]</p>"}
      ]
    },
    {
      "order": 4,
      "type": "blanks",
      "title": "[Thema des Lückentexts]",
      "text": "[Wichtiger Satz aus Transcript] mit *Schlüsselbegriff1* und *Schlüsselbegriff2*."
    },
    {
      "order": 5,
      "type": "draganddrop",
      "title": "[Kategorisierungs-Thema]",
      "task": "[Konkrete Aufgabenstellung]",
      "categories": ["[Kategorie aus Transcript]", "[Andere Kategorie]"],
      "items": [
        {"text": "[Begriff]", "category": 0},
        {"text": "[Begriff]", "category": 1}
      ]
    },
    {
      "order": 6,
      "type": "truefalse",
      "title": "Stimmt das?",
      "statement": "[Konkrete Aussage aus dem Transcript]",
      "correct": true,
      "feedback_correct": "Genau! [Begründung aus Transcript]",
      "feedback_wrong": "Nicht ganz. [Richtige Information]"
    },
    {
      "order": 7,
      "type": "summary",
      "title": "Was haben Sie gelernt?",
      "intro": "Wählen Sie die korrekten Kernaussagen:",
      "statements": [
        {
          "correct": "[Korrekte Hauptaussage aus Transcript]",
          "wrong": ["[Falsche Alternative]", "[Weitere falsche Alternative]"]
        }
      ]
    }
  ]
}

== QUALITÄTSKRITERIEN ==

1. ALLE Inhalte MÜSSEN aus dem Transcript stammen - keine erfundenen Fakten!
2. Titel MÜSSEN inhaltsbezogen sein - KEINE generischen Titel wie "Wichtige Begriffe"!
3. Abwechslung: Passiv → Aktiv → Passiv → Aktiv (niemals 2x gleicher Typ hintereinander)
4. Mindestens 5 verschiedene Content-Typen verwenden
5. Sprache: Deutsch, keine Emojis
6. Formatierung:
   - dialogcards: Vorderseite als FRAGE, <span class='h5p-term'>Begriff</span> für Hervorhebung
   - blanks: Lücken mit *Antwort* markieren
   - draganddrop: category ist Index (0, 1, 2...)

== VERBOTEN ==

- Generische Titel ("Begriffe", "Quiz", "Faktencheck")
- Zwei passive Elemente hintereinander
- imagehotspots (Bilder passen selten zum Audio-Transcript)
- Inhalte erfinden, die nicht im Transcript stehen
- Interaktives Video ohne {{VIDEO_URL}}

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

    # Replace placeholders or indicate unavailable URLs
    if video_url:
        prompt = prompt.replace("{{VIDEO_URL}}", video_url)
    else:
        # Mark interactivevideo as unavailable
        prompt = prompt.replace(
            "- interactivevideo: NUR wenn {{VIDEO_URL}} vorhanden - Video mit eingebetteten Fragen",
            "- interactivevideo: NICHT VERFÜGBAR (keine Video-URL)"
        )

    # imagehotspots are disabled by default in the new prompt
    # No replacement needed since they're already marked as "NICHT verwenden"

    prompt = prompt + transcript

    # Add URL context at the end
    if video_url:
        prompt += f"\n\nVERFÜGBARE VIDEO-URL: {video_url}\n"

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

# Dark Theme CSS embedded in every H5P package for Moodle dark theme compatibility
H5P_DARK_THEME_CSS = """
/* H5P Dark Theme - Embedded in Package */
/* Issue #13: CSS must be in package since iframe doesn't inherit theme */

/* DIALOGCARDS - Dark cards with white text */
.h5p-dialogcards-card-content,
.h5p-dialogcards .h5p-dialogcards-card,
.h5p-dialogcards-card-side,
.h5p-dialogcards-card-text-wrapper,
.h5p-dialogcards-card-text-area,
.h5p-dialogcards-card-text-inner,
.h5p-dialogcards-card-text {
    background-color: #252538 !important;
    color: #ffffff !important;
}

/* TRUE/FALSE - Both buttons visible */
.h5p-true-false .h5p-question-content {
    background-color: #1a1a2e !important;
}
.h5p-true-false .h5p-question-introduction,
.h5p-true-false .h5p-question-introduction p {
    color: #ffffff !important;
}
.h5p-true-false-answer,
.h5p-answer {
    background-color: #252538 !important;
    color: #ffffff !important;
    border: 1px solid #555 !important;
    display: inline-block !important;
    min-width: 80px !important;
}

/* MULTICHOICE */
.h5p-question-content, .h5p-multichoice {
    background-color: #1a1a2e !important;
}
.h5p-question-introduction p, .h5p-question h2, .h5p-question h3 {
    color: #ffffff !important;
}
.h5p-alternative-container .h5p-answer {
    background-color: #252538 !important;
    color: #e8e8e8 !important;
}
.h5p-alternative-inner { color: #e8e8e8 !important; }

/* ACCORDION */
.h5p-accordion { background-color: #1a1a2e !important; }
.h5p-panel-title {
    background-color: #353550 !important;
    color: #ffffff !important;
}
.h5p-panel-content {
    background-color: #252538 !important;
    color: #e0e0e0 !important;
}

/* BLANKS */
.h5p-blanks { background-color: #1a1a2e !important; color: #e8e8e8 !important; }
.h5p-text-input {
    background-color: #333 !important;
    color: #fff !important;
    border: 1px solid #666 !important;
}

/* SUMMARY */
.h5p-summary { background-color: #1a1a2e !important; }
.h5p-summary-statement {
    background-color: #252538 !important;
    color: #e8e8e8 !important;
}

/* DRAG AND DROP */
.h5p-drag-text { background-color: #1a1a2e !important; color: #e8e8e8 !important; }

/* IMAGE HOTSPOTS */
.h5p-image-hotspot-popup {
    background-color: rgba(30, 30, 45, 0.97) !important;
    color: #ffffff !important;
}
.h5p-image-hotspot-popup-header { color: #ffffff !important; }
.h5p-image-hotspot-popup-body p { color: #e0e0e0 !important; }

/* BUTTONS */
.h5p-joubelui-button, .h5p-question-check-answer,
.h5p-question-show-solution, .h5p-question-try-again {
    background-color: #5a4a8a !important;
    color: #ffffff !important;
}

/* Global text visibility */
body, .h5p-content { color: #e8e8e8; }
"""


def _create_h5p_package(content_json: Dict, h5p_json: Dict, output_path: str) -> str:
    """Helper to create H5P zip package with embedded dark theme CSS"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        content_dir = tmppath / "content"
        content_dir.mkdir()

        # Create CSS directory and add dark theme
        css_dir = content_dir / "css"
        css_dir.mkdir()
        with open(css_dir / "dark-theme.css", "w", encoding="utf-8") as f:
            f.write(H5P_DARK_THEME_CSS)

        with open(content_dir / "content.json", "w", encoding="utf-8") as f:
            json.dump(content_json, f, ensure_ascii=False, indent=2)

        # Add preloadedCss to h5p.json for dark theme
        if "preloadedCss" not in h5p_json:
            h5p_json["preloadedCss"] = []
        h5p_json["preloadedCss"].append({"path": "content/css/dark-theme.css"})

        with open(tmppath / "h5p.json", "w", encoding="utf-8") as f:
            json.dump(h5p_json, f, ensure_ascii=False, indent=2)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmppath / "h5p.json", "h5p.json")
            zf.write(content_dir / "content.json", "content/content.json")
            zf.write(css_dir / "dark-theme.css", "content/css/dark-theme.css")

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
        "embedTypes": ["iframe"],
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
            "autoCheck": True
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
        "embedTypes": ["iframe"],
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
            "autoCheck": True,
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
        "embedTypes": ["iframe"],
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
        "embedTypes": ["iframe"],
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
        "embedTypes": ["iframe"],
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
        "embedTypes": ["iframe"],
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
        "embedTypes": ["iframe"],
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

def build_image_hotspots_h5p(data: Dict[str, Any], output_path: str, transcript: str = "") -> str:
    """
    Build H5P.ImageHotspots package with AI-generated or provided image.

    If no image_url is provided (or it's a YouTube thumbnail), generates a
    contextual infographic via DALL-E based on the transcript content.

    Expected data format:
    {
        "type": "imagehotspots",
        "title": "Themen-Übersicht",
        "image_url": "https://...",  # Optional - will generate if missing
        "hotspots": [
            {
                "x": 25,  # percentage from left
                "y": 40,  # percentage from top
                "header": "Thema A",
                "content": "Erklärung zu Thema A..."
            }
        ]
    }
    """
    hotspots = data.get("hotspots", [])
    title = data.get("title", "Themenübersicht")
    image_url = data.get("image_url", "")

    # Check if we should generate an AI image
    # Generate if: no URL, or URL is a YouTube thumbnail (which isn't content-specific)
    should_generate = not image_url or "img.youtube.com" in image_url

    if should_generate and hotspots:
        print('{"status": "info", "message": "Generating AI infographic for ImageHotspots..."}')
        generated_url = generate_infographic_image(
            transcript=transcript,
            hotspots=hotspots,
            title=title
        )
        if generated_url:
            image_url = generated_url

    if not image_url:
        raise ValueError("ImageHotspots requires image_url (generation failed)")

    # Build hotspots structure
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

    # Try to download and embed image in package for better performance
    image_data = download_and_encode_image(image_url)

    if image_data:
        # Embed image in package - better for offline/performance
        b64_data, mime, ext, raw_bytes = image_data
        image_filename = f"images/infographic.{ext}"

        content_json = {
            "image": {
                "path": image_filename,
                "mime": mime,
                "copyright": {"license": "U"},
                "width": 1792,
                "height": 1024
            },
            "hotspots": h5p_hotspots,
            "hotspotNumberLabel": "Hotspot #num",
            "closeButtonLabel": "Schließen",
            "iconType": "icon",
            "icon": "plus",
            "color": "#981d99"
        }

        h5p_json = {
            "title": title,
            "language": "de",
            "mainLibrary": "H5P.ImageHotspots",
            "embedTypes": ["iframe"],
            "license": "U",
            "preloadedDependencies": [
                {"machineName": "H5P.ImageHotspots", "majorVersion": 1, "minorVersion": 10},
                {"machineName": "H5P.Text", "majorVersion": 1, "minorVersion": 1},
                {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
            ]
        }

        # Create package with embedded image
        return _create_h5p_package_with_image(content_json, h5p_json, output_path, image_filename, raw_bytes)

    else:
        # Fallback: use URL directly (external image)
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
            "title": title,
            "language": "de",
            "mainLibrary": "H5P.ImageHotspots",
            "embedTypes": ["iframe"],
            "license": "U",
            "preloadedDependencies": [
                {"machineName": "H5P.ImageHotspots", "majorVersion": 1, "minorVersion": 10},
                {"machineName": "H5P.Text", "majorVersion": 1, "minorVersion": 1},
                {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
            ]
        }

        return _create_h5p_package(content_json, h5p_json, output_path)


def _create_h5p_package_with_image(content_json: Dict, h5p_json: Dict, output_path: str,
                                    image_path: str, image_bytes: bytes) -> str:
    """Create H5P package with embedded image file and dark theme CSS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        content_dir = tmppath / "content"
        content_dir.mkdir()

        # Create images subdirectory and save image
        images_dir = content_dir / "images"
        images_dir.mkdir()
        image_filename = Path(image_path).name
        with open(images_dir / image_filename, "wb") as f:
            f.write(image_bytes)

        # Create CSS directory and add dark theme
        css_dir = content_dir / "css"
        css_dir.mkdir()
        with open(css_dir / "dark-theme.css", "w", encoding="utf-8") as f:
            f.write(H5P_DARK_THEME_CSS)

        with open(content_dir / "content.json", "w", encoding="utf-8") as f:
            json.dump(content_json, f, ensure_ascii=False, indent=2)

        # Add preloadedCss to h5p.json for dark theme
        if "preloadedCss" not in h5p_json:
            h5p_json["preloadedCss"] = []
        h5p_json["preloadedCss"].append({"path": "content/css/dark-theme.css"})

        with open(tmppath / "h5p.json", "w", encoding="utf-8") as f:
            json.dump(h5p_json, f, ensure_ascii=False, indent=2)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmppath / "h5p.json", "h5p.json")
            zf.write(content_dir / "content.json", "content/content.json")
            zf.write(images_dir / image_filename, f"content/images/{image_filename}")
            zf.write(css_dir / "dark-theme.css", "content/css/dark-theme.css")

        return output_path


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
           f"--file=/tmp/generated.h5p", f"--title={title}", f"--courseid={courseid}"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    for line in result.stdout.split("\n"):
        if line.startswith("{"):
            return json.loads(line)

    return {"status": "error", "message": result.stderr or result.stdout}


def create_moodle_course(coursename: str, courseimage: Optional[str] = None) -> Dict[str, Any]:
    """Create a new Moodle course via PHP script"""
    # Build command with optional courseimage
    cmd = [
        "docker", "exec", "moodle-app", "php", "/opt/bitnami/moodle/local/import_h5p.php",
        "--createcourse",
        f"--coursename={coursename}",
        "--file=/dev/null"  # Dummy file, we just want to create the course
    ]

    if courseimage:
        cmd.append(f"--courseimage={courseimage}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    for line in result.stdout.split("\n"):
        if line.startswith("{"):
            data = json.loads(line)
            # Extract courseid from the response - ensure it's an integer
            if data.get("status") == "success" or data.get("courseid"):
                courseid = data.get("courseid")
                if courseid:
                    courseid = int(courseid)  # Ensure integer
                return {"status": "success", "courseid": courseid}
            return data

    return {"status": "error", "message": result.stderr or result.stdout}


def generate_learning_path(
    transcript: str,
    title: str,
    courseid: int,
    output_dir: str = "/tmp/h5p_learning_path",
    video_url: Optional[str] = None,
    createcourse: bool = False,
    coursename: Optional[str] = None,
    courseimage: Optional[str] = None
) -> Dict[str, Any]:
    """Generate complete learning path with diverse H5P activities"""
    os.makedirs(output_dir, exist_ok=True)

    # Create course if requested
    if createcourse:
        course_result = create_moodle_course(coursename or title, courseimage)
        if course_result.get("status") == "success":
            courseid = course_result.get("courseid", 0)
            print(json.dumps({
                "status": "info",
                "message": f"Created course: {coursename or title}",
                "courseid": courseid
            }), file=sys.stderr)
        else:
            return {"status": "error", "message": f"Failed to create course: {course_result.get('message')}"}

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
            # ImageHotspots needs transcript for AI image generation
            if act_type == "imagehotspots":
                builder(activity, h5p_path, transcript=transcript)
            else:
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

    # E2E Validation: Verify H5P content is accessible via HTTP
    e2e_results = []
    moodle_base = os.environ.get("MOODLE_URL", "https://moodle.srv947487.hstgr.cloud")

    for r in results:
        if r.get("moodle", {}).get("status") == "success":
            cmid = r["moodle"].get("cmid")
            if cmid:
                try:
                    # Check if the H5P activity page is reachable
                    url = f"{moodle_base}/mod/h5pactivity/view.php?id={cmid}"
                    resp = httpx.get(url, follow_redirects=True, timeout=10.0)
                    # 200 OK or 303 redirect (to login) both indicate the page exists
                    if resp.status_code in [200, 303]:
                        e2e_results.append({"cmid": cmid, "status": "reachable"})
                    else:
                        e2e_results.append({"cmid": cmid, "status": "error", "http_status": resp.status_code})
                except Exception as e:
                    e2e_results.append({"cmid": cmid, "status": "error", "message": str(e)})

    e2e_passed = sum(1 for r in e2e_results if r.get("status") == "reachable")

    return {
        "status": "success" if successful > 0 else "error",
        "module_title": path_data.get("module_title", title),
        "total_activities": len(activities),
        "successful_imports": successful,
        "e2e_validation": {
            "verified": e2e_passed,
            "total": len(e2e_results),
            "all_passed": e2e_passed == len(e2e_results)
        },
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

    # Extract YouTube thumbnail for course image if creating course
    courseimage = None
    if args.createcourse and video_url:
        video_id_match = re.search(
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            video_url
        )
        if video_id_match:
            video_id = video_id_match.group(1)
            courseimage = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    result = generate_learning_path(
        transcript=transcript,
        title=title,
        courseid=args.courseid or 0,
        output_dir=args.output_dir,
        video_url=video_url,
        createcourse=args.createcourse,
        coursename=args.coursename,
        courseimage=courseimage
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
