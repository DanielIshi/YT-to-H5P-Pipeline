"""
Stage 2: Learning Path Planner

Plant die didaktische Reihenfolge und wählt Content-Types basierend auf:
- Strukturiertem Skript aus Stage 1
- Verfügbaren Content-Types für den Milestone
- Didaktischen Regeln (Passiv → Aktiv → Reflexion)
"""

import json
import os
from typing import TypedDict

import httpx

from ..config.milestones import (
    get_milestone_config,
    format_content_types_for_prompt,
    MilestoneConfig
)


class ActivityPlan(TypedDict):
    """Geplante Aktivität im Lernpfad"""
    order: int
    content_type: str
    concept_refs: list[str]
    rationale: str
    brief: str


class ColumnPlan(TypedDict):
    """Ein Column-Block mit mehreren Aktivitäten"""
    title: str
    phase: str  # "passive", "active", "reflect"
    activities: list[ActivityPlan]


class LearningPathPlan(TypedDict):
    """Output von Stage 2"""
    learning_path: list[ActivityPlan]  # Legacy: flache Liste
    columns: list[ColumnPlan]  # NEU: gruppierte Columns
    phase_distribution: dict[str, int]


def get_planner_prompt(milestone: str) -> str:
    """
    Generiere den Prompt für den Learning Path Planner.

    Args:
        milestone: Milestone-Bezeichnung (mvp, 1.1, 1.2, 1.3)

    Returns:
        Vollständiger Prompt mit Milestone-spezifischen Content-Types
    """
    config = get_milestone_config(milestone)
    content_types_formatted = format_content_types_for_prompt(milestone)

    # Extrahiere Content-Type Matching Regeln
    matching_rules = []
    for concept_type, types in config["content_type_matching"].items():
        matching_rules.append(f"- [{concept_type}] → {' ODER '.join(types)}")

    return f"""
Du bist ein E-Learning Didaktik-Experte, der Lernpfade plant.

VERFÜGBARE CONTENT-TYPES für Milestone "{config['name']}":
{content_types_formatted}

AUFGABE:
Erstelle einen Lernpfad-Plan mit THEMATISCHEN COLUMNS (Blöcken).
Jeder Column wird in Moodle als EIN Menüpunkt angezeigt.
Ziel: 3-4 Columns mit je 2-3 Aktivitäten (bildschirmfüllend, kein Scrollen).

COLUMN-STRUKTUR:
1. Column "Einführung" (passive Phase): Dialogcards + Accordion
2. Column "Wissenstest" (active Phase): TrueFalse + MultiChoice
3. Column "Anwendung" (active Phase): Blanks + DragText
4. Column "Abschluss" (reflect Phase): Summary

DIDAKTISCHE REGELN:
1. Beginne mit PASSIVEN Elementen (Einführung, Begriffe erklären)
2. Dann AKTIVE Elemente (Übungen, Quiz, Anwendung)
3. Ende mit REFLEXION (Summary - muss in letztem Column sein!)
4. Keine zwei gleichen Content-Types direkt hintereinander
5. 7-10 Aktivitäten insgesamt, verteilt auf 3-4 Columns
6. Pro Column 2-3 Aktivitäten (nicht mehr, damit Bildschirm gefüllt ohne Scroll)

CONTENT-TYPE MATCHING (wähle basierend auf Konzept-Typ):
{chr(10).join(matching_rules)}

OUTPUT FORMAT (JSON):
{{
  "columns": [
    {{
      "title": "Einführung: Grundbegriffe",
      "phase": "passive",
      "activities": [
        {{
          "order": 1,
          "content_type": "dialogcards",
          "concept_refs": ["Begriff1", "Begriff2"],
          "rationale": "Einführung der Kernbegriffe als Karteikarten",
          "brief": "Erstelle Karteikarten für: Begriff1 (Definition...), Begriff2 (Definition...)"
        }},
        {{
          "order": 2,
          "content_type": "accordion",
          "concept_refs": ["Prozess1"],
          "rationale": "Detaillierte Erklärung des Prozesses",
          "brief": "Erkläre die Schritte von Prozess1 in 3-4 Panels"
        }}
      ]
    }},
    {{
      "title": "Wissenstest: Fakten prüfen",
      "phase": "active",
      "activities": [
        {{
          "order": 3,
          "content_type": "truefalse",
          "concept_refs": ["Fakt1"],
          "rationale": "Schnelle Faktenprüfung",
          "brief": "Frage: 'Aussage über Fakt1' - Wahr/Falsch"
        }},
        {{
          "order": 4,
          "content_type": "multichoice",
          "concept_refs": ["Konzept1"],
          "rationale": "Verständnisprüfung mit Auswahl",
          "brief": "Frage: 'Was ist richtig über Konzept1?' mit 4 Optionen"
        }}
      ]
    }},
    {{
      "title": "Anwendung & Abschluss",
      "phase": "active",
      "activities": [
        {{
          "order": 5,
          "content_type": "blanks",
          "concept_refs": ["Begriff1"],
          "rationale": "Aktive Anwendung im Kontext",
          "brief": "Lückentext wo Begriff1 eingesetzt werden muss"
        }},
        {{
          "order": 6,
          "content_type": "summary",
          "concept_refs": ["Alle"],
          "rationale": "Kernpunkte zusammenfassen",
          "brief": "Fasse die wichtigsten Punkte zusammen"
        }}
      ]
    }}
  ],
  "learning_path": [/* Flache Liste aller activities in order */],
  "phase_distribution": {{
    "passive": 2,
    "active": 3,
    "reflect": 1
  }}
}}

WICHTIG:
- Column-Titel sollen thematisch passend und kurz sein (max 30 Zeichen)
- Der "brief" muss konkret genug sein, dass Stage 3 den Content generieren kann
- Referenziere nur Konzepte/Begriffe die im Skript vorkommen
- Summary MUSS im letzten Column sein
- "learning_path" enthält ALLE activities flach sortiert nach order (für Kompatibilität)

STRUKTURIERTES SKRIPT:
"""


async def call_openai(prompt: str, content: str) -> dict:
    """
    OpenAI API Call für Lernpfad-Planung.

    Args:
        prompt: Der Planner-Prompt
        content: Das strukturierte Skript als JSON

    Returns:
        Parsed JSON Response mit Lernpfad
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Du antwortest ausschliesslich mit validem JSON. Keine Markdown-Codeblöcke."
                    },
                    {
                        "role": "user",
                        "content": prompt + content
                    }
                ],
                "max_tokens": 3000,
                "temperature": 0.6,
                "response_format": {"type": "json_object"}
            },
            timeout=60.0
        )

        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

        result = response.json()
        content_str = result["choices"][0]["message"]["content"]

        return json.loads(content_str)


def validate_learning_path(
    plan: LearningPathPlan,
    config: MilestoneConfig
) -> tuple[bool, list[str]]:
    """
    Validiere den generierten Lernpfad gegen Milestone-Regeln.

    Args:
        plan: Der generierte Lernpfad
        config: Milestone-Konfiguration

    Returns:
        Tuple von (is_valid, error_messages)
    """
    errors = []
    rules = config["rules"]
    activities = plan.get("learning_path", [])

    # 1. Anzahl Aktivitäten
    if len(activities) < rules.get("min_activities", 8):
        errors.append(f"Too few activities: {len(activities)} < {rules['min_activities']}")
    if len(activities) > rules.get("max_activities", 12):
        errors.append(f"Too many activities: {len(activities)} > {rules['max_activities']}")

    # 2. Summary am Ende
    if rules.get("summary_position") == "last":
        if activities and activities[-1].get("content_type") != "summary":
            errors.append("Last activity must be 'summary'")

    # 3. Keine gleichen Types hintereinander
    max_consecutive = rules.get("max_consecutive_same_type", 1)
    consecutive_count = 1
    for i in range(1, len(activities)):
        if activities[i].get("content_type") == activities[i-1].get("content_type"):
            consecutive_count += 1
            if consecutive_count > max_consecutive:
                errors.append(
                    f"Too many consecutive same types at position {i}: "
                    f"{activities[i].get('content_type')}"
                )
        else:
            consecutive_count = 1

    # 4. Nur erlaubte Content-Types
    allowed_types = set()
    for phase in config["phases"].values():
        allowed_types.update(phase["types"])

    for activity in activities:
        ct = activity.get("content_type")
        if ct not in allowed_types:
            errors.append(f"Content type '{ct}' not allowed in milestone '{config['name']}'")

    return len(errors) == 0, errors


async def plan_learning_path(
    structured_script: dict,
    milestone: str = "mvp"
) -> LearningPathPlan:
    """
    Hauptfunktion: Plane Lernpfad basierend auf strukturiertem Skript.

    Args:
        structured_script: Output von Stage 1 (summarize_transcript)
        milestone: Milestone-Bezeichnung (mvp, 1.1, 1.2, 1.3)

    Returns:
        LearningPathPlan mit geordneten Aktivitäten und Content-Type Zuordnung
    """
    config = get_milestone_config(milestone)
    prompt = get_planner_prompt(milestone)

    # Script als JSON für Prompt
    script_json = json.dumps(structured_script, indent=2, ensure_ascii=False)

    print(f"Planning learning path for milestone '{milestone}'...")
    result = await call_openai(prompt, script_json)

    # Ensure legacy "learning_path" is present (flattened) even when LLM only returns columns
    if not result.get("learning_path") and result.get("columns"):
        flattened: list[ActivityPlan] = []
        next_order = 1

        for column in result.get("columns", []):
            for activity in column.get("activities", []):
                # Assign missing order sequentially to preserve didactic flow
                if "order" not in activity or activity.get("order") is None:
                    activity["order"] = next_order
                flattened.append(activity)
                next_order = max(next_order, activity["order"] + 1)

        # Sort by order to keep Stage 3 deterministic
        flattened.sort(key=lambda a: a.get("order", 0))
        result["learning_path"] = flattened

    # Compute simple phase distribution if LLM omitted it
    if not result.get("phase_distribution"):
        distribution = {"passive": 0, "active": 0, "reflect": 0}
        for activity in result.get("learning_path", []):
            ct = activity.get("content_type")
            for phase, cfg in config["phases"].items():
                if ct in cfg.get("types", []):
                    distribution[phase] += 1
                    break
        result["phase_distribution"] = distribution

    # Validierung
    is_valid, errors = validate_learning_path(result, config)
    if not is_valid:
        print(f"WARNING: Learning path validation failed:")
        for error in errors:
            print(f"  - {error}")

    return result


# Für direkten Aufruf
if __name__ == "__main__":
    import asyncio

    async def main():
        # Test mit Beispiel-Skript
        test_script = {
            "title": "Einführung in Machine Learning",
            "summary": "Machine Learning ist ein Teilbereich der KI, bei dem Algorithmen aus Daten lernen.",
            "sections": [
                {
                    "title": "Grundlagen",
                    "concepts": [
                        {
                            "type": "DEFINITION",
                            "term": "Machine Learning",
                            "explanation": "Ein Algorithmus lernt aus Trainingsdaten Muster zu erkennen"
                        },
                        {
                            "type": "DEFINITION",
                            "term": "Künstliche Intelligenz",
                            "explanation": "Oberbegriff für intelligente Maschinen"
                        }
                    ]
                },
                {
                    "title": "Der ML-Prozess",
                    "concepts": [
                        {
                            "type": "PROZESS",
                            "name": "ML-Training",
                            "steps": [
                                "Daten sammeln",
                                "Daten vorbereiten",
                                "Modell trainieren",
                                "Modell evaluieren"
                            ]
                        }
                    ]
                },
                {
                    "title": "Vergleich",
                    "concepts": [
                        {
                            "type": "VERGLEICH",
                            "item_a": "Traditionelle Programmierung",
                            "item_b": "Machine Learning",
                            "differences": [
                                "Regeln explizit vs. aus Daten gelernt",
                                "Deterministisch vs. probabilistisch"
                            ]
                        }
                    ]
                }
            ],
            "key_terms": ["Machine Learning", "Künstliche Intelligenz", "Training", "Modell"],
            "visual_opportunities": ["Der ML-Prozess als Flowchart"]
        }

        result = await plan_learning_path(test_script, milestone="mvp")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(main())
