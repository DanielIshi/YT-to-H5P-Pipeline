#!/usr/bin/env python3
"""
Create a showcase section in Moodle with all H5P content types.
Marks broken content types with (-) in the title.
"""
import json
import os
import sys
import subprocess
import tempfile
import zipfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "h5p"))

from learning_path_generator import (
    build_multichoice_h5p,
    build_truefalse_h5p,
    build_blanks_h5p,
    build_dialogcards_h5p,
    build_accordion_h5p,
    build_summary_h5p,
    build_draganddrop_h5p,
    build_interactive_video_h5p,
    build_image_hotspots_h5p,
)

# Content Types with their status
# OK = renders correctly, BROKEN = only shows intro text
CONTENT_TYPES = [
    {
        "type": "dialogcards",
        "status": "OK",
        "builder": build_dialogcards_h5p,
        "data": {
            "title": "Dialogcards",
            "cards": [
                {"front": "Was ist H5P?", "back": "H5P ist ein Open-Source-Framework für interaktive Inhalte."},
                {"front": "Wofür steht HTML5?", "back": "HyperText Markup Language Version 5"},
                {"front": "Was ist Moodle?", "back": "Ein Learning Management System (LMS)"}
            ]
        }
    },
    {
        "type": "multichoice",
        "status": "OK",
        "builder": build_multichoice_h5p,
        "data": {
            "title": "MultiChoice",
            "question": "Welche Aussage über H5P ist korrekt?",
            "answers": [
                {"text": "H5P ist Open Source", "correct": True, "feedback": "Richtig! H5P ist vollständig Open Source."},
                {"text": "H5P kostet Lizenzgebühren", "correct": False, "feedback": "Nein, H5P ist kostenlos."},
                {"text": "H5P funktioniert nur offline", "correct": False, "feedback": "Nein, H5P ist webbasiert."},
                {"text": "H5P wurde 2020 eingestellt", "correct": False, "feedback": "Nein, H5P wird aktiv weiterentwickelt."}
            ]
        }
    },
    {
        "type": "accordion",
        "status": "OK",
        "builder": build_accordion_h5p,
        "data": {
            "title": "Accordion",
            "panels": [
                {"title": "Was ist E-Learning?", "content": "<p>E-Learning bezeichnet alle Formen des elektronisch unterstützten Lernens.</p>"},
                {"title": "Vorteile von H5P", "content": "<p>H5P bietet interaktive Inhalte, die in jedes LMS integriert werden können.</p>"},
                {"title": "Einsatzgebiete", "content": "<p>Schulen, Universitäten, Unternehmen und Online-Kurse.</p>"}
            ]
        }
    },
    {
        "type": "truefalse",
        "status": "BROKEN",
        "builder": build_truefalse_h5p,
        "data": {
            "title": "TrueFalse",
            "statement": "H5P-Inhalte können in Moodle eingebettet werden.",
            "correct": True,
            "feedback_correct": "Richtig! H5P ist vollständig in Moodle integrierbar.",
            "feedback_wrong": "Doch! H5P lässt sich problemlos in Moodle einbetten."
        }
    },
    {
        "type": "blanks",
        "status": "BROKEN",
        "builder": build_blanks_h5p,
        "data": {
            "title": "Blanks (Lückentext)",
            "text": "H5P ist ein *Open-Source* Framework für *interaktive* Lerninhalte. Es kann in *Moodle* integriert werden."
        }
    },
    {
        "type": "summary",
        "status": "BROKEN",
        "builder": build_summary_h5p,
        "data": {
            "title": "Summary",
            "intro": "Wähle die korrekten Aussagen über H5P:",
            "statements": [
                {
                    "correct": "H5P ist Open Source und kostenlos nutzbar.",
                    "wrong": ["H5P erfordert teure Lizenzen.", "H5P ist proprietäre Software."]
                },
                {
                    "correct": "H5P-Inhalte sind interaktiv und webbasiert.",
                    "wrong": ["H5P-Inhalte sind statische PDFs.", "H5P funktioniert nur offline."]
                }
            ]
        }
    },
    {
        "type": "draganddrop",
        "status": "BROKEN",
        "builder": build_draganddrop_h5p,
        "data": {
            "title": "DragAndDrop",
            "task": "Ordne die Begriffe den richtigen Kategorien zu:",
            "categories": ["E-Learning Tools", "Traditionell"],
            "items": [
                {"text": "H5P", "category": 0},
                {"text": "Moodle", "category": 0},
                {"text": "Tafel", "category": 1},
                {"text": "SCORM", "category": 0},
                {"text": "Kreide", "category": 1}
            ]
        }
    },
    {
        "type": "interactivevideo",
        "status": "OK",
        "builder": build_interactive_video_h5p,
        "data": {
            "title": "InteractiveVideo",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Example video
            "interactions": [
                {
                    "time": 10,
                    "type": "text",
                    "label": "Willkommen",
                    "text": "Dies ist ein interaktives Video mit eingebetteten Quizfragen."
                },
                {
                    "time": 30,
                    "type": "multichoice",
                    "label": "Quiz",
                    "question": "Was siehst du im Video?",
                    "answers": [
                        {"text": "Einen Mann", "correct": True, "feedback": "Richtig!"},
                        {"text": "Ein Auto", "correct": False, "feedback": "Nein, schau nochmal genau hin."}
                    ]
                }
            ]
        }
    },
    {
        "type": "imagehotspots",
        "status": "OK",
        "builder": build_image_hotspots_h5p,
        "data": {
            "title": "ImageHotspots",
            "image_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            "hotspots": [
                {"x": 25, "y": 40, "header": "Punkt 1", "content": "Hier ist ein interaktiver Hotspot."},
                {"x": 75, "y": 60, "header": "Punkt 2", "content": "Klicke auf die Punkte für mehr Infos."},
                {"x": 50, "y": 80, "header": "Punkt 3", "content": "H5P ImageHotspots ermöglichen interaktive Bilder."}
            ]
        }
    }
]


def import_h5p_to_moodle(h5p_path: str, courseid: int, title: str, section: int = 0) -> dict:
    """Import H5P to Moodle via PHP script"""
    # Copy to container
    subprocess.run(
        ["docker", "cp", h5p_path, "moodle-app:/tmp/showcase.h5p"],
        check=True, capture_output=True
    )

    # Import with section parameter
    cmd = [
        "docker", "exec", "moodle-app", "php",
        "/opt/bitnami/moodle/local/import_h5p.php",
        f"--file=/tmp/showcase.h5p",
        f"--title={title}",
        f"--courseid={courseid}",
        f"--section={section}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    for line in result.stdout.split("\n"):
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass

    return {"status": "error", "message": result.stderr or result.stdout}


def get_next_section_number(courseid: int) -> int:
    """Get the next empty section number"""
    cmd = [
        "docker", "exec", "moodle-mariadb", "mariadb",
        "-u", "bn_moodle", "-pmoodle_db_pass_2025", "bitnami_moodle",
        "-N", "-e",
        f"SELECT MAX(section) + 1 FROM mdl_course_sections WHERE course = {courseid}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 2  # Default to section 2


def rename_section(courseid: int, section: int, name: str):
    """Rename a course section"""
    cmd = [
        "docker", "exec", "moodle-mariadb", "mariadb",
        "-u", "bn_moodle", "-pmoodle_db_pass_2025", "bitnami_moodle",
        "-e",
        f"UPDATE mdl_course_sections SET name = '{name}' WHERE course = {courseid} AND section = {section}"
    ]
    subprocess.run(cmd, capture_output=True, text=True)


def main():
    courseid = 2
    output_dir = "/tmp/h5p_showcase"
    os.makedirs(output_dir, exist_ok=True)

    # Find next available section
    target_section = get_next_section_number(courseid)
    print(f"Creating showcase in Section {target_section}")

    results = []

    for ct in CONTENT_TYPES:
        ct_type = ct["type"]
        status = ct["status"]
        builder = ct["builder"]
        data = ct["data"]

        # Build title with status marker
        if status == "BROKEN":
            title = f"(-) {data['title']}"
        else:
            title = data['title']

        # Update data with marked title
        data_with_title = {**data, "title": title}

        h5p_path = os.path.join(output_dir, f"{ct_type}.h5p")

        try:
            # Build H5P package
            builder(data_with_title, h5p_path)

            # Import to Moodle
            moodle_result = import_h5p_to_moodle(
                h5p_path, courseid, title, target_section
            )

            results.append({
                "type": ct_type,
                "status": status,
                "title": title,
                "moodle": moodle_result
            })

            status_icon = "✓" if moodle_result.get("status") == "success" else "✗"
            print(f"  {status_icon} {title}")

        except Exception as e:
            results.append({
                "type": ct_type,
                "status": status,
                "title": title,
                "error": str(e)
            })
            print(f"  ✗ {title}: {e}")

    # Rename the section
    rename_section(courseid, target_section, "H5P Content Types Showcase")

    # Summary
    successful = sum(1 for r in results if r.get("moodle", {}).get("status") == "success")
    print(f"\n{'='*50}")
    print(f"Created {successful}/{len(CONTENT_TYPES)} activities in Section {target_section}")
    print(f"Section renamed to 'H5P Content Types Showcase'")
    print(f"\nLegend: (-) = Content type has rendering issues")

    return results


if __name__ == "__main__":
    main()
