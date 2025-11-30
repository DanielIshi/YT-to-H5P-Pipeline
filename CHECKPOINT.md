# YouTube to E-Learning Pipeline - Checkpoint 2025-11-29

## Stand

Projekt wurde in eigenes Repository verschoben. Die Pipeline generiert **7 H5P-Aktivitätstypen**. Zwei weitere Content-Types (InteractiveVideo, ImageHotspots) stehen zur Implementierung an.

## Abgeschlossene Aufgaben

1. ✅ **7 H5P Builder-Funktionen implementiert**
   - Dialogcards (Karteikarten)
   - Accordion (aufklappbare Erklärungen)
   - MultiChoice (Quiz)
   - TrueFalse (Wahr/Falsch)
   - Blanks (Lückentext)
   - DragAndDrop (DragText-basiert)
   - Summary (Zusammenfassung)

2. ✅ **LLM Prompt (LEARNING_PATH_PROMPT)**
   - Generiert didaktisch strukturierten Lernpfad
   - 8-12 Aktivitäten in logischer Reihenfolge
   - Beginnt passiv (Dialogcards, Accordion) → aktiv (Quiz, Blanks) → Summary

3. ✅ **CLI mit youtube-url-id Support**
   - Holt Transcript direkt aus Supabase
   - Generiert alle Aktivitäten in einem Durchlauf
   - Importiert automatisch in Moodle

4. ✅ **Projekt-Verschiebung abgeschlossen**
   - Eigenes Projekt: `YT_to_Interactive E-Learning`
   - Dateien in `src/h5p/` strukturiert

## Projektstruktur

```
src/h5p/
├── learning_path_generator.py   # Hauptgenerator (7 Content-Types)
├── package_builder.py           # H5P ZIP Builder
├── content_types.py             # Pydantic Models
├── course_schema.py             # Schema Definitionen
├── generator.py                 # Basis-Generator
├── cli_youtube_to_h5p.py        # CLI v1
├── cli_youtube_to_h5p_v2.py     # CLI v2
├── multi_quiz_generator.py      # Legacy: Nur MultiChoice
├── find_youtube.py              # YouTube Helper
├── import_h5p.php               # Moodle Import Script
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

## Nächste Schritte

### Standard-Test-Video (PERSISTIERT)

| Feld | Wert |
|------|------|
| **Supabase ID** | 3420 |
| **Thema** | Corporate LLMs |
| **Zweck** | E-Learning Modul für neue Mitarbeiter |

**Dieses Video für ALLE Tests verwenden!**

### Robustness-Test Status

**Lokaler Test:** ✅ Alle 9 Content-Types bestanden (2025-11-29)

**E2E-Test:** 9/9 PASS (technisch) - Visuelle Validierung zeigt Rendering-Issues (2025-11-29)

| # | Content-Type | CMID | Erreichbar | Content sichtbar |
|---|--------------|------|------------|------------------|
| 1 | ImageHotspots | 92 | ✅ | ⚠️ Prüfung ausstehend |
| 2 | Dialogcards | 93 | ✅ | ✅ Karteikarten mit Turn-Button |
| 3 | Accordion | 94 | ✅ | ⚠️ Prüfung ausstehend |
| 4 | InteractiveVideo | 95 | ✅ | ⚠️ Prüfung ausstehend |
| 5 | MultiChoice | 96 | ✅ | ✅ Quiz mit Antwortoptionen |
| 6 | Blanks | 97 | ✅ | ⚠️ Nur Intro-Text sichtbar |
| 7 | TrueFalse | 98 | ✅ | ⚠️ Nur Intro-Text sichtbar |
| 8 | DragAndDrop | 99 | ✅ | ⚠️ Nur Intro-Text sichtbar |
| 9 | Summary | 100 | ✅ | ⚠️ Nur Intro-Text sichtbar |

**Fixes durchgeführt (2025-11-29):**
1. ✅ **import_h5p.php** - H5P-Deployment via `helper::save_h5p()` statt nur Datei-Upload
2. ✅ **H5P CSS Mixed-Content** - Hardcodierte HTTP-URLs auf relative Pfade geändert
3. ✅ **H5P Hub aktiviert** - 268+ Libraries von h5p.org heruntergeladen
4. ✅ **Moodle-Caches** - Regelmäßig gepurged

**Bekanntes Problem:**
- Einige H5P Content-Types (TrueFalse, Blanks, Summary, DragAndDrop) rendern nur den Intro-Text
- Dialogcards und MultiChoice funktionieren korrekt
- H5P-Daten sind in DB korrekt gespeichert (jsoncontent vorhanden)
- Mögliche Ursache: H5P iframe-Rendering oder JavaScript-Konflikt

**Test-User:** student1 / Student2025! (eingeschrieben in Kurs 2)

**Aktueller Kurs:**
- **Titel:** NoneKurs_1764274401
- **URL:** https://moodle.srv947487.hstgr.cloud/course/view.php?id=2
- **Activities:** 92-100 (neu generiert mit fixiertem Import-Script)

**Screenshots:** `tests/e2e/screenshots/`

### Geplant: Selenium-Adapter für externe Plattformen

**Feature:** Integration eines Selenium-Adapters zur automatischen Extraktion von Lerninhalten von externen Plattformen.

**Ziel:** Inhalte von kostenlosen Lernplattformen abziehen und in H5P/Moodle integrieren:
- Lernvideos
- Mindmaps
- Zusammenfassungslisten
- Andere interaktive Inhalte

**Architektur-Vorschlag:**
```
src/adapters/
├── __init__.py
├── base_adapter.py       # Abstract Base Class
├── selenium_service.py   # WebDriver Management
└── platforms/
    └── example_platform.py
```

**Akzeptanzkriterien:**
- [ ] Mindestens eine Plattform als Proof-of-Concept
- [ ] Extrahierte Inhalte in H5P-Pipeline nutzbar
- [ ] Robuste Fehlerbehandlung
- [ ] Dokumentation

### Weitere optionale Schritte

1. ⏳ **VPS Deployment** - Neue Version deployen
2. ⏳ **H5P Libraries prüfen** - InteractiveVideo 1.26 und ImageHotspots 1.10 in Moodle
