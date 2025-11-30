# YouTube to E-Learning Pipeline - Checkpoint 2025-11-30

## Stand

**Aktuelles Ziel:** Upgrade auf modulare 3-Stufen-Pipeline mit Milestone-spezifischen Prompts.

Die Kernkomponenten der neuen Pipeline sind implementiert (Stage 1-3). Es fehlen noch:
- builders/ Verzeichnis (Refactor)
- run_pipeline.py (CLI)
- Tests und Supabase Schema

## Neue 3-Stufen-Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│ STUFE 1: TRANSCRIPT AUFBEREITUNG (stage1_summarizer.py)         │
│ Input:  Rohe YouTube-Untertitel                                │
│ Output: Strukturiertes Lern-Skript mit Tags                     │
│         [DEFINITION], [PROZESS], [VERGLEICH], [FAKT], [BEISPIEL]│
│ Cache:  Supabase structured_scripts Tabelle                     │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ STUFE 2: DIDAKTISCHE PLANUNG (stage2_planner.py)                │
│ Input:  Strukturiertes Skript + Milestone-Config                │
│ Output: Lernpfad-Plan mit Content-Type Empfehlungen             │
│ Regeln: 25% passiv → 50% aktiv → 15% reflektiv                  │
│         Summary muss am Ende, keine gleichen Types nacheinander │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ STUFE 3: H5P CONTENT GENERIERUNG (stage3_generator.py)          │
│ Input:  Lernpfad-Plan + Strukturiertes Skript                   │
│ Output: H5P-fähige JSON-Strukturen pro Content-Type             │
│ Builds: builders/*.py → H5P ZIP → Moodle Import                 │
└─────────────────────────────────────────────────────────────────┘
```

## Pipeline-Komponenten Status

| Komponente | Status | Datei |
|------------|--------|-------|
| Milestone Configs | ✅ | `config/milestones.py` |
| Content-Type Schemas | ✅ | `config/content_types.py` |
| Stage 1: Summarizer | ✅ | `pipeline/stage1_summarizer.py` |
| Stage 2: Planner | ✅ | `pipeline/stage2_planner.py` |
| Stage 3: Generator | ✅ | `pipeline/stage3_generator.py` |
| builders/ Refactor | ⏳ | `builders/__init__.py` etc. |
| CLI Entry Point | ⏳ | `run_pipeline.py` |
| Validierungs-Tests | ⏳ | `tests/test_learning_path_mix.py` |
| Supabase Schema | ⏳ | SQL Migration |

## Milestone-Konfigurationen

| Milestone | Content-Types | Besonderheit |
|-----------|---------------|--------------|
| MVP 1.0 | 7 (dialogcards, accordion, truefalse, blanks, dragtext, multichoice, summary) | Basis-Pipeline |
| 1.1 UX | 7 + auto_advance | Weniger Klicks |
| 1.2 Media | +3 (imagehotspots, interactivevideo, audiosummary) | ElevenLabs Audio |
| 1.3 Multimodal | +1 (speechinput_quiz) | Web Speech API |

## Projektstruktur (Aktuell + Geplant)

```
src/h5p/
├── config/                      # ✅ NEU: Milestone-Configs
│   ├── __init__.py
│   ├── milestones.py            # MVP, 1.1, 1.2, 1.3 Konfigurationen
│   └── content_types.py         # Schemas für 9 Content-Types
├── pipeline/                    # ✅ NEU: 3-Stufen-Pipeline
│   ├── __init__.py
│   ├── stage1_summarizer.py     # Transcript → Strukturiertes Skript
│   ├── stage2_planner.py        # Skript → Lernpfad-Plan
│   └── stage3_generator.py      # Plan → H5P Content
├── builders/                    # ⏳ TODO: Refactor aus learning_path_generator
│   ├── __init__.py
│   ├── base.py
│   ├── truefalse.py
│   ├── blanks.py
│   └── ... (alle 9 Types)
├── run_pipeline.py              # ⏳ TODO: CLI Entry Point
├── learning_path_generator.py   # LEGACY: Monolithischer Generator
├── package_builder.py
├── content_types.py
├── course_schema.py
├── generator.py
├── cli_youtube_to_h5p.py
├── cli_youtube_to_h5p_v2.py
├── multi_quiz_generator.py
├── find_youtube.py
└── __init__.py
```

## CLI Nutzung

```bash
# Auf VPS:
cd /home/claude/python-modules/src/services/h5p
python3 learning_path_generator.py \
  --youtube-url-id 2454 \
  --courseid 2

# Mit Transcript-Datei:
python3 learning_path_generator.py \
  --transcript-file transcript.txt \
  --title "Mein Kurs" \
  --courseid 2
```

## Technische Details

- **Moodle:** http://148.230.71.150:8080
- **Supabase:** http://148.230.71.150:8000
- **VPS:** 148.230.71.150 (SSH als root oder claude)
- **LLM:** OpenAI gpt-4o-mini mit JSON response_format

---

## Implementierte Features (2025-11-29)

### 9 H5P Content-Types - VOLLSTÄNDIG

| # | Typ | Status | Didaktische Phase |
|---|-----|--------|-------------------|
| 1 | Dialogcards | ✅ | Passiv - Einführung |
| 2 | Accordion | ✅ | Passiv - Vertiefung |
| 3 | MultiChoice | ✅ | Aktiv - Prüfung |
| 4 | TrueFalse | ✅ | Aktiv - Schnellcheck |
| 5 | Blanks | ✅ | Aktiv - Anwendung |
| 6 | DragAndDrop | ✅ | Aktiv - Verknüpfung |
| 7 | Summary | ✅ | Abschluss |
| 8 | InteractiveVideo | ✅ | Video mit Stopp-Fragen |
| 9 | ImageHotspots | ✅ | Visuelles Erkunden |

### Neue Features:

1. **InteractiveVideo Builder** (`build_interactive_video_h5p()`)
   - YouTube Video via URL einbinden
   - Interaktionen mit Timestamps (Sekunden)
   - Unterstützte Interaktionstypen: MultiChoice, TrueFalse, Text
   - Video pausiert automatisch bei Quiz-Fragen

2. **ImageHotspots Builder** (`build_image_hotspots_h5p()`)
   - YouTube Thumbnail automatisch generiert
   - Hotspots mit x/y Koordinaten (%)
   - Popup-Content als Text/HTML

3. **Helper-Funktionen**
   - `extract_video_id(url)` - Extrahiert YouTube Video-ID
   - `extract_timestamps_from_subtitles(subtitles)` - Parst Timestamps aus Untertiteln
   - `get_youtube_thumbnail(video_id)` - Generiert Thumbnail-URL

4. **LLM Prompt erweitert**
   - Alle 9 Content-Types im Beispiel
   - URL-Platzhalter werden automatisch ersetzt
   - Kontextuelle Hinweise für InteractiveVideo und ImageHotspots

---

## Nächste Schritte (Priorisiert)

### 1. Pipeline fertigstellen - ABGESCHLOSSEN! (2025-11-30)

| Task | Status | Beschreibung |
|------|--------|--------------|
| builders/ Refactor | ✅ | 9 Builder-Module in `builders/` |
| run_pipeline.py | ✅ | CLI Entry Point mit --milestone Support |
| test_learning_path_mix.py | ✅ | Validierungs-Tests für "richtige Mischung" |
| Supabase Schema | ✅ | `structured_scripts` Tabelle erstellt |
| E2E Test | ✅ | 8/8 Aktivitäten erfolgreich importiert |

### E2E Test Ergebnis (2025-11-30)

```
Pipeline: 3-stage
Milestone: mvp
YouTube URL ID: 3420
Total Activities: 8
Successful Imports: 8/8

Mix Distribution:
- Passive: 25.0% (2 activities)
- Active: 62.5% (5 activities)
- Reflect: 12.5% (1 activity)

Validation: ALL PASSED
```

**Test-Kurs:** Pipeline Test (ID: 23)
**Activities:** cmid 136-143

### 2. Standard-Test-Video (PERSISTIERT)

| Feld | Wert |
|------|------|
| **Supabase ID** | 3420 |
| **Thema** | Corporate LLMs |
| **Zweck** | E-Learning Modul für neue Mitarbeiter |

**Dieses Video für ALLE Tests verwenden!**

### 3. Bekannte Issues

**H5P Rendering-Problem (2025-11-29):**
- Einige H5P Content-Types (TrueFalse, Blanks, Summary, DragAndDrop) rendern nur den Intro-Text
- Dialogcards und MultiChoice funktionieren korrekt
- Mögliche Ursache: H5P iframe-Rendering oder JavaScript-Konflikt

**Test-User:** student1 / Student2025! (eingeschrieben in Kurs 2)

### 4. UX-Verbesserungen (Milestone 1.1) - ABGESCHLOSSEN! (2025-11-30)

**Auto-Check Feature:** Weniger Klicks für User

| Content-Type | Parameter | Effekt |
|--------------|-----------|--------|
| MultiChoice | `autoCheck: true` | Sofortige Prüfung nach Auswahl |
| TrueFalse | `autoCheck: true` | Sofortige Prüfung |
| Blanks | `autoCheck: true` | Auto-Check nach Eingabe |

**Aktivierung:** `--milestone 1.1` (oder höher)

**Test-Aktivitäten:**
- cmid 144: UX Test: Auto-Check MultiChoice
- cmid 145: UX Test: Auto-Check TrueFalse

**Quellen:**
- [H5P MultiChoice semantics.json](https://github.com/h5p/h5p-multi-choice)
- [H5P TrueFalse semantics.json](https://github.com/h5p/h5p-true-false)

### 5. NotebookLM Integration (2025-11-30) - IN PROGRESS

**Gesamtplan:** `src/doc/NOTEBOOKLM_PLAN.md`

| Komponente | Status | Tests |
|------------|--------|-------|
| Mindmap Node-Extraktion | ✅ Gefixt | 8/8 |
| MindmapAnimator | ✅ Neu | 14/14 |
| AudioTranscriber (Whisper) | ✅ Neu | - |
| CLI (--animate, --sync-audio) | ✅ Erweitert | - |

**Was jetzt funktioniert:**
- Mindmap SVG + JSON Extraktion mit korrekter Node-Hierarchie
- Timeline-Generierung (sequentiell oder Audio-synced)
- Keyword-Matching für Audio-zu-Node Zuordnung
- CLI mit allen neuen Flags

**CLI-Beispiele:**
```bash
# Mindmap mit Animation
python -m src.adapters.notebooklm.cli --youtube-url-id 3420 --mindmap --animate

# Mit Audio-Sync
python -m src.adapters.notebooklm.cli --youtube-url-id 3420 --mindmap --animate --audio --sync-audio
```

**Noch ausstehend:**
- E2E-Browser-Tests (benötigen manuelles Chrome mit NotebookLM-Login)
- Video Recording (Playwright/FFmpeg Integration)
- Content-Selektoren für Nov 2025 UI

### 5. Backlog

- **VPS Deployment** - Neue Version deployen
- **H5P Libraries prüfen** - InteractiveVideo 1.26 und ImageHotspots 1.10
