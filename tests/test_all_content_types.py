#!/usr/bin/env python3
"""
Robustness Test: Alle 9 H5P Content-Types

Testet jeden Content-Type Builder mit Beispieldaten.
Ziel: Sicherstellen, dass alle Builder funktionieren BEVOR wir zum VPS deployen.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from h5p.learning_path_generator import (
    build_multichoice_h5p,
    build_truefalse_h5p,
    build_blanks_h5p,
    build_dialogcards_h5p,
    build_accordion_h5p,
    build_summary_h5p,
    build_draganddrop_h5p,
    build_interactive_video_h5p,
    build_image_hotspots_h5p,
    extract_video_id,
    extract_timestamps_from_subtitles,
    get_youtube_thumbnail,
)


# Test data for each content type
TEST_DATA = {
    "multichoice": {
        "title": "Test MultiChoice",
        "question": "Was ist 2 + 2?",
        "answers": [
            {"text": "4", "correct": True, "feedback": "Richtig!"},
            {"text": "3", "correct": False, "feedback": "Falsch"},
            {"text": "5", "correct": False, "feedback": "Falsch"},
        ]
    },
    "truefalse": {
        "title": "Test TrueFalse",
        "statement": "Python ist eine Programmiersprache.",
        "correct": True,
        "feedback_correct": "Richtig!",
        "feedback_wrong": "Falsch!"
    },
    "blanks": {
        "title": "Test Blanks",
        "text": "Python ist eine *Programmiersprache*. Sie wurde von *Guido van Rossum* entwickelt."
    },
    "dialogcards": {
        "title": "Test Dialogcards",
        "cards": [
            {"front": "Python", "back": "Eine interpretierte Programmiersprache"},
            {"front": "Variable", "back": "Ein benannter Speicherplatz für Daten"},
        ]
    },
    "accordion": {
        "title": "Test Accordion",
        "panels": [
            {"title": "Was ist Python?", "content": "<p>Python ist eine Programmiersprache.</p>"},
            {"title": "Warum Python?", "content": "<p>Python ist einfach zu lernen.</p>"},
        ]
    },
    "summary": {
        "title": "Test Summary",
        "intro": "Wähle die korrekten Aussagen:",
        "statements": [
            {"correct": "Python ist interpretiert.", "wrong": ["Python ist kompiliert.", "Python ist assembler."]},
            {"correct": "Python hat dynamische Typisierung.", "wrong": ["Python ist statisch typisiert."]},
        ]
    },
    "draganddrop": {
        "title": "Test DragAndDrop",
        "task": "Ordne die Begriffe zu.",
        "categories": ["Programmiersprachen", "Datenbanken"],
        "items": [
            {"text": "Python", "category": 0},
            {"text": "PostgreSQL", "category": 1},
            {"text": "JavaScript", "category": 0},
        ]
    },
    "interactivevideo": {
        "title": "Test InteractiveVideo",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "interactions": [
            {
                "time": 30,
                "type": "multichoice",
                "label": "Frage 1",
                "question": "Was siehst du?",
                "answers": [
                    {"text": "Ein Video", "correct": True},
                    {"text": "Ein Bild", "correct": False},
                ]
            },
            {
                "time": 60,
                "type": "truefalse",
                "label": "Frage 2",
                "statement": "Das Video ist farbig.",
                "correct": True
            },
        ]
    },
    "imagehotspots": {
        "title": "Test ImageHotspots",
        "image_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
        "hotspots": [
            {"x": 25, "y": 30, "header": "Punkt 1", "content": "Erklärung zu Punkt 1"},
            {"x": 75, "y": 60, "header": "Punkt 2", "content": "Erklärung zu Punkt 2"},
        ]
    },
}

# Map content type to builder function
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


def test_helper_functions():
    """Test helper functions"""
    print("\n=== Testing Helper Functions ===")

    # Test extract_video_id
    test_urls = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]

    for url, expected_id in test_urls:
        result = extract_video_id(url)
        status = "✅" if result == expected_id else "❌"
        print(f"  {status} extract_video_id({url[:40]}...) = {result}")

    # Test get_youtube_thumbnail
    thumbnail = get_youtube_thumbnail("dQw4w9WgXcQ")
    expected = "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
    status = "✅" if thumbnail == expected else "❌"
    print(f"  {status} get_youtube_thumbnail() = {thumbnail[:50]}...")

    # Test extract_timestamps_from_subtitles
    test_subtitles = """
    0:00 Intro
    1:30 Hauptteil
    5:45 Zusammenfassung
    """
    timestamps = extract_timestamps_from_subtitles(test_subtitles)
    status = "✅" if len(timestamps) >= 2 else "❌"
    print(f"  {status} extract_timestamps_from_subtitles() found {len(timestamps)} timestamps")

    return True


def test_content_type(content_type: str, data: dict, output_dir: str) -> dict:
    """Test a single content type builder"""
    result = {
        "type": content_type,
        "success": False,
        "error": None,
        "h5p_path": None,
        "h5p_size": 0,
    }

    try:
        builder = BUILDERS[content_type]
        output_path = os.path.join(output_dir, f"test_{content_type}.h5p")

        # Build H5P package
        h5p_path = builder(data, output_path)

        # Verify file exists and has content
        if os.path.exists(h5p_path):
            size = os.path.getsize(h5p_path)
            result["success"] = size > 100  # Minimum size check
            result["h5p_path"] = h5p_path
            result["h5p_size"] = size
        else:
            result["error"] = "H5P file not created"

    except Exception as e:
        result["error"] = str(e)

    return result


def run_all_tests():
    """Run tests for all 9 content types"""
    print("=" * 60)
    print("H5P Content-Type Robustness Test")
    print("=" * 60)

    # Test helper functions first
    test_helper_functions()

    print("\n=== Testing All 9 Content Types ===\n")

    with tempfile.TemporaryDirectory() as output_dir:
        results = []

        for content_type, data in TEST_DATA.items():
            result = test_content_type(content_type, data, output_dir)
            results.append(result)

            status = "✅" if result["success"] else "❌"
            size_kb = result["h5p_size"] / 1024 if result["h5p_size"] else 0

            if result["success"]:
                print(f"  {status} {content_type:20} - {size_kb:.1f} KB")
            else:
                print(f"  {status} {content_type:20} - ERROR: {result['error']}")

        # Summary
        successful = sum(1 for r in results if r["success"])
        total = len(results)

        print("\n" + "=" * 60)
        print(f"ERGEBNIS: {successful}/{total} Content-Types erfolgreich")
        print("=" * 60)

        if successful == total:
            print("\n✅ ALLE TESTS BESTANDEN - Bereit für VPS Deployment!")
        else:
            print("\n❌ FEHLER GEFUNDEN - Bitte vor Deployment beheben!")
            for r in results:
                if not r["success"]:
                    print(f"   - {r['type']}: {r['error']}")

        return successful == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
