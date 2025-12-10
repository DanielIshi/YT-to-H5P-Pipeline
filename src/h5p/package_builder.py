"""
H5P Package Builder

Converts the LLM-generated CoursePresentation JSON into a valid H5P package
that can be uploaded to Moodle.
"""

import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

try:
    from .course_schema import CoursePresentation, Slide, SlideElement
except ImportError:
    from course_schema import CoursePresentation, Slide, SlideElement


class H5PPackageBuilder:
    """Builds H5P packages from CoursePresentation schema."""

    # H5P library versions (must match Moodle installation)
    # Course Presentation requires ALL its dependencies listed
    LIBRARY_VERSIONS = {
        "H5P.CoursePresentation": {"major": 1, "minor": 25},
        "H5P.MultiChoice": {"major": 1, "minor": 16},
        "H5P.TrueFalse": {"major": 1, "minor": 8},
        "H5P.Blanks": {"major": 1, "minor": 14},
        "H5P.DragText": {"major": 1, "minor": 10},
        "H5P.AdvancedText": {"major": 1, "minor": 1},
        "H5P.Image": {"major": 1, "minor": 1},
        "H5P.Video": {"major": 1, "minor": 6},
        "H5P.Accordion": {"major": 1, "minor": 0},
        "H5P.Dialogcards": {"major": 1, "minor": 9},
        "H5P.Summary": {"major": 1, "minor": 10},
        # Core dependencies for Course Presentation
        "H5P.Question": {"major": 1, "minor": 5},
        "H5P.JoubelUI": {"major": 1, "minor": 3},
        "FontAwesome": {"major": 4, "minor": 5},
        "H5P.Transition": {"major": 1, "minor": 0},
        "H5P.FontIcons": {"major": 1, "minor": 0},
        "H5P.DragNBar": {"major": 1, "minor": 5},
        "H5P.DragNDrop": {"major": 1, "minor": 1},
        "H5P.DragNResize": {"major": 1, "minor": 2},
    }

    # Dependencies that Course Presentation always needs
    CORE_DEPENDENCIES = [
        "H5P.JoubelUI", "FontAwesome", "H5P.Transition", "H5P.FontIcons",
        "H5P.DragNBar", "H5P.DragNDrop", "H5P.DragNResize", "H5P.Question"
    ]

    def __init__(self, course: CoursePresentation):
        self.course = course
        self.used_libraries: set[str] = {"H5P.CoursePresentation"}
        self.media_files: dict[str, bytes] = {}

    def build(self, output_path: str) -> str:
        """
        Build the H5P package and save to output_path.

        Returns the path to the created .h5p file.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create content directory
            content_dir = Path(tmpdir) / "content"
            content_dir.mkdir()

            # Generate content.json
            content_json = self._build_content_json()
            (content_dir / "content.json").write_text(
                json.dumps(content_json, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # Copy media files if any
            if self.media_files:
                images_dir = content_dir / "images"
                images_dir.mkdir(exist_ok=True)
                for filename, data in self.media_files.items():
                    (images_dir / filename).write_bytes(data)

            # Generate h5p.json
            h5p_json = self._build_h5p_json()
            (Path(tmpdir) / "h5p.json").write_text(
                json.dumps(h5p_json, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # Create ZIP without directory entries (important for Moodle!)
            h5p_path = Path(output_path)
            with zipfile.ZipFile(h5p_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add h5p.json
                zf.write(Path(tmpdir) / "h5p.json", "h5p.json")
                # Add content/content.json
                zf.write(content_dir / "content.json", "content/content.json")
                # Add media files
                for filename in self.media_files:
                    zf.write(content_dir / "images" / filename, f"content/images/{filename}")

            return str(h5p_path)

    def _build_h5p_json(self) -> dict:
        """Build the h5p.json manifest."""
        # Add core dependencies that Course Presentation always needs
        all_libs = self.used_libraries.union(set(self.CORE_DEPENDENCIES))

        dependencies = []
        for lib_name in sorted(all_libs):
            if lib_name in self.LIBRARY_VERSIONS:
                ver = self.LIBRARY_VERSIONS[lib_name]
                dependencies.append({
                    "machineName": lib_name,
                    "majorVersion": ver["major"],
                    "minorVersion": ver["minor"]
                })

        return {
            "title": self.course.metadata.title,
            "language": self.course.metadata.language,
            "mainLibrary": "H5P.CoursePresentation",
            "embedTypes": ["iframe"],
            "license": self.course.metadata.license,
            "authors": [{"name": self.course.metadata.author or "Auto-generated", "role": "Author"}],
            "preloadedDependencies": dependencies
        }

    def _build_content_json(self) -> dict:
        """Build the content.json for Course Presentation."""
        slides = []
        for slide in self.course.slides:
            slides.append(self._build_slide(slide))

        return {
            "presentation": {
                "slides": slides,
                "keywordListEnabled": True,
                "globalBackgroundSelector": {},
                "keywordListAlwaysShow": False,
                "keywordListAutoHide": False,
                "keywordListOpacity": 90
            },
            "override": {
                "activeSurface": False,
                "hideSummarySlide": False,
                "summarySlideRetry": True,
                "enablePrintButton": self.course.enable_print,
                "social": {
                    "showFacebookShare": self.course.enable_social_sharing,
                    "showTwitterShare": self.course.enable_social_sharing
                }
            },
            "l10n": self._get_localization()
        }

    def _build_slide(self, slide: Slide) -> dict:
        """Build a single slide."""
        elements = []
        y_position = 5  # Start position

        for elem in slide.elements:
            h5p_elem = self._build_element(elem, y_position)
            if h5p_elem:
                elements.append(h5p_elem)
                y_position += 25  # Increment Y for next element

        return {
            "elements": elements,
            "keywords": [{"main": slide.title}],
            "slideBackgroundSelector": {}
        }

    def _build_element(self, elem: SlideElement, y_pos: int) -> dict | None:
        """Convert schema element to H5P element."""
        base = {
            "x": 5,
            "y": y_pos,
            "width": 90,
            "height": 20
        }

        if elem.type == "text":
            return {
                **base,
                "action": {
                    "library": "H5P.AdvancedText 1.1",
                    "params": {"text": elem.content},
                    "subContentId": self._generate_id()
                }
            }

        elif elem.type == "multichoice":
            self.used_libraries.add("H5P.MultiChoice")
            return {
                **base,
                "height": 40,
                "action": {
                    "library": "H5P.MultiChoice 1.16",
                    "params": self._build_multichoice(elem),
                    "subContentId": self._generate_id()
                }
            }

        elif elem.type == "truefalse":
            self.used_libraries.add("H5P.TrueFalse")
            return {
                **base,
                "height": 30,
                "action": {
                    "library": "H5P.TrueFalse 1.8",
                    "params": self._build_truefalse(elem),
                    "subContentId": self._generate_id()
                }
            }

        elif elem.type == "blanks":
            self.used_libraries.add("H5P.Blanks")
            return {
                **base,
                "height": 30,
                "action": {
                    "library": "H5P.Blanks 1.14",
                    "params": self._build_blanks(elem),
                    "subContentId": self._generate_id()
                }
            }

        elif elem.type == "accordion":
            self.used_libraries.add("H5P.Accordion")
            return {
                **base,
                "height": 50,
                "action": {
                    "library": "H5P.Accordion 1.0",
                    "params": self._build_accordion(elem),
                    "subContentId": self._generate_id()
                }
            }

        elif elem.type == "dialogcards":
            self.used_libraries.add("H5P.Dialogcards")
            return {
                **base,
                "height": 50,
                "action": {
                    "library": "H5P.Dialogcards 1.9",
                    "params": self._build_dialogcards(elem),
                    "subContentId": self._generate_id()
                }
            }

        elif elem.type == "summary":
            self.used_libraries.add("H5P.Summary")
            return {
                **base,
                "height": 40,
                "action": {
                    "library": "H5P.Summary 1.10",
                    "params": self._build_summary(elem),
                    "subContentId": self._generate_id()
                }
            }

        elif elem.type == "image":
            self.used_libraries.add("H5P.Image")
            return {
                **base,
                "height": 40,
                "action": {
                    "library": "H5P.Image 1.1",
                    "params": {
                        "file": {"path": elem.path},
                        "alt": elem.alt
                    },
                    "subContentId": self._generate_id()
                }
            }

        return None

    def _build_multichoice(self, elem) -> dict:
        """Build MultiChoice params."""
        answers = []
        for ans in elem.answers:
            answers.append({
                "text": f"<div>{ans.text}</div>",
                "correct": ans.correct,
                "tipsAndFeedback": {
                    "tip": ans.tip or "",
                    "chosenFeedback": ans.feedback or "",
                    "notChosenFeedback": ""
                }
            })

        return {
            "question": f"<p>{elem.question}</p>",
            "answers": answers,
            "behaviour": {
                "enableRetry": True,
                "enableSolutionsButton": True,
                "enableCheckButton": True,
                "type": "auto",
                "singlePoint": True,
                "randomAnswers": elem.randomize,
                "showSolutionsRequiresInput": True,
                "confirmCheckDialog": False,
                "confirmRetryDialog": False,
                "autoCheck": True,
                "passPercentage": 100
            },
            "UI": {
                "checkAnswerButton": "Prüfen",
                "submitAnswerButton": "Absenden",
                "showSolutionButton": "Lösung anzeigen",
                "tryAgainButton": "Wiederholen",
                "correctText": "Richtig!",
                "wrongText": "Falsch"
            }
        }

    def _build_truefalse(self, elem) -> dict:
        """Build TrueFalse params."""
        return {
            "question": f"<p>{elem.question}</p>",
            "correct": "true" if elem.correct else "false",
            "behaviour": {
                "enableRetry": True,
                "enableSolutionsButton": True,
                "confirmCheckDialog": False,
                "confirmRetryDialog": False
            },
            "l10n": {
                "trueText": "Wahr",
                "falseText": "Falsch",
                "checkAnswer": "Prüfen",
                "showSolutionButton": "Lösung anzeigen",
                "tryAgain": "Wiederholen"
            },
            "feedbackOnCorrect": elem.feedback_true or "Richtig!",
            "feedbackOnWrong": elem.feedback_false or "Leider falsch."
        }

    def _build_blanks(self, elem) -> dict:
        """Build Blanks (fill in) params."""
        return {
            "text": elem.text,
            "overallFeedback": [{"from": 0, "to": 100}],
            "showSolutions": "Show solutions",
            "tryAgain": "Retry",
            "checkAnswer": "Check",
            "notFilledOut": "Please fill in all blanks",
            "behaviour": {
                "enableRetry": True,
                "enableSolutionsButton": True,
                "caseSensitive": elem.case_sensitive,
                "autoCheck": True
            }
        }

    def _build_accordion(self, elem) -> dict:
        """Build Accordion params."""
        panels = []
        for panel in elem.panels:
            panels.append({
                "title": panel.title,
                "content": {
                    "params": {"text": panel.content},
                    "library": "H5P.AdvancedText 1.1"
                }
            })
        return {"panels": panels}

    def _build_dialogcards(self, elem) -> dict:
        """Build Dialogcards params."""
        cards = []
        for card in elem.cards:
            cards.append({
                "text": card.front,
                "answer": card.back,
                "tips": []
            })
        return {
            "dialogs": cards,
            "description": elem.description or "",
            "behaviour": {
                "enableRetry": True,
                "scaleTextNotCard": False,
                "randomCards": False
            }
        }

    def _build_summary(self, elem) -> dict:
        """Build Summary params."""
        summaries = []
        for stmt in elem.statements:
            tips = [{"text": stmt.correct}]
            for wrong in stmt.wrong:
                tips.append({"text": wrong})
            summaries.append({"summary": tips})
        return {
            "intro": elem.intro or "Wähle die korrekten Aussagen:",
            "summaries": summaries,
            "solvedLabel": "Abgeschlossen!",
            "scoreLabel": "Falsche Antworten:",
            "labelCorrect": "Richtig!",
            "labelIncorrect": "Falsch!"
        }

    def _get_localization(self) -> dict:
        """Get German localization strings."""
        return {
            "slide": "Folie",
            "score": "Punkte",
            "yourScore": "Deine Punktzahl",
            "maxScore": "Maximale Punktzahl",
            "total": "Gesamt",
            "totalScore": "Gesamtpunktzahl",
            "showSolutions": "Lösungen anzeigen",
            "retry": "Wiederholen",
            "exportAnswers": "Antworten exportieren",
            "hideKeywords": "Schlagwörter ausblenden",
            "showKeywords": "Schlagwörter anzeigen",
            "fullscreen": "Vollbild",
            "exitFullscreen": "Vollbild verlassen",
            "prevSlide": "Vorherige Folie",
            "nextSlide": "Nächste Folie",
            "currentSlide": "Aktuelle Folie",
            "lastSlide": "Letzte Folie",
            "solutionModeTitle": "Lösungsmodus",
            "solutionModeText": "Lösungsmodus beenden",
            "summaryMultipleTaskText": "Aufgaben",
            "scoreMessage": "Du hast :achieved von :max Punkten erreicht.",
            "shareFacebook": "Auf Facebook teilen",
            "shareTwitter": "Auf Twitter teilen"
        }

    def _generate_id(self) -> str:
        """Generate a unique subContentId."""
        import uuid
        return str(uuid.uuid4())


def build_h5p_from_json(course_json: dict, output_path: str) -> str:
    """
    Build an H5P package from JSON data.

    Args:
        course_json: JSON data matching CoursePresentation schema
        output_path: Path for the output .h5p file

    Returns:
        Path to the created .h5p file
    """
    course = CoursePresentation.model_validate(course_json)
    builder = H5PPackageBuilder(course)
    return builder.build(output_path)
