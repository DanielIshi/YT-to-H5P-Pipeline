"""
H5P InteractiveVideo Builder

YouTube video with embedded quiz questions.
"""
import re
from typing import Dict, Any, Optional

from .base import create_h5p_package, COMMON_DEPENDENCIES


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def build_interactivevideo_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.InteractiveVideo package.

    Args:
        data: Dict with keys:
            - title: Activity title
            - video_url: YouTube video URL
            - interactions: List of interaction dicts:
                - time: Timestamp in seconds
                - type: "multichoice", "truefalse", or "text"
                - question/statement/text: Content based on type
                - answers: List of {text, correct, feedback} for multichoice
                - correct: Boolean for truefalse
                - label: Optional label for the interaction
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package

    Raises:
        ValueError: If video_url is missing or invalid
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
        "embedTypes": ["iframe"],  # InteractiveVideo needs iframe!
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.InteractiveVideo", "majorVersion": 1, "minorVersion": 26},
            {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 16},
            {"machineName": "H5P.TrueFalse", "majorVersion": 1, "minorVersion": 8},
            COMMON_DEPENDENCIES["text"],
            {"machineName": "H5P.Summary", "majorVersion": 1, "minorVersion": 10},
            COMMON_DEPENDENCIES["joubelui"],
            COMMON_DEPENDENCIES["question"],
            {"machineName": "H5P.Video", "majorVersion": 1, "minorVersion": 6},
            COMMON_DEPENDENCIES["transition"],
            COMMON_DEPENDENCIES["fontawesome"]
        ]
    }

    return create_h5p_package(content_json, h5p_json, output_path)
