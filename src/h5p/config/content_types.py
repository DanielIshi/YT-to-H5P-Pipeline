"""
Content-Type Schemas und H5P-spezifische Konfigurationen.

Definiert für jeden Content-Type:
- LLM Output Schema (was der Generator produzieren soll)
- H5P Library Dependencies
- Validierungsregeln
"""

from typing import TypedDict, Any


class ContentTypeSchema(TypedDict):
    """Schema-Definition für einen Content-Type"""
    name: str
    description: str
    engagement_level: str  # "neutral", "interessant", "sehr_interessant", "exzellent"
    llm_output_schema: dict[str, Any]
    h5p_library: dict[str, Any]
    validation_rules: dict[str, Any]


# ============================================================================
# PASSIVE CONTENT-TYPES (Wissensvermittlung)
# ============================================================================

DIALOGCARDS_SCHEMA: ContentTypeSchema = {
    "name": "dialogcards",
    "description": "Karteikarten für Begriffe und Definitionen",
    "engagement_level": "neutral",
    "llm_output_schema": {
        "type": "object",
        "required": ["title", "cards"],
        "properties": {
            "title": {"type": "string", "description": "Titel der Kartensammlung"},
            "cards": {
                "type": "array",
                "minItems": 3,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "required": ["front", "back"],
                    "properties": {
                        "front": {"type": "string", "description": "Vorderseite (Begriff/Frage)"},
                        "back": {"type": "string", "description": "Rückseite (Definition/Antwort)"}
                    }
                }
            }
        }
    },
    "h5p_library": {
        "machineName": "H5P.Dialogcards",
        "majorVersion": 1,
        "minorVersion": 9,
        "dependencies": [
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    },
    "validation_rules": {
        "min_cards": 3,
        "max_cards": 8,
        "max_front_length": 100,
        "max_back_length": 300
    }
}


ACCORDION_SCHEMA: ContentTypeSchema = {
    "name": "accordion",
    "description": "Aufklappbare Panels für strukturierte Erklärungen",
    "engagement_level": "neutral",
    "llm_output_schema": {
        "type": "object",
        "required": ["title", "panels"],
        "properties": {
            "title": {"type": "string"},
            "panels": {
                "type": "array",
                "minItems": 2,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "required": ["title", "content"],
                    "properties": {
                        "title": {"type": "string", "description": "Überschrift des Panels"},
                        "content": {"type": "string", "description": "HTML-Inhalt des Panels"}
                    }
                }
            }
        }
    },
    "h5p_library": {
        "machineName": "H5P.Accordion",
        "majorVersion": 1,
        "minorVersion": 0,
        "dependencies": []
    },
    "validation_rules": {
        "min_panels": 2,
        "max_panels": 6,
        "max_title_length": 80,
        "max_content_length": 500
    }
}


# ============================================================================
# ACTIVE CONTENT-TYPES (Wissensanwendung)
# ============================================================================

TRUEFALSE_SCHEMA: ContentTypeSchema = {
    "name": "truefalse",
    "description": "Wahr/Falsch Aussagen für schnellen Faktencheck",
    "engagement_level": "interessant",
    "llm_output_schema": {
        "type": "object",
        "required": ["title", "statement", "correct", "feedback_correct", "feedback_wrong"],
        "properties": {
            "title": {"type": "string"},
            "statement": {"type": "string", "description": "Die zu bewertende Aussage"},
            "correct": {"type": "boolean", "description": "True wenn Aussage wahr ist"},
            "feedback_correct": {"type": "string", "description": "Feedback bei richtiger Antwort"},
            "feedback_wrong": {"type": "string", "description": "Feedback bei falscher Antwort"}
        }
    },
    "h5p_library": {
        "machineName": "H5P.TrueFalse",
        "majorVersion": 1,
        "minorVersion": 8,
        "dependencies": [
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    },
    "validation_rules": {
        "max_statement_length": 200,
        "max_feedback_length": 150
    }
}


BLANKS_SCHEMA: ContentTypeSchema = {
    "name": "blanks",
    "description": "Lückentext zum Ausfüllen von Begriffen",
    "engagement_level": "sehr_interessant",
    "llm_output_schema": {
        "type": "object",
        "required": ["title", "text", "description"],
        "properties": {
            "title": {"type": "string"},
            "text": {
                "type": "string",
                "description": "Text mit *Lücken* markiert durch Sternchen"
            },
            "description": {"type": "string", "description": "Anweisung für den Lernenden"}
        }
    },
    "h5p_library": {
        "machineName": "H5P.Blanks",
        "majorVersion": 1,
        "minorVersion": 14,
        "dependencies": [
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    },
    "validation_rules": {
        "min_blanks": 2,
        "max_blanks": 5,
        "max_text_length": 500,
        "blank_marker": "*"
    }
}


DRAGTEXT_SCHEMA: ContentTypeSchema = {
    "name": "dragtext",
    "description": "Drag & Drop Text für Zuordnungen",
    "engagement_level": "sehr_interessant",
    "llm_output_schema": {
        "type": "object",
        "required": ["title", "task_description", "text"],
        "properties": {
            "title": {"type": "string"},
            "task_description": {"type": "string", "description": "Anweisung"},
            "text": {
                "type": "string",
                "description": "Text mit *Drag-Wörtern* markiert durch Sternchen"
            }
        }
    },
    "h5p_library": {
        "machineName": "H5P.DragText",
        "majorVersion": 1,
        "minorVersion": 10,
        "dependencies": [
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    },
    "validation_rules": {
        "min_drag_words": 2,
        "max_drag_words": 6,
        "max_text_length": 400,
        "drag_marker": "*"
    }
}


MULTICHOICE_SCHEMA: ContentTypeSchema = {
    "name": "multichoice",
    "description": "Multiple Choice Quiz für Verständnisprüfung",
    "engagement_level": "interessant",
    "llm_output_schema": {
        "type": "object",
        "required": ["title", "question", "answers"],
        "properties": {
            "title": {"type": "string"},
            "question": {"type": "string", "description": "Die Frage"},
            "answers": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": ["text", "correct"],
                    "properties": {
                        "text": {"type": "string"},
                        "correct": {"type": "boolean"},
                        "feedback": {"type": "string"}
                    }
                }
            }
        }
    },
    "h5p_library": {
        "machineName": "H5P.MultiChoice",
        "majorVersion": 1,
        "minorVersion": 16,
        "dependencies": [
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    },
    "validation_rules": {
        "min_answers": 3,
        "max_answers": 5,
        "exactly_one_correct": True,
        "max_question_length": 200,
        "max_answer_length": 100
    }
}


# ============================================================================
# REFLECT CONTENT-TYPES
# ============================================================================

SUMMARY_SCHEMA: ContentTypeSchema = {
    "name": "summary",
    "description": "Kernaussagen identifizieren für Reflexion",
    "engagement_level": "interessant",
    "llm_output_schema": {
        "type": "object",
        "required": ["title", "intro", "statements"],
        "properties": {
            "title": {"type": "string"},
            "intro": {"type": "string", "description": "Einleitungstext"},
            "statements": {
                "type": "array",
                "minItems": 2,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "required": ["correct", "wrong"],
                    "properties": {
                        "correct": {"type": "string", "description": "Korrekte Aussage"},
                        "wrong": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 3,
                            "description": "Falsche Aussagen"
                        }
                    }
                }
            }
        }
    },
    "h5p_library": {
        "machineName": "H5P.Summary",
        "majorVersion": 1,
        "minorVersion": 10,
        "dependencies": [
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    },
    "validation_rules": {
        "min_statement_groups": 2,
        "max_statement_groups": 4,
        "wrong_per_correct": [2, 3]
    }
}


# ============================================================================
# MEDIA CONTENT-TYPES (Post-MVP 1.2)
# ============================================================================

IMAGEHOTSPOTS_SCHEMA: ContentTypeSchema = {
    "name": "imagehotspots",
    "description": "Interaktives Bild mit klickbaren Hotspots",
    "engagement_level": "interessant",
    "llm_output_schema": {
        "type": "object",
        "required": ["title", "image_description", "hotspots"],
        "properties": {
            "title": {"type": "string"},
            "image_description": {
                "type": "string",
                "description": "Beschreibung für Bildgenerierung"
            },
            "hotspots": {
                "type": "array",
                "minItems": 3,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "required": ["x", "y", "header", "content"],
                    "properties": {
                        "x": {"type": "number", "minimum": 0, "maximum": 100},
                        "y": {"type": "number", "minimum": 0, "maximum": 100},
                        "header": {"type": "string"},
                        "content": {"type": "string"}
                    }
                }
            }
        }
    },
    "h5p_library": {
        "machineName": "H5P.ImageHotspots",
        "majorVersion": 1,
        "minorVersion": 10,
        "dependencies": [
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    },
    "validation_rules": {
        "min_hotspots": 3,
        "max_hotspots": 8,
        "requires_image_url": True
    }
}


INTERACTIVEVIDEO_SCHEMA: ContentTypeSchema = {
    "name": "interactivevideo",
    "description": "Video mit eingebetteten Quizfragen",
    "engagement_level": "exzellent",
    "llm_output_schema": {
        "type": "object",
        "required": ["title", "video_url", "interactions"],
        "properties": {
            "title": {"type": "string"},
            "video_url": {"type": "string", "description": "YouTube URL"},
            "interactions": {
                "type": "array",
                "minItems": 2,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": ["time", "type", "question"],
                    "properties": {
                        "time": {"type": "number", "description": "Sekunden"},
                        "type": {"type": "string", "enum": ["multichoice", "truefalse"]},
                        "question": {"type": "string"},
                        "answers": {"type": "array"}
                    }
                }
            }
        }
    },
    "h5p_library": {
        "machineName": "H5P.InteractiveVideo",
        "majorVersion": 1,
        "minorVersion": 26,
        "dependencies": [
            {"machineName": "H5P.Video", "majorVersion": 1, "minorVersion": 6}
        ]
    },
    "validation_rules": {
        "requires_video_url": True,
        "min_interactions": 2,
        "max_interactions": 5
    }
}


# ============================================================================
# SCHEMA REGISTRY
# ============================================================================

CONTENT_TYPE_SCHEMAS: dict[str, ContentTypeSchema] = {
    "dialogcards": DIALOGCARDS_SCHEMA,
    "accordion": ACCORDION_SCHEMA,
    "truefalse": TRUEFALSE_SCHEMA,
    "blanks": BLANKS_SCHEMA,
    "dragtext": DRAGTEXT_SCHEMA,
    "multichoice": MULTICHOICE_SCHEMA,
    "summary": SUMMARY_SCHEMA,
    "imagehotspots": IMAGEHOTSPOTS_SCHEMA,
    "interactivevideo": INTERACTIVEVIDEO_SCHEMA,
}


def get_content_type_schema(content_type: str) -> ContentTypeSchema:
    """
    Hole Schema für einen Content-Type.

    Args:
        content_type: Name des Content-Types

    Returns:
        ContentTypeSchema mit allen Konfigurationen

    Raises:
        ValueError: Wenn Content-Type nicht existiert
    """
    if content_type not in CONTENT_TYPE_SCHEMAS:
        available = ", ".join(CONTENT_TYPE_SCHEMAS.keys())
        raise ValueError(f"Unknown content type '{content_type}'. Available: {available}")
    return CONTENT_TYPE_SCHEMAS[content_type]


def get_llm_schema_for_prompt(content_type: str) -> str:
    """
    Formatiere LLM Output Schema als String für Prompt.

    Args:
        content_type: Name des Content-Types

    Returns:
        JSON-Schema als formatierter String
    """
    import json
    schema = get_content_type_schema(content_type)
    return json.dumps(schema["llm_output_schema"], indent=2, ensure_ascii=False)


def validate_content(content_type: str, data: dict) -> tuple[bool, list[str]]:
    """
    Validiere generierte Daten gegen Content-Type Schema.

    Args:
        content_type: Name des Content-Types
        data: Generierte Daten vom LLM

    Returns:
        Tuple von (is_valid, error_messages)
    """
    schema = get_content_type_schema(content_type)
    rules = schema["validation_rules"]
    errors = []

    # Generische Validierung
    llm_schema = schema["llm_output_schema"]
    required_fields = llm_schema.get("required", [])

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Spezifische Validierung je nach Type
    if content_type == "blanks":
        text = data.get("text", "")
        blank_count = text.count("*") // 2  # Jede Lücke hat 2 Sternchen
        if blank_count < rules.get("min_blanks", 1):
            errors.append(f"Need at least {rules['min_blanks']} blanks, found {blank_count}")

    elif content_type == "multichoice":
        answers = data.get("answers", [])
        correct_count = sum(1 for a in answers if a.get("correct"))
        if rules.get("exactly_one_correct") and correct_count != 1:
            errors.append(f"Need exactly 1 correct answer, found {correct_count}")

    elif content_type == "summary":
        statements = data.get("statements", [])
        if len(statements) < rules.get("min_statement_groups", 2):
            errors.append(f"Need at least {rules['min_statement_groups']} statement groups")

    return len(errors) == 0, errors
