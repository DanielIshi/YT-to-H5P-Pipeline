"""
Stage 3: H5P Content Generator

Generiert den konkreten H5P-Content für jede geplante Aktivität.
- Nutzt den Brief aus Stage 2
- Generiert type-spezifischen Content
- Validiert gegen H5P-Schema
"""

import json
import os
from typing import Any

import httpx

from ..config.content_types import (
    get_content_type_schema,
    get_llm_schema_for_prompt,
    validate_content
)


def extract_relevant_concepts(
    structured_script: dict,
    concept_refs: list[str]
) -> list[dict]:
    """
    Extrahiere relevante Konzepte aus dem strukturierten Skript.

    Args:
        structured_script: Output von Stage 1
        concept_refs: Liste von Konzept-Referenzen aus dem Activity-Plan

    Returns:
        Liste der relevanten Konzepte
    """
    relevant = []

    # Durchsuche alle Sections nach referenzierten Konzepten
    for section in structured_script.get("sections", []):
        for concept in section.get("concepts", []):
            # Prüfe ob dieses Konzept referenziert wird
            concept_name = concept.get("term") or concept.get("name") or concept.get("statement", "")

            for ref in concept_refs:
                if ref.lower() in concept_name.lower() or concept_name.lower() in ref.lower():
                    relevant.append(concept)
                    break

    # Fallback: Wenn keine Konzepte gefunden, nimm alle aus passender Section
    if not relevant:
        for section in structured_script.get("sections", []):
            for ref in concept_refs:
                if ref.lower() in section.get("title", "").lower():
                    relevant.extend(section.get("concepts", []))

    return relevant


def get_generator_prompt(content_type: str, activity_brief: str) -> str:
    """
    Generiere den Prompt für einen spezifischen Content-Type.

    Args:
        content_type: Name des Content-Types
        activity_brief: Der Brief aus Stage 2 (was generiert werden soll)

    Returns:
        Vollständiger Prompt für Content-Generierung
    """
    schema = get_llm_schema_for_prompt(content_type)
    schema_obj = get_content_type_schema(content_type)

    # Type-spezifische Hinweise
    type_hints = {
        "truefalse": """
WICHTIG für TrueFalse:
- "correct" muss ein boolean sein (true oder false)
- Formuliere die Aussage so, dass sie eindeutig wahr ODER falsch ist
- Vermeide "manchmal", "oft", "kann" - diese machen Aussagen mehrdeutig
""",
        "blanks": """
WICHTIG für Blanks:
- Markiere Lücken mit *Sternchen*, z.B.: "Das wichtigste Konzept ist *Machine Learning*"
- 2-5 Lücken pro Text
- Die Lücken-Wörter sollten Schlüsselbegriffe sein
""",
        "dragtext": """
WICHTIG für DragText:
- Markiere Drag-Wörter mit *Sternchen*, z.B.: "*KI* ist ein Teilbereich der *Informatik*"
- 3-6 Drag-Wörter
- Die Wörter werden zu Drag-Items
""",
        "multichoice": """
WICHTIG für MultiChoice:
- Genau EINE Antwort muss correct: true sein
- 3-5 Antwortoptionen
- Falsche Antworten sollten plausibel aber eindeutig falsch sein
""",
        "summary": """
WICHTIG für Summary:
- "statements" ist ein Array von Gruppen
- Jede Gruppe hat genau EINE "correct" Aussage und 2-3 "wrong" Aussagen
- Die richtige Aussage muss die wichtigste Kernaussage sein
""",
        "dialogcards": """
WICHTIG für Dialogcards:
- "front" = Begriff oder Frage (kurz)
- "back" = Definition oder Antwort (kann länger sein)
- 3-8 Karten
""",
        "accordion": """
WICHTIG für Accordion:
- "panels" = aufklappbare Abschnitte
- Jedes Panel hat "title" und "content" (HTML erlaubt)
- 2-6 Panels
"""
    }

    hint = type_hints.get(content_type, "")

    return f"""
Generiere H5P-Content für den Typ: {content_type}
{schema_obj['description']}

AUFGABE:
{activity_brief}

OUTPUT SCHEMA:
{schema}
{hint}

REGELN:
- Deutsche Sprache
- Keine Emojis
- Korrekte Antworten müssen eindeutig sein
- Halte dich exakt an das Schema

KONZEPTE AUS DEM SKRIPT:
"""


async def call_openai(prompt: str, concepts_json: str) -> dict:
    """
    OpenAI API Call für Content-Generierung.

    Args:
        prompt: Der Generator-Prompt
        concepts_json: Relevante Konzepte als JSON

    Returns:
        Parsed JSON Response mit H5P Content
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
                        "content": prompt + concepts_json
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.7,
                "response_format": {"type": "json_object"}
            },
            timeout=45.0
        )

        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

        result = response.json()
        content_str = result["choices"][0]["message"]["content"]

        return json.loads(content_str)


async def generate_h5p_content(
    activity: dict,
    structured_script: dict
) -> dict:
    """
    Hauptfunktion: Generiere H5P-Content für eine Aktivität.

    Args:
        activity: Eine Aktivität aus dem Lernpfad-Plan (Stage 2 Output)
        structured_script: Das strukturierte Skript (Stage 1 Output)

    Returns:
        H5P-fähiger Content für den spezifischen Content-Type
    """
    content_type = activity["content_type"]
    brief = activity.get("brief", "")
    concept_refs = activity.get("concept_refs", [])

    # 1. Extrahiere relevante Konzepte
    concepts = extract_relevant_concepts(structured_script, concept_refs)

    # Fallback: Wenn keine Konzepte gefunden, nutze key_terms
    if not concepts:
        concepts = [{"term": term} for term in structured_script.get("key_terms", [])]

    # 2. Generiere Prompt
    prompt = get_generator_prompt(content_type, brief)
    concepts_json = json.dumps(concepts, indent=2, ensure_ascii=False)

    # 3. OpenAI Call
    print(f"Generating content for '{content_type}': {activity.get('order', '?')}...")
    result = await call_openai(prompt, concepts_json)

    # 4. Validierung
    is_valid, errors = validate_content(content_type, result)
    if not is_valid:
        print(f"WARNING: Content validation failed for {content_type}:")
        for error in errors:
            print(f"  - {error}")

    # 5. Füge Metadaten hinzu
    result["_meta"] = {
        "content_type": content_type,
        "order": activity.get("order"),
        "concept_refs": concept_refs,
        "rationale": activity.get("rationale", "")
    }

    return result


async def generate_all_content(
    learning_path: dict,
    structured_script: dict
) -> list[dict]:
    """
    Generiere Content für alle Aktivitäten im Lernpfad.

    Args:
        learning_path: Output von Stage 2 (plan_learning_path)
        structured_script: Output von Stage 1 (summarize_transcript)

    Returns:
        Liste von H5P-Content Objekten
    """
    activities = learning_path.get("learning_path", [])
    results = []

    for activity in activities:
        try:
            content = await generate_h5p_content(activity, structured_script)
            results.append(content)
        except Exception as e:
            print(f"ERROR generating content for activity {activity.get('order')}: {e}")
            results.append({
                "_error": str(e),
                "_activity": activity
            })

    return results


# Für direkten Aufruf
if __name__ == "__main__":
    import asyncio

    async def main():
        # Test mit Beispiel-Aktivität
        test_activity = {
            "order": 1,
            "content_type": "truefalse",
            "concept_refs": ["Machine Learning"],
            "rationale": "Test ob Grundverständnis vorhanden",
            "brief": "Erstelle eine Wahr/Falsch-Aussage über Machine Learning"
        }

        test_script = {
            "title": "ML Basics",
            "summary": "Machine Learning lernt aus Daten",
            "sections": [
                {
                    "title": "Definition",
                    "concepts": [
                        {
                            "type": "DEFINITION",
                            "term": "Machine Learning",
                            "explanation": "Ein Algorithmus der aus Trainingsdaten Muster erkennt"
                        }
                    ]
                }
            ],
            "key_terms": ["Machine Learning", "Algorithmus", "Training"]
        }

        result = await generate_h5p_content(test_activity, test_script)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(main())
