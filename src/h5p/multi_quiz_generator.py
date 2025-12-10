#!/usr/bin/env python3
"""
Multi-Quiz Generator: Creates multiple separate MultiChoice H5P activities
Workaround for H5P Course Presentation JavaScript compatibility issues
"""
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import httpx

# LLM prompt for generating multiple quiz questions
MULTI_QUIZ_PROMPT = """Du bist ein E-Learning Experte. Erstelle aus dem Video-Transkript 5-8 Multiple-Choice Quizfragen.

WICHTIG: Jede Frage wird eine SEPARATE H5P-Aktivität. Erstelle daher vielfältige, eigenständige Fragen.

OUTPUT FORMAT (JSON):
{
  "module_title": "Übergeordneter Titel für alle Quizzes",
  "questions": [
    {
      "title": "Quiz 1: [Kurzer Titel]",
      "question": "Die eigentliche Frage?",
      "answers": [
        {"text": "Korrekte Antwort", "correct": true, "feedback": "Genau richtig! [Erklärung warum]"},
        {"text": "Falsche Option A", "correct": false, "feedback": "Nicht ganz. [Erklärung warum falsch]"},
        {"text": "Falsche Option B", "correct": false, "feedback": "Leider nein. [Erklärung]"},
        {"text": "Falsche Option C", "correct": false, "feedback": "Das stimmt nicht. [Erklärung]"}
      ]
    }
  ]
}

REGELN:
- 5-8 verschiedene Fragen
- Jede Frage hat genau 4 Antwortmöglichkeiten
- Genau EINE Antwort ist korrekt (correct: true)
- Feedback erklärt WARUM richtig/falsch
- Fragen decken verschiedene Aspekte des Videos ab
- Sprache: Deutsch
- Keine Emojis

FRAGENTYPEN (variiere):
1. Faktenwissen: "Was ist...?", "Welche...?"
2. Verständnis: "Warum...?", "Wie erklärt das Video...?"
3. Anwendung: "Was würde passieren, wenn...?"
4. Analyse: "Was ist der Hauptunterschied zwischen...?"

VIDEO-TRANSKRIPT:
"""


def call_openai_multi_quiz(transcript: str, title: str = "Lernmodul") -> Dict[str, Any]:
    """Call OpenAI API to generate multiple quiz questions"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    # Truncate very long transcripts
    if len(transcript) > 15000:
        transcript = transcript[:15000] + "... [gekürzt]"

    prompt = MULTI_QUIZ_PROMPT + transcript

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
            "max_tokens": 3000,
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        },
        timeout=60.0
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def build_single_multichoice_h5p(question_data: Dict[str, Any], output_path: str) -> str:
    """Build a single MultiChoice H5P package"""
    import tempfile
    import zipfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create content directory
        content_dir = tmppath / "content"
        content_dir.mkdir()

        # Build answers array
        answers = []
        for a in question_data.get("answers", []):
            answers.append({
                "text": f"<div>{a['text']}</div>",
                "correct": a.get("correct", False),
                "tpiSpecific": {
                    "choosenFeedback": f"<div>{a.get('feedback', '')}</div>"
                }
            })

        # content.json for MultiChoice
        content_json = {
            "question": f"<p>{question_data.get('question', 'Frage?')}</p>",
            "answers": answers,
            "behaviour": {
                "enableRetry": True,
                "enableSolutionsButton": True,
                "enableCheckButton": True,
                "singlePoint": False,
                "randomAnswers": True,
                "showSolutionsRequiresInput": True,
                "confirmCheckDialog": False,
                "autoCheck": True,
                "passPercentage": 100,
                "showScorePoints": True
            },
            "UI": {
                "checkAnswerButton": "Überprüfen",
                "submitAnswerButton": "Absenden",
                "showSolutionButton": "Lösung anzeigen",
                "tryAgainButton": "Wiederholen",
                "tipsLabel": "Tipps anzeigen",
                "scoreBarLabel": "Du hast :num von :total Punkten erreicht.",
                "tipAvailable": "Tipp verfügbar",
                "feedbackAvailable": "Feedback verfügbar",
                "readFeedback": "Feedback vorlesen",
                "wrongAnswer": "Falsche Antwort",
                "correctAnswer": "Richtige Antwort",
                "shouldCheck": "Hätte ausgewählt werden sollen",
                "shouldNotCheck": "Hätte nicht ausgewählt werden sollen",
                "noInput": "Bitte antworte, bevor du die Lösung siehst",
                "a11yCheck": "Die Antworten überprüfen. Die Eingaben werden als richtig, falsch oder nicht beantwortet markiert.",
                "a11yShowSolution": "Die Lösung anzeigen. Die Aufgabe wird mit der korrekten Lösung angezeigt.",
                "a11yRetry": "Die Aufgabe wiederholen. Alle Versuche werden zurückgesetzt und die Aufgabe beginnt von vorne."
            },
            "confirmCheck": {
                "header": "Beenden?",
                "body": "Bist du sicher, dass du beenden möchtest?",
                "cancelLabel": "Abbrechen",
                "confirmLabel": "Beenden"
            },
            "confirmRetry": {
                "header": "Wiederholen?",
                "body": "Bist du sicher, dass du wiederholen möchtest?",
                "cancelLabel": "Abbrechen",
                "confirmLabel": "Bestätigen"
            },
            "singleAnswer": True,
            "type": "auto"
        }

        with open(content_dir / "content.json", "w", encoding="utf-8") as f:
            json.dump(content_json, f, ensure_ascii=False, indent=2)

        # h5p.json manifest
        h5p_json = {
            "title": question_data.get("title", "Quiz"),
            "language": "de",
            "mainLibrary": "H5P.MultiChoice",
            "embedTypes": ["div"],
            "license": "U",
            "defaultLanguage": "de",
            "preloadedDependencies": [
                {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 16},
                {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
                {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
                {"machineName": "H5P.Transition", "majorVersion": 1, "minorVersion": 0},
                {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
            ]
        }

        with open(tmppath / "h5p.json", "w", encoding="utf-8") as f:
            json.dump(h5p_json, f, ensure_ascii=False, indent=2)

        # Create ZIP without libraries (Moodle has them)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmppath / "h5p.json", "h5p.json")
            zf.write(content_dir / "content.json", "content/content.json")

    return output_path


def import_h5p_to_moodle(h5p_path: str, courseid: int, title: str) -> Dict[str, Any]:
    """Import H5P to Moodle via PHP script"""
    # Copy H5P to container
    subprocess.run(["docker", "cp", h5p_path, "moodle-app:/tmp/generated.h5p"],
                   check=True, capture_output=True)

    # Import - NOTE: option is --course not --courseid!
    cmd = ["docker", "exec", "moodle-app", "php", "/opt/bitnami/moodle/local/import_h5p.php",
           f"--file=/tmp/generated.h5p", f"--title={title}", f"--course={courseid}"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    for line in result.stdout.split("\n"):
        if line.startswith("{"):
            return json.loads(line)

    return {"status": "error", "message": result.stderr or result.stdout}


def generate_multi_quiz_activities(
    transcript: str,
    title: str,
    courseid: int,
    output_dir: str = "/tmp/h5p_quizzes"
) -> Dict[str, Any]:
    """Generate multiple MultiChoice H5P activities and import them to Moodle

    Returns:
        Dict with status and list of created activities
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate quiz questions via LLM
    print(json.dumps({"status": "info", "message": "Generating quiz questions via LLM..."}),
          file=sys.stderr)
    quiz_data = call_openai_multi_quiz(transcript, title)

    questions = quiz_data.get("questions", [])
    if not questions:
        return {"status": "error", "message": "No questions generated"}

    print(json.dumps({"status": "info", "message": f"Generated {len(questions)} questions"}),
          file=sys.stderr)

    # Build and import each quiz
    activities = []
    for i, q in enumerate(questions, 1):
        q_title = q.get("title", f"Quiz {i}")
        h5p_path = os.path.join(output_dir, f"quiz_{i}.h5p")

        try:
            # Build H5P package
            build_single_multichoice_h5p(q, h5p_path)

            # Import to Moodle
            result = import_h5p_to_moodle(h5p_path, courseid, q_title)

            activities.append({
                "index": i,
                "title": q_title,
                "question": q.get("question", ""),
                "h5p_path": h5p_path,
                "moodle_result": result
            })

            print(json.dumps({
                "status": "progress",
                "message": f"Created quiz {i}/{len(questions)}: {q_title}",
                "activity_id": result.get("activity_id")
            }), file=sys.stderr)

        except Exception as e:
            activities.append({
                "index": i,
                "title": q_title,
                "error": str(e)
            })

    successful = sum(1 for a in activities if "error" not in a)

    return {
        "status": "success" if successful > 0 else "error",
        "module_title": quiz_data.get("module_title", title),
        "total_questions": len(questions),
        "successful_imports": successful,
        "activities": activities
    }


if __name__ == "__main__":
    # Test with sample transcript
    import argparse

    parser = argparse.ArgumentParser(description="Generate multiple MultiChoice H5P activities")
    parser.add_argument("--transcript", required=True, help="Video transcript text")
    parser.add_argument("--title", default="Video Lernmodul", help="Module title")
    parser.add_argument("--courseid", type=int, required=True, help="Moodle course ID")
    parser.add_argument("--output-dir", default="/tmp/h5p_quizzes", help="Output directory")

    args = parser.parse_args()

    result = generate_multi_quiz_activities(
        args.transcript,
        args.title,
        args.courseid,
        args.output_dir
    )

    print(json.dumps(result, indent=2))
