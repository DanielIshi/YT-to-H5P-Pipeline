"""
Stage 1: Transcript Summarizer

Wandelt rohe YouTube-Untertitel in ein strukturiertes Lern-Skript um.
- Entfernt Füllwörter und Wiederholungen
- Identifiziert Kernkonzepte mit Tags
- Strukturiert in logische Abschnitte
- Cached Ergebnisse in Supabase
"""

import hashlib
import json
import os
from typing import TypedDict

import httpx

# Supabase Config
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://148.230.71.150:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


class Concept(TypedDict):
    """Ein identifiziertes Konzept aus dem Transcript"""
    type: str  # DEFINITION, PROZESS, VERGLEICH, FAKT, BEISPIEL
    content: dict  # Type-spezifische Felder


class Section(TypedDict):
    """Ein logischer Abschnitt des Skripts"""
    title: str
    concepts: list[Concept]


class StructuredScript(TypedDict):
    """Output von Stage 1"""
    title: str
    summary: str
    sections: list[Section]
    key_terms: list[str]
    visual_opportunities: list[str]


SUMMARIZER_PROMPT = """
Du bist ein Experte für didaktische Aufbereitung von Video-Inhalten.

AUFGABE:
Analysiere das folgende YouTube-Transcript und erstelle ein strukturiertes Lern-Skript.

SCHRITTE:
1. Entferne Füllwörter, Wiederholungen, "äh"s, Begrüßungen
2. Identifiziere Kernkonzepte und tagge sie:
   - DEFINITION: Begriffserklärungen ("X ist...", "X bedeutet...")
   - PROZESS: Abläufe/Schritte ("Zuerst..., dann..., schließlich...")
   - VERGLEICH: A vs B Gegenüberstellungen ("Im Gegensatz zu...", "Anders als...")
   - FAKT: Einzelne Fakten, Zahlen, Daten
   - BEISPIEL: Konkrete Beispiele ("Zum Beispiel...", "Ein Beispiel wäre...")
3. Strukturiere in logische Abschnitte (3-6 Abschnitte)
4. Markiere was visuell besser erklärt werden könnte

OUTPUT FORMAT (JSON):
{
  "title": "Prägnanter Titel des Themas",
  "summary": "2-3 Sätze Zusammenfassung des Kerninhhalts",
  "sections": [
    {
      "title": "Abschnitt 1: Einführung",
      "concepts": [
        {
          "type": "DEFINITION",
          "term": "Begriff",
          "explanation": "Kurze, klare Erklärung"
        },
        {
          "type": "PROZESS",
          "name": "Prozessname",
          "steps": ["Schritt 1", "Schritt 2", "Schritt 3"]
        },
        {
          "type": "VERGLEICH",
          "item_a": "Konzept A",
          "item_b": "Konzept B",
          "differences": ["Unterschied 1", "Unterschied 2"]
        },
        {
          "type": "FAKT",
          "statement": "Eine wichtige Tatsache",
          "is_common_misconception": false
        },
        {
          "type": "BEISPIEL",
          "context": "Wofür ist das ein Beispiel",
          "example": "Das konkrete Beispiel"
        }
      ]
    }
  ],
  "key_terms": ["Begriff1", "Begriff2", "Begriff3"],
  "visual_opportunities": [
    "Der Prozess X könnte als Flowchart visualisiert werden",
    "Der Vergleich Y eignet sich für eine Gegenüberstellung"
  ]
}

REGELN:
- Maximal 6 Abschnitte
- Maximal 5 Konzepte pro Abschnitt
- Kurze, prägnante Formulierungen
- Deutsche Sprache
- Keine Emojis
- Nur relevante Inhalte (keine Werbung, Sponsoren, etc.)

TRANSCRIPT:
"""


def compute_transcript_hash(transcript: str) -> str:
    """Berechne SHA256 Hash des Transcripts für Cache-Invalidierung"""
    return hashlib.sha256(transcript.encode("utf-8")).hexdigest()


async def get_cached_script(youtube_url_id: int, transcript_hash: str) -> StructuredScript | None:
    """
    Prüfe ob ein gecachtes strukturiertes Skript existiert.

    Args:
        youtube_url_id: ID aus youtube_urls Tabelle
        transcript_hash: SHA256 Hash des Transcripts

    Returns:
        Gecachtes Skript oder None
    """
    if not SUPABASE_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/structured_scripts",
                params={
                    "youtube_url_id": f"eq.{youtube_url_id}",
                    "transcript_hash": f"eq.{transcript_hash}",
                    "select": "structured_script"
                },
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]["structured_script"]
    except Exception as e:
        print(f"Cache lookup failed: {e}")

    return None


async def cache_script(
    youtube_url_id: int,
    transcript_hash: str,
    script: StructuredScript
) -> bool:
    """
    Speichere strukturiertes Skript im Cache.

    Args:
        youtube_url_id: ID aus youtube_urls Tabelle
        transcript_hash: SHA256 Hash des Transcripts
        script: Das strukturierte Skript

    Returns:
        True wenn erfolgreich gespeichert
    """
    if not SUPABASE_KEY:
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/structured_scripts",
                json={
                    "youtube_url_id": youtube_url_id,
                    "transcript_hash": transcript_hash,
                    "structured_script": script,
                    "concepts": script.get("key_terms", [])
                },
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                timeout=10.0
            )

            return response.status_code in (200, 201)
    except Exception as e:
        print(f"Cache write failed: {e}")
        return False


async def call_openai(prompt: str, content: str) -> dict:
    """
    OpenAI API Call für Transcript-Zusammenfassung.

    Args:
        prompt: System/User Prompt
        content: Das Transcript

    Returns:
        Parsed JSON Response
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    # Transcript kürzen wenn zu lang
    max_chars = 18000
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[... gekürzt ...]"

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
                "temperature": 0.5,  # Niedrigere Temperatur für konsistentere Struktur
                "response_format": {"type": "json_object"}
            },
            timeout=60.0
        )

        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

        result = response.json()
        content_str = result["choices"][0]["message"]["content"]

        return json.loads(content_str)


async def summarize_transcript(
    transcript: str,
    youtube_url_id: int | None = None,
    force: bool = False
) -> StructuredScript:
    """
    Hauptfunktion: Wandle Transcript in strukturiertes Skript um.

    Args:
        transcript: Rohe YouTube-Untertitel
        youtube_url_id: Optional, für Caching in Supabase
        force: Ignoriere Cache und generiere neu

    Returns:
        StructuredScript mit Abschnitten, Konzepten, Key Terms
    """
    transcript_hash = compute_transcript_hash(transcript)

    # 1. Cache prüfen (wenn nicht force)
    if not force and youtube_url_id:
        cached = await get_cached_script(youtube_url_id, transcript_hash)
        if cached:
            print(f"Using cached script for youtube_url_id={youtube_url_id}")
            return cached

    # 2. OpenAI Call
    print("Calling OpenAI for transcript summarization...")
    result = await call_openai(SUMMARIZER_PROMPT, transcript)

    # 3. Validierung
    required_fields = ["title", "summary", "sections", "key_terms"]
    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing required field in response: {field}")

    # 4. Cache speichern
    if youtube_url_id:
        success = await cache_script(youtube_url_id, transcript_hash, result)
        if success:
            print(f"Cached script for youtube_url_id={youtube_url_id}")

    return result


# Für direkten Aufruf
if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        # Test mit einem Beispiel-Transcript
        test_transcript = """
        Willkommen zu unserem Video über künstliche Intelligenz.
        KI, oder künstliche Intelligenz, ist ein Teilbereich der Informatik.
        Sie beschäftigt sich damit, Maschinen intelligent zu machen.

        Machine Learning ist ein wichtiger Teil von KI.
        Dabei lernt ein Algorithmus aus Daten.
        Zuerst werden Trainingsdaten gesammelt.
        Dann wird ein Modell trainiert.
        Schließlich kann das Modell Vorhersagen treffen.

        Im Gegensatz zu traditioneller Programmierung, wo Regeln explizit definiert werden,
        lernt Machine Learning die Regeln aus Beispielen.

        Ein Beispiel: Spam-Erkennung in E-Mails nutzt ML.
        Das System lernt aus tausenden E-Mails, welche Spam sind.

        Zusammenfassend: KI macht Maschinen intelligent, ML ist der Lernprozess dahinter.
        """

        result = await summarize_transcript(test_transcript)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(main())
