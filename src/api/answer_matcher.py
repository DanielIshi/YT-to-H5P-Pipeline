"""
H5P Answer Matcher API
LLM-basiertes semantisches Matching für Spracheingaben

Endpoints:
- POST /api/match - Vergleicht gesprochene Antwort mit erwarteter Antwort
- GET /api/health - Health Check

Nutzung:
    uvicorn src.api.answer_matcher:app --host 0.0.0.0 --port 8085
"""

import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="H5P Answer Matcher",
    description="LLM-basiertes semantisches Matching für H5P Dialogcards",
    version="1.0.0"
)

# CORS für Browser-Zugriff
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Production einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== MODELS ==========

class MatchRequest(BaseModel):
    spoken: str  # Gesprochene Antwort (STT Transkript)
    expected: str  # Erwartete Antwort (Kartenrückseite)
    context: Optional[str] = None  # Optionaler Kontext (Frage)
    lang: str = "de"  # Sprache

class MatchResponse(BaseModel):
    match_score: int  # 0-100
    is_correct: bool  # True wenn score >= threshold
    feedback: str  # Feedback für den Lernenden
    spoken_normalized: str  # Normalisierte gesprochene Antwort
    expected_normalized: str  # Normalisierte erwartete Antwort


# ========== CONFIG ==========

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MATCH_THRESHOLD = 70  # Minimum Score für "korrekt"


# ========== LLM MATCHING ==========

MATCH_PROMPT = """Du bist ein Lern-Assistent, der gesprochene Antworten mit erwarteten Antworten vergleicht.

Kontext/Frage: {context}
Erwartete Antwort: {expected}
Gesprochene Antwort: {spoken}

Aufgabe:
1. Vergleiche die semantische Bedeutung (nicht nur exakte Wörter)
2. Berücksichtige Synonyme, Umschreibungen und Tippfehler
3. Ignoriere Füllwörter und grammatische Unterschiede

Bewerte:
- match_score: 0-100 (semantische Übereinstimmung)
  - 90-100: Exakt oder sehr nah
  - 70-89: Kernaussage korrekt
  - 50-69: Teilweise richtig
  - 0-49: Falsch oder unvollständig

- is_correct: true wenn score >= 70

- feedback: Kurzes, ermutigendes Feedback auf Deutsch
  - Bei Erfolg: Bestätigung + ggf. Ergänzung
  - Bei Fehler: Hinweis auf den richtigen Ansatz

Antworte NUR mit validem JSON:
{{"match_score": <int>, "is_correct": <bool>, "feedback": "<string>"}}"""


async def match_with_llm(spoken: str, expected: str, context: Optional[str] = None) -> dict:
    """Führt LLM-basiertes Matching durch"""

    if not OPENAI_API_KEY:
        # Fallback: Einfaches String-Matching
        logger.warning("No OPENAI_API_KEY - using fallback matching")
        return fallback_match(spoken, expected)

    prompt = MATCH_PROMPT.format(
        context=context or "Dialogkarte",
        expected=expected,
        spoken=spoken
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": "Du antwortest nur mit validem JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200
                }
            )

            if response.status_code != 200:
                logger.error(f"OpenAI API Error: {response.status_code} - {response.text}")
                return fallback_match(spoken, expected)

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Parse JSON response
            try:
                result = json.loads(content)
                return {
                    "match_score": result.get("match_score", 0),
                    "is_correct": result.get("is_correct", False),
                    "feedback": result.get("feedback", "")
                }
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response: {content}")
                return fallback_match(spoken, expected)

    except Exception as e:
        logger.error(f"LLM matching error: {e}")
        return fallback_match(spoken, expected)


def fallback_match(spoken: str, expected: str) -> dict:
    """Fallback: Dice-Koeffizient für String-Ähnlichkeit"""

    def normalize(s: str) -> str:
        return s.lower().strip()

    def dice_coefficient(s1: str, s2: str) -> float:
        if s1 == s2:
            return 1.0
        if len(s1) < 2 or len(s2) < 2:
            return 0.0

        bigrams1 = set(s1[i:i+2] for i in range(len(s1) - 1))
        bigrams2 = set(s2[i:i+2] for i in range(len(s2) - 1))

        intersection = len(bigrams1 & bigrams2)
        return (2 * intersection) / (len(bigrams1) + len(bigrams2))

    s1 = normalize(spoken)
    s2 = normalize(expected)

    score = int(dice_coefficient(s1, s2) * 100)
    is_correct = score >= MATCH_THRESHOLD

    if is_correct:
        feedback = f"Richtig! ({score}% Übereinstimmung)"
    elif score >= 50:
        feedback = f"Fast richtig! Die erwartete Antwort war: {expected}"
    else:
        feedback = f"Leider nicht korrekt. Die richtige Antwort ist: {expected}"

    return {
        "match_score": score,
        "is_correct": is_correct,
        "feedback": feedback
    }


def normalize_text(text: str) -> str:
    """Normalisiert Text für Vergleich"""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)  # Entferne Satzzeichen
    text = re.sub(r'\s+', ' ', text)  # Normalisiere Whitespace
    return text


# ========== ENDPOINTS ==========

@app.get("/api/health")
async def health():
    """Health Check"""
    return {
        "status": "ok",
        "service": "H5P Answer Matcher",
        "version": "1.0.0",
        "llm_enabled": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL if OPENAI_API_KEY else "fallback"
    }


@app.post("/api/match", response_model=MatchResponse)
async def match_answer(request: MatchRequest):
    """
    Vergleicht gesprochene Antwort mit erwarteter Antwort.

    Nutzt GPT-4o-mini für semantisches Matching.
    Fallback auf Dice-Koeffizient wenn kein API Key.
    """

    if not request.spoken or not request.expected:
        raise HTTPException(status_code=400, detail="spoken and expected are required")

    # Normalisiere Texte
    spoken_norm = normalize_text(request.spoken)
    expected_norm = normalize_text(request.expected)

    # Quick check: Exakte Übereinstimmung
    if spoken_norm == expected_norm:
        return MatchResponse(
            match_score=100,
            is_correct=True,
            feedback="Perfekt! Genau richtig.",
            spoken_normalized=spoken_norm,
            expected_normalized=expected_norm
        )

    # LLM Matching
    result = await match_with_llm(
        spoken=request.spoken,
        expected=request.expected,
        context=request.context
    )

    return MatchResponse(
        match_score=result["match_score"],
        is_correct=result["is_correct"],
        feedback=result["feedback"],
        spoken_normalized=spoken_norm,
        expected_normalized=expected_norm
    )


# ========== MAIN ==========

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8085))
    uvicorn.run(app, host="0.0.0.0", port=port)
