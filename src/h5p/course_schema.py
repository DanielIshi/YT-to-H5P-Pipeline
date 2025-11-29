"""
H5P Course Generation Schema for LLM Output

This module defines the JSON schema that an LLM should output to generate
a multimodal H5P Course Presentation from video content.

The schema supports various H5P content types that can be embedded in slides.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# === Quiz Element Types ===

class MultiChoiceAnswer(BaseModel):
    """A single answer option for multiple choice questions."""
    text: str = Field(..., description="Answer text (can include HTML)")
    correct: bool = Field(..., description="Whether this is the correct answer")
    tip: Optional[str] = Field(None, description="Hint shown when hovering")
    feedback: Optional[str] = Field(None, description="Feedback when selected")


class MultiChoiceQuestion(BaseModel):
    """Multiple choice question with single or multiple correct answers."""
    type: Literal["multichoice"] = "multichoice"
    question: str = Field(..., description="The question text (HTML supported)")
    answers: list[MultiChoiceAnswer] = Field(..., min_length=2)
    single_answer: bool = Field(True, description="True=radio buttons, False=checkboxes")
    randomize: bool = Field(True, description="Randomize answer order")


class TrueFalseQuestion(BaseModel):
    """True/False question."""
    type: Literal["truefalse"] = "truefalse"
    question: str = Field(..., description="The statement to evaluate")
    correct: bool = Field(..., description="True if statement is correct")
    feedback_true: Optional[str] = Field(None, description="Feedback if user selects True")
    feedback_false: Optional[str] = Field(None, description="Feedback if user selects False")


class FillInBlanksQuestion(BaseModel):
    """Fill in the blanks question."""
    type: Literal["blanks"] = "blanks"
    text: str = Field(..., description="Text with *blanks* marked by asterisks. E.g., 'Machine *Learning* is a subset of *AI*'")
    case_sensitive: bool = Field(False)


class DragTextQuestion(BaseModel):
    """Drag words into text."""
    type: Literal["dragtext"] = "dragtext"
    text: str = Field(..., description="Text with *draggable* words marked. E.g., 'AI stands for *Artificial* *Intelligence*'")


# === Passive Content Types ===

class TextContent(BaseModel):
    """Simple text/HTML content."""
    type: Literal["text"] = "text"
    content: str = Field(..., description="HTML content")


class ImageContent(BaseModel):
    """Image with optional caption."""
    type: Literal["image"] = "image"
    path: str = Field(..., description="Path to image file or URL")
    alt: str = Field(..., description="Alt text for accessibility")
    caption: Optional[str] = Field(None)


class VideoContent(BaseModel):
    """Embedded video."""
    type: Literal["video"] = "video"
    sources: list[str] = Field(..., description="Video URLs (mp4, webm, youtube)")
    poster: Optional[str] = Field(None, description="Thumbnail image path")


class AccordionItem(BaseModel):
    """Single accordion panel."""
    title: str
    content: str = Field(..., description="HTML content when expanded")


class AccordionContent(BaseModel):
    """Collapsible accordion sections."""
    type: Literal["accordion"] = "accordion"
    panels: list[AccordionItem] = Field(..., min_length=1)


class DialogCard(BaseModel):
    """A single flashcard."""
    front: str = Field(..., description="Front side text/question")
    back: str = Field(..., description="Back side text/answer")
    image: Optional[str] = Field(None, description="Optional image path")


class DialogCardsContent(BaseModel):
    """Flashcard deck for vocabulary/concepts."""
    type: Literal["dialogcards"] = "dialogcards"
    cards: list[DialogCard] = Field(..., min_length=1)
    description: Optional[str] = Field(None, description="Introduction text")


class SummaryStatement(BaseModel):
    """A summary task statement."""
    correct: str = Field(..., description="The correct summary statement")
    wrong: list[str] = Field(..., description="Incorrect alternatives", min_length=1)


class SummaryContent(BaseModel):
    """Summary task - select correct statements."""
    type: Literal["summary"] = "summary"
    intro: Optional[str] = Field(None, description="Introduction text")
    statements: list[SummaryStatement] = Field(..., min_length=1)


# === Slide Definition ===

SlideElement = (
    MultiChoiceQuestion |
    TrueFalseQuestion |
    FillInBlanksQuestion |
    DragTextQuestion |
    TextContent |
    ImageContent |
    VideoContent |
    AccordionContent |
    DialogCardsContent |
    SummaryContent
)


class Slide(BaseModel):
    """A single slide in the course presentation."""
    title: str = Field(..., description="Slide title shown in navigation")
    elements: list[SlideElement] = Field(..., description="Content elements on this slide")
    background: Optional[str] = Field(None, description="Background image path or color")
    speaker_notes: Optional[str] = Field(None, description="Notes for instructor/narrator")


# === Course Structure ===

class CourseMetadata(BaseModel):
    """Course metadata."""
    title: str = Field(..., description="Course title")
    description: str = Field(..., description="Course description/intro")
    language: str = Field("de", description="Content language (de, en, etc.)")
    author: Optional[str] = Field(None)
    license: str = Field("CC BY", description="Content license")
    source_video: Optional[str] = Field(None, description="Original video URL")
    keywords: list[str] = Field(default_factory=list)


class CoursePresentation(BaseModel):
    """
    Complete H5P Course Presentation structure.

    This is the main schema that the LLM should output.
    """
    metadata: CourseMetadata
    slides: list[Slide] = Field(..., min_length=1, description="Course slides in order")

    # Optional settings
    enable_print: bool = Field(False)
    enable_social_sharing: bool = Field(False)
    show_slide_numbers: bool = Field(True)

    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "title": "Einführung in Machine Learning",
                    "description": "Lernen Sie die Grundlagen von ML",
                    "language": "de",
                    "keywords": ["AI", "Machine Learning", "KI"]
                },
                "slides": [
                    {
                        "title": "Was ist Machine Learning?",
                        "elements": [
                            {"type": "text", "content": "<h2>Willkommen!</h2><p>In diesem Kurs lernen wir...</p>"},
                            {"type": "image", "path": "intro.jpg", "alt": "ML Übersicht"}
                        ]
                    },
                    {
                        "title": "Quiz: Grundlagen",
                        "elements": [
                            {
                                "type": "multichoice",
                                "question": "Was ist Machine Learning?",
                                "answers": [
                                    {"text": "Ein Teilbereich der KI", "correct": True},
                                    {"text": "Eine Programmiersprache", "correct": False}
                                ],
                                "single_answer": True
                            }
                        ]
                    }
                ]
            }
        }


# === LLM Prompt Template ===

LLM_SYSTEM_PROMPT = """Du erstellst interaktive H5P Lernkurse im EXAKTEN JSON-Schema.

WICHTIG - DAS EXAKTE FORMAT:
{
  "metadata": {
    "title": "Kurstitel",
    "description": "Kurzbeschreibung",
    "language": "de",
    "keywords": ["keyword1", "keyword2"]
  },
  "slides": [
    {
      "title": "Slide-Titel fuer Navigation",
      "elements": [
        {"type": "text", "content": "<h2>Ueberschrift</h2><p>Text...</p>"}
      ]
    }
  ]
}

ELEMENT-TYPEN (in elements-Array) - NUR diese verwenden:
- text: {"type":"text","content":"<p>HTML Text</p>"}
- multichoice: {"type":"multichoice","question":"Frage?","answers":[{"text":"A","correct":true,"feedback":"Richtig!"},{"text":"B","correct":false,"feedback":"Falsch"}],"single_answer":true,"randomize":true}
- truefalse: {"type":"truefalse","question":"Aussage","correct":true,"feedback_true":"Ja!","feedback_false":"Nein!"}
- blanks: {"type":"blanks","text":"Das *Wort* fehlt","case_sensitive":false}

NICHT VERWENDEN (nicht installiert): accordion, dialogcards, summary, dragtext

REGELN:
- 8-15 Slides mit je 1-3 Elementen
- Jeder Slide braucht "title" UND "elements"
- "metadata" ist Pflicht mit title, description, language, keywords
- Sprache: Deutsch
- Keine Emojis
"""

LLM_USER_PROMPT_TEMPLATE = """Erstelle einen H5P Kurs aus diesem Video-Transcript.

VIDEO: {title}
URL: {url}

TRANSCRIPT:
{transcript}

---
Erstelle 8-12 Slides mit:
1. Willkommens-Slide (text)
2-4. Inhalts-Slides (text)
5-6. Quiz-Slides (multichoice oder truefalse)
7-8. Lueckentext-Slides (blanks)
9+. Weitere Quiz-Slides (multichoice, truefalse)
Letzter Slide: Abschluss (text)

Antworte NUR mit JSON. Kein erklaerende Text drumherum.
"""
