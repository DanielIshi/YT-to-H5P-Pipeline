"""
H5P DragText Builder

Drag and drop text for word assignments.
"""
from typing import Dict, Any

from .base import create_h5p_package, COMMON_DEPENDENCIES


def build_dragtext_params(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform stage3 output into H5P.DragText params (content.json payload).
    Supports both marker-based text and legacy categories/items.
    """
    if "text" in data and "*" in data.get("text", ""):
        text_field = data["text"]
        task_description = data.get("task_description", "Ziehe die Wörter an die richtige Stelle.")
    else:
        categories = data.get("categories", ["Kategorie A", "Kategorie B"])
        items = data.get("items", [])

        text_lines = []
        for i, category in enumerate(categories):
            cat_items = [item["text"] for item in items if item.get("category", 0) == i]
            if cat_items:
                items_str = " ".join([f"*{item}*" for item in cat_items])
                text_lines.append(f"{category}: {items_str}")

        text_field = "\n".join(text_lines)
        task_description = data.get("task", "Ordne die Begriffe den richtigen Kategorien zu.")

    return {
        "taskDescription": f"<p>{task_description}</p>",
        "textField": text_field,
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


def build_dragtext_h5p(data: Dict[str, Any], output_path: str) -> str:
    """
    Build H5P.DragText package.

    WICHTIG: H5P.DragText erwartet:
    - "taskDescription": Aufgabenbeschreibung (optional)
    - "textField": Der Text mit *Lücken* die gefüllt werden sollen
    - Vollständige a11y-Felder für Accessibility

    Args:
        data: Dict with keys:
            - title: Activity title
            - text: Text with *drag words* marked by asterisks
            - task_description: Task description
            OR for legacy format:
            - task: Task description
            - categories: List of category names
            - items: List of {text, category} dicts
        output_path: Path for the .h5p file

    Returns:
        Path to created H5P package
    """
    content_json = build_dragtext_params(data)

    h5p_json = {
        "title": data.get("title", "Zuordnung"),
        "language": "de",
        "mainLibrary": "H5P.DragText",
        "embedTypes": ["div"],
        "license": "U",
        "preloadedDependencies": [
            {"machineName": "H5P.DragText", "majorVersion": 1, "minorVersion": 10},
            COMMON_DEPENDENCIES["joubelui"],
            COMMON_DEPENDENCIES["question"],
            COMMON_DEPENDENCIES["transition"],
            COMMON_DEPENDENCIES["jqueryui"],
            COMMON_DEPENDENCIES["fontawesome"]
        ]
    }

    return create_h5p_package(content_json, h5p_json, output_path)
