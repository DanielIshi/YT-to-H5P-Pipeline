● Der Plan ist jetzt vollständig mit:

  1. 3-Stufen-Architektur (Summarizer → Planner → Generator)
  2. Milestone-spezifische Configs (MVP, 1.1, 1.2, 1.3)
  3. Supabase Caching für strukturierte Skripte
  4. Tests für die "richtige Mischung"
  5. Konkrete Prompts für jede Stufe
  6. Implementation-Reihenfolge

● User approved Claude's plan
  ⎿  Plan saved to: ~\.claude\plans\virtual-sprouting-deer.md · /plan to edit
     Plan: Mehrstufige LLM-Pipeline mit Milestone-spezifischen Prompts

     Kontext

     - 4 Milestones definiert: MVP 1.0, Post-MVP 1.1 (UX), 1.2 (Media), 1.3 (Multimodal)
     - Jeder Milestone hat unterschiedliche Content-Types verfügbar
     - Aktueller Prompt (LEARNING_PATH_PROMPT) ist statisch mit allen 9 Types
     - YouTube-Transcripts sind oft unstrukturiert und brauchen Aufbereitung

     Ziel

     Mehrstufige Pipeline die:
     1. Transcript aufbereitet und strukturiert
     2. Didaktisch plant welche Content-Types passen
     3. Milestone-spezifisch nur verfügbare Types nutzt
     4. Testbar ist für "richtige Mischung"

     Architektur: 3-Stufen-Pipeline

     ┌─────────────────────────────────────────────────────────────┐
     │ STUFE 1: TRANSCRIPT AUFBEREITUNG                            │
     │ Input:  Rohe YouTube-Untertitel                            │
     │ Agent:  "Transcript Summarizer"                            │
     │ Output: Strukturiertes Lern-Skript                         │
     │         - Kernkonzepte identifiziert                       │
     │         - Logische Abschnitte                              │
     │         - Visuelle Elemente markiert (Prozesse, Vergleiche)│
     └─────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
     ┌─────────────────────────────────────────────────────────────┐
     │ STUFE 2: DIDAKTISCHE PLANUNG                                │
     │ Input:  Strukturiertes Skript + Milestone-Config           │
     │ Agent:  "Learning Path Planner"                            │
     │ Output: Lernpfad-Plan mit Content-Type Empfehlungen        │
     │         - Aktivitäten-Reihenfolge                          │
     │         - Passende Content-Types pro Konzept               │
     │         - Begründung warum dieser Type                     │
     └─────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
     ┌─────────────────────────────────────────────────────────────┐
     │ STUFE 3: H5P CONTENT GENERIERUNG                            │
     │ Input:  Lernpfad-Plan                                      │
     │ Agent:  "H5P Content Generator"                            │
     │ Output: Fertige H5P JSON-Strukturen                        │
     │         - Konkrete Fragen/Antworten                        │
     │         - Type-spezifische Felder                          │
     └─────────────────────────────────────────────────────────────┘

     Milestone-Konfigurationen

     MVP 1.0 (7 Types)

     MVP_CONTENT_TYPES = {
         "passive": ["dialogcards", "accordion"],
         "active": ["truefalse", "blanks", "dragtext", "multichoice"],
         "reflect": ["summary"]
     }

     Post-MVP 1.1 - UX (7 Types + Verbesserungen)

     - Gleiche Types wie MVP
     - Zusätzlich: Auto-Weiter Logik im Prompt

     Post-MVP 1.2 - Media (+ 3 Types)

     MEDIA_CONTENT_TYPES = {
         ...MVP_CONTENT_TYPES,
         "visual": ["imagehotspots", "interactivevideo"],
         "audio": ["audiosummary"]  # NEU: ElevenLabs generiert
     }

     Post-MVP 1.3 - Multimodal (+ Speech)

     MULTIMODAL_CONTENT_TYPES = {
         ...MEDIA_CONTENT_TYPES,
         "speech": ["speechinput_quiz"]  # NEU: Spracheingabe
     }

     Prompts pro Stufe

     Prompt 1: Transcript Summarizer

     - Entferne Füllwörter, Wiederholungen
     - Identifiziere Kernkonzepte (mit Tags: [DEFINITION], [PROZESS], [VERGLEICH])
     - Strukturiere in logische Abschnitte
     - Markiere was visuell erklärt werden könnte

     Prompt 2: Learning Path Planner

     - Erhalte: Strukturiertes Skript + verfügbare Content-Types
     - Plane didaktische Reihenfolge (Passiv → Aktiv → Reflexion)
     - Wähle Content-Type basierend auf Inhaltstyp:
       - [DEFINITION] → Dialogcards oder Blanks
       - [PROZESS] → DragText oder InteractiveVideo
       - [VERGLEICH] → TrueFalse oder MultiChoice
     - Output: JSON mit Begründung

     Prompt 3: H5P Content Generator

     - Erhalte: Einzelne Aktivität aus Plan
     - Generiere type-spezifischen Content
     - Validiere gegen Schema

     Tests für "richtige Mischung"

     Test-Kriterien

     1. Varianz: Keine 2 gleichen Types hintereinander
     2. Balance: ~25% passiv, ~50% aktiv, ~25% reflektiv
     3. Didaktik: Passiv vor Aktiv, Summary am Ende
     4. Vollständigkeit: Alle Kernkonzepte abgedeckt

     Test-Implementation

     def test_learning_path_mix(activities: list) -> dict:
         """Validiert die Mischung eines generierten Lernpfads"""
         return {
             "variance_ok": check_no_consecutive_same_type(activities),
             "balance_ok": check_phase_distribution(activities),
             "didactic_ok": check_passive_before_active(activities),
             "coverage_ok": check_concepts_covered(activities, concepts)
         }

     Zu ändernde Dateien

     1. src/h5p/learning_path_generator.py
       - Aufteilen in 3 separate Funktionen/Prompts
       - Milestone-Config Parameter hinzufügen
     2. src/h5p/prompts/ (NEU)
       - transcript_summarizer.py
       - learning_path_planner.py
       - h5p_content_generator.py
     3. src/h5p/milestone_config.py (NEU)
       - Content-Type Definitionen pro Milestone
       - Gewichtungen und Regeln
     4. tests/test_learning_path_mix.py (NEU)
       - Validierung der generierten Mischung

     Entscheidungen (User-Feedback)

     1. 3 separate API-Calls - Jede Stufe ist ein eigener OpenAI-Call (einfacher zu debuggen)
     2. Caching in Supabase - Strukturiertes Skript wird gespeichert für Iteration
     3. Komplett neu schreiben - Saubere 3-Stufen-Architektur statt Erweiterung

     Implementierungsplan

     Phase 1: Neue Dateistruktur

     src/h5p/
     ├── pipeline/                    # NEU: 3-Stufen-Pipeline
     │   ├── __init__.py
     │   ├── stage1_summarizer.py     # Transcript → Strukturiertes Skript
     │   ├── stage2_planner.py        # Skript → Lernpfad-Plan
     │   └── stage3_generator.py      # Plan → H5P Content
     ├── config/                      # NEU: Milestone-Configs
     │   ├── __init__.py
     │   ├── milestones.py            # MVP, Post-MVP 1.1/1.2/1.3
     │   └── content_types.py         # Type-Definitionen & Schemas
     ├── builders/                    # REFACTOR: Aus learning_path_generator.py
     │   ├── __init__.py
     │   ├── truefalse.py
     │   ├── blanks.py
     │   ├── dragtext.py
     │   ├── summary.py
     │   ├── multichoice.py
     │   ├── dialogcards.py
     │   └── accordion.py
     ├── learning_path_generator.py   # DEPRECATED: Wird durch pipeline/ ersetzt
     └── run_pipeline.py              # NEU: CLI Entry Point

     Phase 2: Supabase Schema-Erweiterung

     -- Neue Tabelle für gecachte strukturierte Skripte
     CREATE TABLE structured_scripts (
         id SERIAL PRIMARY KEY,
         youtube_url_id INT REFERENCES youtube_urls(id),
         transcript_hash VARCHAR(64),           -- SHA256 für Invalidierung
         structured_script JSONB,               -- Stufe 1 Output
         concepts JSONB,                         -- Extrahierte Kernkonzepte
         created_at TIMESTAMP DEFAULT NOW()
     );

     -- Index für schnelle Lookups
     CREATE INDEX idx_scripts_url ON structured_scripts(youtube_url_id);
     CREATE INDEX idx_scripts_hash ON structured_scripts(transcript_hash);

     Phase 3: Implementation der 3 Stufen

     Stufe 1: stage1_summarizer.py

     SUMMARIZER_PROMPT = """
     Du bist ein Experte für didaktische Aufbereitung von Video-Inhalten.

     AUFGABE:
     Analysiere das folgende YouTube-Transcript und erstelle ein strukturiertes Lern-Skript.

     SCHRITTE:
     1. Entferne Füllwörter, Wiederholungen, "äh"s
     2. Identifiziere Kernkonzepte und tagge sie:
        - [DEFINITION] für Begriffserklärungen
        - [PROZESS] für Abläufe/Schritte
        - [VERGLEICH] für A vs B Gegenüberstellungen
        - [FAKT] für einzelne Fakten
        - [BEISPIEL] für konkrete Beispiele
     3. Strukturiere in logische Abschnitte
     4. Markiere was visuell besser erklärt werden könnte [VISUAL]

     OUTPUT FORMAT (JSON):
     {
       "title": "Thema des Videos",
       "summary": "2-3 Sätze Zusammenfassung",
       "sections": [
         {
           "title": "Abschnitt 1",
           "concepts": [
             {"type": "DEFINITION", "term": "Begriff", "explanation": "..."},
             {"type": "PROZESS", "steps": ["Schritt 1", "Schritt 2"]},
             {"type": "FAKT", "statement": "...", "is_common_misconception": false}
           ]
         }
       ],
       "key_terms": ["Begriff1", "Begriff2"],
       "visual_opportunities": ["Prozess X könnte als Flowchart dargestellt werden"]
     }
     """

     async def summarize_transcript(transcript: str, youtube_url_id: int) -> dict:
         # 1. Check cache
         cached = await get_cached_script(youtube_url_id, transcript)
         if cached:
             return cached

         # 2. Call OpenAI
         response = await call_openai(SUMMARIZER_PROMPT, transcript)

         # 3. Cache result
         await cache_script(youtube_url_id, transcript, response)

         return response

     Stufe 2: stage2_planner.py

     def get_planner_prompt(milestone: str) -> str:
         config = MILESTONE_CONFIGS[milestone]
         available_types = config["content_types"]

         return f"""
     Du bist ein E-Learning Didaktik-Experte.

     VERFÜGBARE CONTENT-TYPES für {milestone}:
     {format_content_types(available_types)}

     AUFGABE:
     Erstelle einen Lernpfad-Plan basierend auf dem strukturierten Skript.

     REGELN:
     1. Beginne mit passiven Elementen (Dialogcards, Accordion)
     2. Dann aktive Elemente (Blanks, DragText, MultiChoice, TrueFalse)
     3. Ende mit Reflexion (Summary)
     4. Keine zwei gleichen Types hintereinander
     5. 8-12 Aktivitäten total
     6. Jede Aktivität braucht Begründung

     CONTENT-TYPE MATCHING:
     - [DEFINITION] → dialogcards ODER blanks
     - [PROZESS] → dragtext ODER multichoice (Reihenfolge)
     - [VERGLEICH] → truefalse ODER multichoice
     - [FAKT] → truefalse (Mythos vs Fakt)
     - [BEISPIEL] → blanks (Lückentext mit Beispiel)

     OUTPUT FORMAT (JSON):
     {{
       "learning_path": [
         {{
           "order": 1,
           "content_type": "dialogcards",
           "concept_refs": ["Begriff1", "Begriff2"],
           "rationale": "Einführung der Kernbegriffe als Karteikarten",
           "brief": "Zeige Definition von Begriff1 und Begriff2"
         }}
       ],
       "phase_distribution": {{
         "passive": 2,
         "active": 6,
         "reflect": 1
       }}
     }}
     """

     Stufe 3: stage3_generator.py

     def get_generator_prompt(content_type: str) -> str:
         schema = CONTENT_TYPE_SCHEMAS[content_type]

         return f"""
     Generiere H5P-Content für den Typ: {content_type}

     SCHEMA:
     {json.dumps(schema, indent=2)}

     AUFGABE:
     Basierend auf dem Konzept-Brief, erstelle den vollständigen Content.

     REGELN:
     - Deutsche Sprache
     - Keine Emojis
     - Korrekte Antworten müssen eindeutig sein
     - Bei Blanks: *Sternchen* für Lücken
     - Bei DragText: *Sternchen* für Drag-Wörter
     """

     async def generate_h5p_content(activity: dict, structured_script: dict) -> dict:
         content_type = activity["content_type"]
         prompt = get_generator_prompt(content_type)

         # Finde relevante Konzepte aus dem Skript
         concepts = extract_concepts(structured_script, activity["concept_refs"])

         response = await call_openai(prompt, json.dumps(concepts))

         # Validiere gegen Schema
         validate_h5p_schema(response, content_type)

         return response

     Phase 4: Tests für "richtige Mischung"

     # tests/test_learning_path_mix.py

     def test_no_consecutive_same_type(activities: list) -> bool:
         """Prüft dass keine 2 gleichen Types hintereinander kommen"""
         for i in range(len(activities) - 1):
             if activities[i]["content_type"] == activities[i+1]["content_type"]:
                 return False
         return True

     def test_phase_distribution(activities: list, config: dict) -> bool:
         """Prüft ~25% passiv, ~50% aktiv, ~25% reflektiv"""
         passive = sum(1 for a in activities if a["content_type"] in config["passive"])
         active = sum(1 for a in activities if a["content_type"] in config["active"])
         reflect = sum(1 for a in activities if a["content_type"] in config["reflect"])

         total = len(activities)
         return (
             0.15 <= passive/total <= 0.35 and  # 15-35% passiv
             0.40 <= active/total <= 0.60 and   # 40-60% aktiv
             0.10 <= reflect/total <= 0.25      # 10-25% reflektiv
         )

     def test_didactic_order(activities: list, config: dict) -> bool:
         """Prüft dass passive vor aktiven kommen, Summary am Ende"""
         first_active_idx = next(
             (i for i, a in enumerate(activities) if a["content_type"] in config["active"]),
             len(activities)
         )
         last_passive_idx = max(
             (i for i, a in enumerate(activities) if a["content_type"] in config["passive"]),
             default=-1
         )

         # Summary muss am Ende sein
         if activities[-1]["content_type"] != "summary":
             return False

         # Passive sollten vor Aktiven sein (mit Toleranz)
         return last_passive_idx < first_active_idx + 2

     def test_all_concepts_covered(activities: list, concepts: list) -> bool:
         """Prüft dass alle Kernkonzepte in mindestens einer Aktivität vorkommen"""
         covered = set()
         for a in activities:
             covered.update(a.get("concept_refs", []))
         return set(concepts).issubset(covered)

     Phase 5: CLI Entry Point

     # src/h5p/run_pipeline.py

     @click.command()
     @click.option("--youtube-url-id", type=int, required=True)
     @click.option("--milestone", type=click.Choice(["mvp", "1.1", "1.2", "1.3"]), default="mvp")
     @click.option("--courseid", type=int, default=2)
     @click.option("--skip-cache", is_flag=True, help="Ignoriere gecachtes Skript")
     async def run_pipeline(youtube_url_id: int, milestone: str, courseid: int, skip_cache: bool):
         """3-Stufen H5P Generation Pipeline"""

         # 1. Hole Transcript aus Supabase
         transcript = await get_transcript(youtube_url_id)

         # 2. Stufe 1: Strukturiertes Skript
         if skip_cache:
             structured = await summarize_transcript(transcript, youtube_url_id, force=True)
         else:
             structured = await summarize_transcript(transcript, youtube_url_id)

         # 3. Stufe 2: Lernpfad-Planung
         learning_path = await plan_learning_path(structured, milestone)

         # 4. Validiere Mischung
         validation = validate_mix(learning_path, MILESTONE_CONFIGS[milestone])
         if not validation["all_ok"]:
             print(f"WARNING: Mix validation failed: {validation}")

         # 5. Stufe 3: H5P Generierung & Import
         results = []
         for activity in learning_path["learning_path"]:
             h5p_content = await generate_h5p_content(activity, structured)
             h5p_package = build_h5p_package(activity["content_type"], h5p_content)
             result = await import_to_moodle(h5p_package, activity["title"], courseid)
             results.append(result)

         print(json.dumps({"status": "success", "activities": results}))

     Reihenfolge der Implementation

     1. milestone_config.py - Content-Type Definitionen (30 min)
     2. stage1_summarizer.py - Transcript Aufbereitung + Supabase Cache (1h)
     3. stage2_planner.py - Lernpfad Planung (1h)
     4. stage3_generator.py - H5P Content Generation (45 min)
     5. builders/ - Refactor aus learning_path_generator.py (1h)
     6. test_learning_path_mix.py - Validierung Tests (30 min)
     7. run_pipeline.py - CLI Integration (30 min)
     8. E2E Test - Vollständiger Durchlauf mit echtem Transcript (30 min)

● Plan genehmigt! Ich starte mit der Implementation:

● Bash(mkdir -p "C:/Users/Daniel/PycharmProjects/REICHWEITE UND SCHULUNGSCONTENT/YT_to_Interactive E-Learning  (Video → Transcript → LLM → H5P Package → Moodle)/src/h5…)
  ⎿  (No content)

● Write(src\h5p\config\__init__.py)
  ⎿  Wrote 1 lines to src\h5p\config\__init__.py
     """H5P Pipeline Configuration Module"""
     from .milestones import MILESTONE_CONFIGS, get_milestone_config
     from .content_types import CONTENT_TYPE_SCHEMAS, get_content_type_schema
     __all__ = [
         "MILESTONE_CONFIGS",
         "get_milestone_config",
         "CONTENT_TYPE_SCHEMAS",
         "get_content_type_schema",

● Write(src\h5p\config\milestones.py)
  ⎿  Wrote 1 lines to src\h5p\config\milestones.py
     """
     Milestone-spezifische Konfigurationen für die H5P-Pipeline.
     Jeder Milestone hat unterschiedliche Content-Types verfügbar:
     - MVP 1.0: 7 Basis-Types (Text-basiert)
     - Post-MVP 1.1: + UX Verbesserungen (Auto-Weiter)
     - Post-MVP 1.2: + Media Types (Video, Audio, Bilder)
     - Post-MVP 1.3: + Multimodal (Spracheingabe)
     """

● Write(src\h5p\config\content_types.py)
  ⎿  Wrote 1 lines to src\h5p\config\content_types.py
     """
     Content-Type Schemas und H5P-spezifische Konfigurationen.
     Definiert für jeden Content-Type:
     - LLM Output Schema (was der Generator produzieren soll)
     - H5P Library Dependencies
     - Validierungsregeln
     """
     from typing import TypedDict, Any

● Write(src\h5p\pipeline\__init__.py)
  ⎿  Wrote 1 lines to src\h5p\pipeline\__init__.py
     """
     3-Stufen H5P Generation Pipeline
     Stufe 1: Transcript → Strukturiertes Skript (stage1_summarizer)
     Stufe 2: Skript → Lernpfad-Plan (stage2_planner)
     Stufe 3: Plan → H5P Content (stage3_generator)
     """
     from .stage1_summarizer import summarize_transcript
     from .stage2_planner import plan_learning_path

● Write(src\h5p\pipeline\stage1_summarizer.py)
  ⎿  Wrote 1 lines to src\h5p\pipeline\stage1_summarizer.py
     """
     Stage 1: Transcript Summarizer
     Wandelt rohe YouTube-Untertitel in ein strukturiertes Lern-Skript um.
     - Entfernt Füllwörter und Wiederholungen
     - Identifiziert Kernkonzepte mit Tags
     - Strukturiert in logische Abschnitte
     - Cached Ergebnisse in Supabase
     """

● Write(src\h5p\pipeline\stage2_planner.py)
  ⎿  Wrote 1 lines to src\h5p\pipeline\stage2_planner.py
     """
     Stage 2: Learning Path Planner
     Plant die didaktische Reihenfolge und wählt Content-Types basierend auf:
     - Strukturiertem Skript aus Stage 1
     - Verfügbaren Content-Types für den Milestone
     - Didaktischen Regeln (Passiv → Aktiv → Reflexion)
     """
     import json

● Write(src\h5p\pipeline\stage3_generator.py)
  ⎿  Wrote 1 lines to src\h5p\pipeline\stage3_generator.py
     """
     Stage 3: H5P Content Generator
     Generiert den konkreten H5P-Content für jede geplante Aktivität.
     - Nutzt den Brief aus Stage 2
     - Generiert type-spezifischen Content
     - Validiert gegen H5P-Schema
     """
     import json
  ⎿  5-hour limit reached · resets 3pm (Europe/Berlin) · /upgrade to Max 20x or turn on /extra-usage
     /upgrade to increase your usage limit.