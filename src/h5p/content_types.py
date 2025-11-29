"""H5P Content Type Models"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json


@dataclass
class Answer:
    """Multiple Choice Answer"""
    text: str
    correct: bool
    feedback: str = ""
    tip: str = ""

    def to_h5p(self) -> Dict[str, Any]:
        return {
            "correct": self.correct,
            "tipsAndFeedback": {
                "tip": self.tip,
                "chosenFeedback": f"<div>{self.feedback}</div>" if self.feedback else "",
                "notChosenFeedback": ""
            },
            "text": f"<div>{self.text}</div>"
        }


@dataclass
class MultiChoiceContent:
    """H5P Multiple Choice Content"""
    question: str
    answers: List[Answer]
    title: str = "Quiz"
    language: str = "de"
    enable_retry: bool = True
    enable_solutions: bool = True
    randomize: bool = True
    single_point: bool = False
    pass_percentage: int = 100

    def to_content_json(self) -> Dict[str, Any]:
        return {
            "media": {"type": {"params": {}}, "disableImageZooming": False},
            "answers": [a.to_h5p() for a in self.answers],
            "overallFeedback": [
                {"from": 0, "to": 50, "feedback": "Leider nicht korrekt. Versuche es noch einmal!"},
                {"from": 51, "to": 100, "feedback": "Sehr gut!"}
            ],
            "behaviour": {
                "enableRetry": self.enable_retry,
                "enableSolutionsButton": self.enable_solutions,
                "enableCheckButton": True,
                "type": "auto",
                "singlePoint": self.single_point,
                "randomAnswers": self.randomize,
                "showSolutionsRequiresInput": True,
                "autoCheck": False,
                "passPercentage": self.pass_percentage,
                "showScorePoints": True
            },
            "UI": {
                "checkAnswerButton": "Check",
                "submitAnswerButton": "Submit",
                "showSolutionButton": "Show Solution",
                "tryAgainButton": "Retry"
            },
            "question": f"<p>{self.question}</p>"
        }

    def to_h5p_json(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "language": self.language,
            "mainLibrary": "H5P.MultiChoice",
            "embedTypes": ["iframe"],
            "preloadedDependencies": [
                {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 16},
                {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
                {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
                {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
            ],
            "license": "CC BY",
            "authors": [{"name": "AI Generator", "role": "Author"}]
        }


@dataclass
class SlideElement:
    """Element on a Course Presentation Slide"""
    x: float
    y: float
    width: float
    height: float
    library: str
    params: Dict[str, Any]

    def to_h5p(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "action": {"library": self.library, "params": self.params}
        }


@dataclass
class Slide:
    """Course Presentation Slide"""
    elements: List[SlideElement] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    def to_h5p(self) -> Dict[str, Any]:
        return {
            "elements": [e.to_h5p() for e in self.elements],
            "keywords": [{"main": kw} for kw in self.keywords] if self.keywords else []
        }


@dataclass
class CoursePresentationContent:
    """H5P Course Presentation Content"""
    title: str
    slides: List[Slide]
    language: str = "de"

    def to_content_json(self) -> Dict[str, Any]:
        return {
            "presentation": {
                "slides": [s.to_h5p() for s in self.slides],
                "keywordListEnabled": True
            }
        }

    def to_h5p_json(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "language": self.language,
            "mainLibrary": "H5P.CoursePresentation",
            "embedTypes": ["iframe"],
            # Use older library versions compatible with Moodle 4.1 (H5P Core 1.24)
            "preloadedDependencies": [
                {"machineName": "H5P.CoursePresentation", "majorVersion": 1, "minorVersion": 22},
                {"machineName": "H5P.AdvancedText", "majorVersion": 1, "minorVersion": 1},
                {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 14},
                {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5},
                {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
                {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5}
            ],
            "license": "CC BY",
            "authors": [{"name": "AI Generator", "role": "Author"}]
        }
