#!/usr/bin/env python3
"""
CLI: Generate H5P E-Learning Module from YouTube Subtitles with LLM
RECOMMENDED MODE: --multi-quiz (generates multiple separate MultiChoice activities)
"""
import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try current directory
    load_dotenv()

# Fix module path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from multi_quiz_generator import call_openai_multi_quiz, build_single_multichoice_h5p

# Supabase Configuration (self-hosted on VPS)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://148.230.71.150:8000")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))

# LLM Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"


def fetch_youtube_data(youtube_url_id: int) -> Dict[str, Any]:
    """Fetch YouTube data from Supabase by ID"""
    url = f"{SUPABASE_URL}/rest/v1/youtube_urls?id=eq.{youtube_url_id}&select=id,title,subtitles,url"
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


def import_to_moodle(h5p_path: str, courseid: int, title: str, create_course: bool = False, course_name: str = None) -> dict:
    """Import H5P to Moodle via PHP script"""
    # Copy H5P to container
    subprocess.run(["docker", "cp", h5p_path, "moodle-app:/tmp/generated.h5p"], check=True, capture_output=True)

    # Build import command - NOTE: option is --course not --courseid!
    cmd = ["docker", "exec", "moodle-app", "php", "/opt/bitnami/moodle/local/import_h5p.php",
           f"--file=/tmp/generated.h5p", f"--title={title}"]

    if create_course:
        cmd.append(f"--coursename={course_name or title}")
    else:
        cmd.append(f"--course={courseid}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse JSON output
    for line in result.stdout.split("\n"):
        if line.startswith("{"):
            return json.loads(line)

    return {"status": "error", "message": result.stderr or result.stdout}


def main():
    parser = argparse.ArgumentParser(description="Generate H5P E-Learning from YouTube Subtitles")
    parser.add_argument("--youtube-url-id", type=int, help="YouTube URL ID from Supabase (fetches subtitles automatically)")
    parser.add_argument("--subtitle-text", help="Subtitle/Transcript text (alternative to youtube-url-id)")
    parser.add_argument("--title", help="Module title (overrides DB title)")
    parser.add_argument("--courseid", type=int, help="Moodle course ID for import")
    parser.add_argument("--createcourse", action="store_true", help="Create new Moodle course")
    parser.add_argument("--coursename", help="Name for new course (if --createcourse)")
    parser.add_argument("--output", default="/tmp/generated.h5p", help="Output path for single H5P file")
    parser.add_argument("--output-dir", default="/tmp/h5p_quizzes", help="Output directory for multi-quiz mode")
    parser.add_argument("--multi-quiz", action="store_true", help="Generate multiple separate MultiChoice H5P activities (RECOMMENDED)")
    parser.add_argument("--no-import", action="store_true", help="Skip Moodle import (just generate H5P files)")
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
                title = yt_data.get("title") or "Video Lernmodul"
            video_url = yt_data.get("url", "")
            print(json.dumps({"status": "info", "message": f"Fetched subtitles: {len(transcript)} chars for: {title}"}), file=sys.stderr)
        except Exception as e:
            print(json.dumps({"status": "error", "message": f"Failed to fetch from Supabase: {e}"}))
            sys.exit(1)
    elif args.subtitle_text:
        transcript = args.subtitle_text

    if not transcript:
        print(json.dumps({"status": "error", "message": "Provide --youtube-url-id or --subtitle-text"}))
        sys.exit(1)

    try:
        # Generate quiz questions via LLM
        print(json.dumps({"status": "info", "message": "Generating quiz questions via LLM..."}), file=sys.stderr)
        quiz_data = call_openai_multi_quiz(transcript, title)
        questions = quiz_data.get("questions", [])

        if not questions:
            print(json.dumps({"status": "error", "message": "No quiz questions generated"}))
            sys.exit(1)

        print(json.dumps({
            "status": "info",
            "message": f"Generated {len(questions)} quiz questions"
        }), file=sys.stderr)

        # Multi-Quiz Mode (RECOMMENDED) - generates multiple separate MultiChoice activities
        if args.multi_quiz:
            # Create output directory
            os.makedirs(args.output_dir, exist_ok=True)

            # Build and optionally import each quiz
            activities = []
            current_courseid = args.courseid

            for i, q in enumerate(questions, 1):
                q_title = q.get("title", f"Quiz {i}: {title}")
                h5p_path = os.path.join(args.output_dir, f"quiz_{i}.h5p")

                try:
                    # Build H5P package
                    build_single_multichoice_h5p(q, h5p_path)

                    activity_result = {
                        "index": i,
                        "title": q_title,
                        "question": q.get("question", ""),
                        "h5p_path": h5p_path
                    }

                    # Import to Moodle if requested
                    if not args.no_import and (current_courseid or args.createcourse):
                        moodle_result = import_to_moodle(
                            h5p_path,
                            current_courseid or 0,
                            q_title,
                            args.createcourse if i == 1 else False,  # Only create course once
                            args.coursename or f"{title} - Kurs"
                        )
                        activity_result["moodle"] = moodle_result

                        # Get course_id from first import for subsequent imports
                        if i == 1 and args.createcourse and moodle_result.get("course_id"):
                            current_courseid = moodle_result["course_id"]

                        print(json.dumps({
                            "status": "progress",
                            "message": f"Created quiz {i}/{len(questions)}: {q_title}",
                            "activity_id": moodle_result.get("activity_id")
                        }), file=sys.stderr)

                    activities.append(activity_result)

                except Exception as e:
                    activities.append({
                        "index": i,
                        "title": q_title,
                        "error": str(e)
                    })

            successful = sum(1 for a in activities if "error" not in a)

            result = {
                "status": "success" if successful > 0 else "error",
                "mode": "multi_quiz",
                "module_title": quiz_data.get("module_title", title),
                "total_questions": len(questions),
                "successful_imports": successful,
                "activities": activities
            }

            print(json.dumps(result))

        else:
            # Single H5P Mode - generates one MultiChoice H5P with first question
            q = questions[0]
            build_single_multichoice_h5p(q, args.output)

            result = {
                "status": "success",
                "mode": "single_h5p",
                "h5p_path": args.output,
                "title": q.get("title", title),
                "question": q.get("question", ""),
                "note": f"{len(questions)} questions generated, only 1 used. Use --multi-quiz for all."
            }

            # Import to Moodle if requested
            if not args.no_import and (args.courseid or args.createcourse):
                moodle_result = import_to_moodle(
                    args.output,
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
