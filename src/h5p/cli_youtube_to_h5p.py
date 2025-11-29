#!/usr/bin/env python3
"""
CLI: Generate H5P E-Learning Module from YouTube Subtitles with LLM
Mix of: Passive Learning (40%) + Active Quizzes (40%) + Motivation (20%)
"""
import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import httpx

# Fix module path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from generator import generate_multichoice_h5p, generate_course_presentation_h5p
from content_types import Answer, MultiChoiceContent, SlideElement, Slide, CoursePresentationContent
from package_builder import build_h5p_from_json
from course_schema import LLM_SYSTEM_PROMPT, LLM_USER_PROMPT_TEMPLATE


# Supabase Configuration (self-hosted on VPS)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://148.230.71.150:8000")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzU0NjA0MDAwLCJleHAiOjE5MTIzNzA0MDB9.Br6scJPh8nF7n-QIo1DuOshjMiJkqPBHkHLVmoSpZjs"))

# LLM Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"  # Cost-efficient

# Rich E-Learning Prompt for full Course Presentation
E_LEARNING_PROMPT_RICH = """Du bist ein Experte fuer interaktive Lernmodule.
Erstelle aus dem Video-Transkript einen H5P CoursePresentation Kurs.

STRUKTUR (8-15 Slides):
1. Titel-Slide: Willkommen + Kurs-Titel
2-4. Inhalts-Slides: Erklaerungen mit Text und evtl. Accordion
5-6. Interaktive Slides: MultiChoice, TrueFalse, Blanks oder DialogCards
7. Zusammenfassung: Summary oder letzte Kernpunkte
8. Abschluss-Slide mit Quiz

VERFUEGBARE ELEMENT-TYPEN:
- text: HTML Text {"type":"text","content":"<p>Text</p>"}
- multichoice: Multiple Choice {"type":"multichoice","question":"?","answers":[{"text":"A","correct":true},{"text":"B","correct":false}],"single_answer":true,"randomize":true}
- truefalse: Wahr/Falsch {"type":"truefalse","question":"Aussage","correct":true}
- blanks: Lueckentext {"type":"blanks","text":"Das *Wort* fehlt hier","case_sensitive":false}
- accordion: Aufklapp-Sektionen {"type":"accordion","panels":[{"title":"Titel","content":"Inhalt"}]}
- dialogcards: Karteikarten {"type":"dialogcards","cards":[{"front":"Begriff","back":"Definition"}]}
- summary: Zusammenfassung {"type":"summary","statements":[{"correct":"Richtig","wrong":["Falsch1","Falsch2"]}]}

OUTPUT FORMAT (JSON):
{
  "metadata": {
    "title": "Kurs-Titel",
    "description": "Kursbeschreibung",
    "language": "de",
    "keywords": ["keyword1", "keyword2"]
  },
  "slides": [
    {
      "title": "Slide-Titel fuer Navigation",
      "elements": [
        {"type": "text", "content": "<h2>Willkommen</h2><p>Erklaerung...</p>"},
        {"type": "multichoice", "question": "Frage?", "answers": [{"text": "A", "correct": true, "feedback": "Richtig!"}, {"text": "B", "correct": false, "feedback": "Falsch"}], "single_answer": true, "randomize": true}
      ]
    }
  ]
}

REGELN:
- 8-15 Slides
- Mix aus passiven (Text, Accordion) und aktiven (Quiz, Blanks) Elementen
- Jeder Slide hat einen klaren Titel
- 1-3 Elemente pro Slide (nicht ueberladen)
- Sprache: Deutsch
- Keine Emojis
- Feedback bei Quizzes soll lehrreich sein

VIDEO-TRANSKRIPT:
"""

# Simple fallback prompt (legacy)
E_LEARNING_PROMPT = """Du bist ein erfahrener E-Learning Designer. Erstelle aus dem folgenden Video-Transkript
interaktive Lerninhalte fuer ein H5P-Modul.

WICHTIG: Erstelle einen guten Mix aus:
1. PASSIVE WISSENSVERMITTLUNG (40%): Info-Karten mit den wichtigsten Kernaussagen
2. AKTIVE WIEDERHOLUNG (40%): Multiple-Choice Fragen zum Testen des Verstaendnisses
3. MOTIVATION & SPASS (20%): Positives Feedback, Gamification-Elemente

OUTPUT FORMAT (JSON):
{
  "title": "Kurzer, ansprechender Titel",
  "info_slides": [
    {
      "headline": "Kernaussage als Ueberschrift",
      "bulletpoints": ["Punkt 1", "Punkt 2", "Punkt 3"]
    }
  ],
  "quiz_questions": [
    {
      "question": "Frage zum Inhalt?",
      "answers": [
        {"text": "Korrekte Antwort", "correct": true, "feedback": "Genau richtig!"},
        {"text": "Falsche Antwort 1", "correct": false, "feedback": "Nicht ganz, weil..."},
        {"text": "Falsche Antwort 2", "correct": false, "feedback": "Leider nein, denn..."},
        {"text": "Falsche Antwort 3", "correct": false, "feedback": "Nicht korrekt, weil..."}
      ]
    }
  ],
  "completion_message": "Motivierende Abschluss-Nachricht"
}

REGELN:
- 3-5 Info-Slides
- 3-5 Quiz-Fragen
- Fragen sollen Verstaendnis pruefen, nicht nur Fakten abfragen
- Feedback bei falschen Antworten soll lehrreich sein
- Sprache: Deutsch
- Keine Emojis

VIDEO-TRANSKRIPT:
"""


def fetch_youtube_data(youtube_url_id: int) -> Dict[str, Any]:
    """Fetch YouTube data from Supabase by ID"""
    url = f"{SUPABASE_URL}/rest/v1/youtube_urls?id=eq.{youtube_url_id}&select=id,title,subtitles"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    with httpx.Client() as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if not data:
        raise ValueError(f"YouTube URL with ID {youtube_url_id} not found")

    return data[0]


def call_openai(transcript: str, max_tokens: int = 2000) -> Dict[str, Any]:
    """Call OpenAI API to generate e-learning content (legacy simple mode)"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    # Truncate very long transcripts
    if len(transcript) > 15000:
        transcript = transcript[:15000] + "... [gekuerzt]"

    prompt = E_LEARNING_PROMPT + transcript

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "Du antwortest ausschliesslich mit validem JSON."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        },
        timeout=60.0
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def call_openai_rich(transcript: str, title: str = "Lernmodul", video_url: str = "") -> Dict[str, Any]:
    """Call OpenAI API to generate RICH H5P Course Presentation with multiple content types."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    # Truncate very long transcripts
    if len(transcript) > 20000:
        transcript = transcript[:20000] + "... [gekuerzt]"

    user_prompt = LLM_USER_PROMPT_TEMPLATE.format(
        title=title,
        url=video_url or "N/A",
        transcript=transcript
    )

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 4000,  # More tokens for rich content
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        },
        timeout=90.0  # Longer timeout for complex generation
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def generate_simple_quiz(transcript: str, title: str = "Quiz") -> Dict[str, Any]:
    """Fallback: Generate simple quiz without LLM"""
    words = transcript.lower().split()
    topics = [w for w in set(words) if len(w) > 5][:4]
    if not topics:
        topics = ["content", "topic", "subject", "theme"]

    return {
        "title": title,
        "info_slides": [
            {"headline": "Einfuehrung", "bulletpoints": ["Willkommen zum Lernmodul", "Thema: " + title]}
        ],
        "quiz_questions": [
            {
                "question": f"Was ist das Hauptthema des Videos?",
                "answers": [
                    {"text": topics[0].title() if topics else "Thema A", "correct": True, "feedback": "Richtig!"},
                    {"text": topics[1].title() if len(topics) > 1 else "Thema B", "correct": False, "feedback": "Nicht korrekt."},
                    {"text": topics[2].title() if len(topics) > 2 else "Thema C", "correct": False, "feedback": "Nicht korrekt."},
                    {"text": topics[3].title() if len(topics) > 3 else "Thema D", "correct": False, "feedback": "Nicht korrekt."}
                ]
            }
        ],
        "completion_message": "Gut gemacht!"
    }


def build_course_presentation(content: Dict[str, Any], output_path: str) -> str:
    """Build H5P Course Presentation from LLM content"""
    slides = []

    # Title Slide
    title_slide = Slide(elements=[
        SlideElement(
            x=10, y=30, width=80, height=40,
            library="H5P.AdvancedText 1.1",
            params={"text": f"<h1>{content.get('title', 'Lernmodul')}</h1>"}
        )
    ])
    slides.append(title_slide)

    # Info Slides (Passive Learning)
    for info in content.get("info_slides", []):
        bullets_html = "<ul>" + "".join(f"<li>{bp}</li>" for bp in info.get("bulletpoints", [])) + "</ul>"
        info_slide = Slide(elements=[
            SlideElement(
                x=5, y=5, width=90, height=20,
                library="H5P.AdvancedText 1.1",
                params={"text": f"<h2>{info.get('headline', 'Info')}</h2>"}
            ),
            SlideElement(
                x=5, y=30, width=90, height=60,
                library="H5P.AdvancedText 1.1",
                params={"text": bullets_html}
            )
        ])
        slides.append(info_slide)

    # Quiz Slides (Active Learning)
    for q in content.get("quiz_questions", []):
        answers = [
            Answer(
                text=a["text"],
                correct=a.get("correct", False),
                feedback=a.get("feedback", "")
            )
            for a in q.get("answers", [])
        ]

        mc_content = MultiChoiceContent(
            question=q.get("question", "Frage?"),
            answers=answers,
            title="Quiz",
            enable_retry=True,
            enable_solutions=True
        )

        quiz_slide = Slide(elements=[
            SlideElement(
                x=5, y=5, width=90, height=90,
                library="H5P.MultiChoice 1.16",
                params=mc_content.to_content_json()
            )
        ])
        slides.append(quiz_slide)

    # Completion Slide (Motivation)
    completion_msg = content.get("completion_message", "Herzlichen Glueckwunsch! Du hast das Modul abgeschlossen.")
    completion_slide = Slide(elements=[
        SlideElement(
            x=10, y=30, width=80, height=40,
            library="H5P.AdvancedText 1.1",
            params={"text": f"<h2>Geschafft!</h2><p>{completion_msg}</p>"}
        )
    ])
    slides.append(completion_slide)

    # Generate Course Presentation H5P
    cp_content = CoursePresentationContent(
        title=content.get("title", "Lernmodul"),
        slides=slides
    )

    return generate_course_presentation_h5p(cp_content, output_path)


def build_multichoice_only(content: Dict[str, Any], output_path: str) -> str:
    """Build simple MultiChoice H5P (fallback if Course Presentation fails)"""
    if not content.get("quiz_questions"):
        raise ValueError("No quiz questions in content")

    q = content["quiz_questions"][0]
    answers = [
        Answer(
            text=a["text"],
            correct=a.get("correct", False),
            feedback=a.get("feedback", "")
        )
        for a in q.get("answers", [])
    ]

    return generate_multichoice_h5p(
        q.get("question", "Frage?"),
        [{"text": a.text, "correct": a.correct, "feedback": a.feedback} for a in answers],
        content.get("title", "Quiz"),
        output_path
    )


def import_to_moodle(h5p_path: str, courseid: int, title: str, create_course: bool = False, course_name: str = None) -> dict:
    """Import H5P to Moodle via PHP script"""
    # Copy H5P to container
    subprocess.run(["docker", "cp", h5p_path, "moodle-app:/tmp/generated.h5p"], check=True, capture_output=True)

    # Build import command
    cmd = ["docker", "exec", "moodle-app", "php", "/opt/bitnami/moodle/local/import_h5p.php",
           f"--file=/tmp/generated.h5p", f"--title={title}"]

    if create_course:
        cmd.append("--createcourse")
        if course_name:
            cmd.append(f"--coursename={course_name}")
    else:
        cmd.append(f"--courseid={courseid}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse JSON output
    for line in result.stdout.split("\n"):
        if line.startswith("{"):
            return json.loads(line)

    return {"status": "error", "message": result.stderr or result.stdout}


def main():
    parser = argparse.ArgumentParser(description="Generate H5P E-Learning from YouTube Subtitles")
    parser.add_argument("--youtube-url-id", type=int, help="YouTube URL ID from Supabase (fetches subtitles automatically)")
    parser.add_argument("--youtube-id", help="YouTube Video ID")
    parser.add_argument("--subtitle-text", help="Subtitle/Transcript text")
    parser.add_argument("--title", help="Module title (overrides DB title)")
    parser.add_argument("--courseid", type=int, help="Moodle course ID")
    parser.add_argument("--createcourse", action="store_true", help="Create new course")
    parser.add_argument("--coursename", help="Name for new course")
    parser.add_argument("--output", default="/tmp/generated.h5p", help="Output path")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM, use simple generation")
    parser.add_argument("--multichoice-only", action="store_true", help="Generate only MultiChoice (no Course Presentation)")
    parser.add_argument("--simple", action="store_true", help="Use simple mode (legacy, 3-5 slides)")
    # Rich mode is now default
    args = parser.parse_args()

    # Get transcript - prefer youtube-url-id (fetches from DB)
    transcript = ""
    title = args.title or "Video Lernmodul"
    video_url = ""

    if args.youtube_url_id:
        try:
            yt_data = fetch_youtube_data(args.youtube_url_id)
            transcript = yt_data.get("subtitles", "")
            if not args.title:
                title = yt_data.get("title", "Video Lernmodul")
            video_url = yt_data.get("url", "")
            print(json.dumps({"status": "info", "message": f"Fetched subtitles for: {title}"}), file=sys.stderr)
        except Exception as e:
            print(json.dumps({"status": "error", "message": f"Failed to fetch from Supabase: {e}"}))
            sys.exit(1)
    elif args.subtitle_text:
        transcript = args.subtitle_text

    if not transcript:
        print(json.dumps({"status": "error", "message": "Provide --youtube-url-id or --subtitle-text"}))
        sys.exit(1)

    try:
        # Generate content via LLM or fallback
        if args.no_llm or not OPENAI_API_KEY:
            content = generate_simple_quiz(transcript, title)
            method = "fallback"
            use_rich_builder = False
        elif args.simple:
            # Legacy simple mode
            try:
                content = call_openai(transcript)
                content["title"] = title
                method = "llm_simple"
                use_rich_builder = False
            except Exception as e:
                print(json.dumps({"status": "warning", "message": f"LLM failed: {e}, using fallback"}), file=sys.stderr)
                content = generate_simple_quiz(transcript, title)
                method = "fallback"
                use_rich_builder = False
        else:
            # Rich mode (DEFAULT) - generates full Course Presentation with multiple content types
            try:
                content = call_openai_rich(transcript, title, video_url)
                method = "llm_rich"
                use_rich_builder = True
                print(json.dumps({
                    "status": "info",
                    "message": f"Generated rich content: {len(content.get('slides', []))} slides"
                }), file=sys.stderr)
            except Exception as e:
                print(json.dumps({"status": "warning", "message": f"Rich LLM failed: {e}, trying simple mode"}), file=sys.stderr)
                try:
                    content = call_openai(transcript)
                    content["title"] = title
                    method = "llm_simple"
                    use_rich_builder = False
                except Exception as e2:
                    print(json.dumps({"status": "warning", "message": f"Simple LLM also failed: {e2}, using fallback"}), file=sys.stderr)
                    content = generate_simple_quiz(transcript, title)
                    method = "fallback"
                    use_rich_builder = False

        # Build H5P
        if args.multichoice_only:
            h5p_path = build_multichoice_only(content, args.output)
        elif use_rich_builder:
            # Use new package_builder for rich content
            try:
                h5p_path = build_h5p_from_json(content, args.output)
            except Exception as e:
                print(json.dumps({"status": "warning", "message": f"Rich builder failed: {e}, falling back to simple"}), file=sys.stderr)
                h5p_path = build_course_presentation(content, args.output)
        else:
            # Legacy builder for simple content
            try:
                h5p_path = build_course_presentation(content, args.output)
            except Exception as e:
                print(json.dumps({"status": "warning", "message": f"CoursePresentation failed: {e}, using MultiChoice"}), file=sys.stderr)
                h5p_path = build_multichoice_only(content, args.output)

        # Build result summary
        if use_rich_builder:
            result = {
                "status": "success",
                "h5p_path": h5p_path,
                "method": method,
                "content_summary": {
                    "title": content.get("metadata", {}).get("title", title),
                    "slides": len(content.get("slides", [])),
                    "description": content.get("metadata", {}).get("description", "")[:100],
                    "keywords": content.get("metadata", {}).get("keywords", [])
                }
            }
        else:
            result = {
                "status": "success",
                "h5p_path": h5p_path,
                "method": method,
                "content_summary": {
                    "title": content.get("title"),
                    "info_slides": len(content.get("info_slides", [])),
                    "quiz_questions": len(content.get("quiz_questions", []))
                }
            }

        # Import to Moodle if requested
        if args.courseid or args.createcourse:
            moodle_result = import_to_moodle(
                h5p_path,
                args.courseid or 0,
                title,
                args.createcourse,
                args.coursename or f"{title} - Kurs"
            )
            result["moodle"] = moodle_result

        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
