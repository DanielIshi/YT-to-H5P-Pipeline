"""
Milestone-spezifische Konfigurationen für die H5P-Pipeline.

Jeder Milestone hat unterschiedliche Content-Types verfügbar:
- MVP 1.0: 7 Basis-Types (Text-basiert)
- Post-MVP 1.1: + UX Verbesserungen (Auto-Weiter)
- Post-MVP 1.2: + Media Types (Video, Audio, Bilder)
- Post-MVP 1.3: + Multimodal (Spracheingabe)
"""

from typing import TypedDict


class PhaseConfig(TypedDict):
    """Konfiguration für eine didaktische Phase"""
    types: list[str]
    weight: float  # Anteil an Gesamtaktivitäten (0.0-1.0)
    description: str


class MilestoneConfig(TypedDict):
    """Vollständige Milestone-Konfiguration"""
    name: str
    description: str
    phases: dict[str, PhaseConfig]
    rules: dict[str, any]
    content_type_matching: dict[str, list[str]]


# ============================================================================
# MVP 1.0 - Basis-Pipeline (7 Content-Types)
# ============================================================================
MVP_CONFIG: MilestoneConfig = {
    "name": "MVP 1.0",
    "description": "Funktionsfähige Pipeline mit 7 Text-basierten Content-Types",
    "phases": {
        "passive": {
            "types": ["dialogcards", "accordion"],
            "weight": 0.25,
            "description": "Wissensvermittlung: Begriffe und Erklärungen"
        },
        "active": {
            "types": ["truefalse", "blanks", "dragtext", "multichoice"],
            "weight": 0.50,
            "description": "Wissensanwendung: Übungen und Quiz"
        },
        "reflect": {
            "types": ["summary"],
            "weight": 0.15,
            "description": "Reflexion: Kernaussagen identifizieren"
        }
    },
    "rules": {
        "min_activities": 8,
        "max_activities": 12,
        "max_consecutive_same_type": 1,
        "summary_position": "last",
        "passive_before_active": True
    },
    "content_type_matching": {
        "DEFINITION": ["dialogcards", "blanks"],
        "PROZESS": ["dragtext", "multichoice"],
        "VERGLEICH": ["truefalse", "multichoice"],
        "FAKT": ["truefalse"],
        "BEISPIEL": ["blanks", "multichoice"]
    }
}


# ============================================================================
# Post-MVP 1.1 - UX Verbesserungen
# ============================================================================
POST_MVP_1_1_CONFIG: MilestoneConfig = {
    "name": "Post-MVP 1.1 - UX",
    "description": "Verbesserte User Experience mit Auto-Weiter und weniger Klicks",
    "phases": {
        **MVP_CONFIG["phases"]
    },
    "rules": {
        **MVP_CONFIG["rules"],
        "auto_advance_on_correct": True,  # NEU: Automatisch weiter bei richtiger Antwort
        "reduce_confirmation_dialogs": True  # NEU: Weniger Bestätigungsdialoge
    },
    "content_type_matching": MVP_CONFIG["content_type_matching"]
}


# ============================================================================
# Post-MVP 1.2 - Media Types
# ============================================================================
POST_MVP_1_2_CONFIG: MilestoneConfig = {
    "name": "Post-MVP 1.2 - Media",
    "description": "Automatische Video/Audio/Bild-Generierung",
    "phases": {
        "intro": {
            "types": ["imagehotspots"],
            "weight": 0.05,
            "description": "Neugier wecken: Visueller Überblick"
        },
        "passive": {
            "types": ["dialogcards", "accordion", "interactivevideo"],
            "weight": 0.25,
            "description": "Wissensvermittlung mit Video-Integration"
        },
        "active": {
            "types": ["truefalse", "blanks", "dragtext", "multichoice"],
            "weight": 0.45,
            "description": "Wissensanwendung"
        },
        "reflect": {
            "types": ["summary", "audiosummary"],
            "weight": 0.15,
            "description": "Reflexion mit Audio-Zusammenfassung"
        },
        "extend": {
            "types": ["audiofaq"],
            "weight": 0.05,
            "description": "Vertiefung mit FAQ"
        }
    },
    "rules": {
        **POST_MVP_1_1_CONFIG["rules"],
        "prefer_visual_for_processes": True,  # NEU: Prozesse visuell darstellen
        "generate_audio_summary": True  # NEU: ElevenLabs Audio generieren
    },
    "content_type_matching": {
        **MVP_CONFIG["content_type_matching"],
        "PROZESS": ["interactivevideo", "dragtext", "imagehotspots"],
        "VISUAL": ["imagehotspots", "interactivevideo"]
    }
}


# ============================================================================
# Post-MVP 1.3 - Multimodal
# ============================================================================
POST_MVP_1_3_CONFIG: MilestoneConfig = {
    "name": "Post-MVP 1.3 - Multimodal",
    "description": "Spracheingabe und multimodale Interaktion",
    "phases": {
        **POST_MVP_1_2_CONFIG["phases"],
        "active": {
            "types": ["truefalse", "blanks", "dragtext", "multichoice", "speechinput_quiz"],
            "weight": 0.45,
            "description": "Wissensanwendung mit Spracheingabe"
        }
    },
    "rules": {
        **POST_MVP_1_2_CONFIG["rules"],
        "enable_speech_input": True,  # NEU: Web Speech API Integration
        "speech_quiz_ratio": 0.2  # 20% der Quiz-Fragen mit Spracheingabe
    },
    "content_type_matching": {
        **POST_MVP_1_2_CONFIG["content_type_matching"],
        "DEFINITION": ["dialogcards", "blanks", "speechinput_quiz"],
        "BEISPIEL": ["blanks", "speechinput_quiz"]
    }
}


# ============================================================================
# Milestone Registry
# ============================================================================
MILESTONE_CONFIGS: dict[str, MilestoneConfig] = {
    "mvp": MVP_CONFIG,
    "1.0": MVP_CONFIG,
    "1.1": POST_MVP_1_1_CONFIG,
    "1.2": POST_MVP_1_2_CONFIG,
    "1.3": POST_MVP_1_3_CONFIG
}


def get_milestone_config(milestone: str) -> MilestoneConfig:
    """
    Hole Konfiguration für einen Milestone.

    Args:
        milestone: "mvp", "1.0", "1.1", "1.2", oder "1.3"

    Returns:
        MilestoneConfig mit allen Phasen, Regeln und Content-Type-Mappings

    Raises:
        ValueError: Wenn Milestone nicht existiert
    """
    if milestone not in MILESTONE_CONFIGS:
        available = ", ".join(MILESTONE_CONFIGS.keys())
        raise ValueError(f"Unknown milestone '{milestone}'. Available: {available}")
    return MILESTONE_CONFIGS[milestone]


def get_all_content_types(milestone: str) -> list[str]:
    """
    Alle verfügbaren Content-Types für einen Milestone.

    Args:
        milestone: Milestone-Bezeichnung

    Returns:
        Flache Liste aller Content-Types
    """
    config = get_milestone_config(milestone)
    types = []
    for phase in config["phases"].values():
        types.extend(phase["types"])
    return list(set(types))  # Deduplizieren


def format_content_types_for_prompt(milestone: str) -> str:
    """
    Formatiere Content-Types für LLM-Prompt.

    Args:
        milestone: Milestone-Bezeichnung

    Returns:
        Formatierter String für Prompt-Injection
    """
    config = get_milestone_config(milestone)
    lines = []

    for phase_name, phase_config in config["phases"].items():
        lines.append(f"\n### {phase_name.upper()} ({int(phase_config['weight']*100)}%)")
        lines.append(f"{phase_config['description']}")
        for t in phase_config["types"]:
            lines.append(f"  - {t}")

    return "\n".join(lines)
