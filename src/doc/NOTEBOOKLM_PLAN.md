# NotebookLM Integration - Gesamtplan

> **Ziel:** Multimodale E-Learning-Inhalte aus NotebookLM extrahieren und in Moodle-kompatible Formate transformieren.

---

## 1. Status Quo - Analyse der existierenden Module

### 1.1 Implementierte Module

| Modul | Status | Beschreibung | Robustheit |
|-------|--------|--------------|------------|
| `client.py` | ✅ Implementiert | Browser-Automation Core (CDP + Playwright) | ⚠️ Mittel - Auth-Flow funktioniert |
| `config.py` | ✅ Implementiert | Konfiguration + Selektoren (DE/EN) | ⚠️ Mittel - UI-Änderungen erfordern Updates |
| `notebook_manager.py` | ✅ Implementiert | Notebook erstellen, Quellen hinzufügen | ⚠️ Mittel - Text-Source funktioniert |
| `content_extractor.py` | ⚠️ Teilweise | FAQ, Study Guide, Briefing, Timeline | ❌ Schwach - Selektoren veraltet |
| `audio_downloader.py` | ⚠️ Teilweise | Audio Overview (Podcast) Download | ❌ Nicht getestet |
| `video_downloader.py` | ⚠️ Teilweise | Video Overview Download | ❌ Nicht getestet |
| `mindmap_extractor.py` | ⚠️ Teilweise | Mindmap SVG + JSON Extraktion | ❌ **KRITISCH**: Nodes werden nicht extrahiert! |
| `cli.py` | ✅ Implementiert | CLI mit allen Flags | ⚠️ Mittel - Abhängig von anderen Modulen |

### 1.2 Kritische Probleme (Stand 2025-11-30)

#### Problem 1: Mindmap Node-Extraktion scheitert
```json
// Aktueller Output (tests/output/notebooklm/mindmap/*.json):
{
  "nodes": [],           // ❌ LEER!
  "connections": [],     // ❌ LEER!
  "hierarchy": null      // ❌ NULL!
}
```

**Ursache:** Die Regex-Patterns in `_extract_nodes_from_svg()` matchen nicht auf NotebookLMs aktuelles SVG-Format.

```python
# Alter Pattern (funktioniert nicht):
node_pattern = r'<text class="node-name"[^>]*>([^<]+)</text>'
```

**Lösung:** SVG analysieren und Patterns aktualisieren.

#### Problem 2: Content-Selektoren veraltet
NotebookLM UI wurde im November 2025 umgebaut:
- Studio Panel hat jetzt "Cards" statt Tabs
- FAQ, Study Guide etc. sind jetzt anders erreichbar
- Einige Selektoren in `config.py` sind obsolet

#### Problem 3: Audio/Video Generierung ungetestet
- Timeout-Handling unklar
- Download-Mechanismus nicht verifiziert
- Generierungszeit 5-10 Minuten für Video

### 1.3 Was funktioniert

✅ **Browser-Verbindung via CDP** (Chrome mit Pre-Auth)
✅ **Notebook erstellen**
✅ **Text-Quelle hinzufügen** ("Kopierter Text")
✅ **SVG der Mindmap extrahieren** (aber ohne Nodes)
✅ **CLI Grundstruktur**

---

## 2. Geplante Features

### 2.1 Core Features (Phase 1 - Bugfixes)

| Feature | Priorität | Beschreibung |
|---------|-----------|--------------|
| **Fix: Mindmap Node-Extraktion** | 🔴 KRITISCH | SVG parsen, Nodes + Hierarchie extrahieren |
| **Fix: Content-Selektoren** | 🔴 KRITISCH | Selektoren an Nov 2025 UI anpassen |
| **Test: Audio Download** | 🟡 HOCH | E2E-Test für Podcast-Generierung |
| **Test: Video Download** | 🟡 HOCH | E2E-Test für Video-Generierung |

### 2.2 Neue Features (Phase 2 - Erweiterungen)

| Feature | Priorität | Beschreibung |
|---------|-----------|--------------|
| **Mindmap Animation** | 🟡 HOCH | Nodes durchklicken, aufklappen basierend auf Audio-Timing |
| **Audio-Transcript Sync** | 🟡 HOCH | Audio → Timestamps → Mindmap-Nodes synchronisieren |
| **Video Recording** | 🟡 HOCH | Mindmap-Animation als Video aufnehmen |
| **Moodle Integration** | 🟢 MITTEL | H5P-Pakete aus NotebookLM-Content erstellen |

### 2.3 Erweiterte Features (Phase 3 - Advanced)

| Feature | Priorität | Beschreibung |
|---------|-----------|--------------|
| **Multi-Source Notebooks** | 🟢 MITTEL | Mehrere YouTube-Videos/Dokumente kombinieren |
| **Batch Processing** | 🟢 MITTEL | Mehrere Notebooks parallel verarbeiten |
| **Auto-Quiz Generation** | 🔵 NIEDRIG | Quiz aus FAQ/Study Guide generieren |
| **Interactive Mindmap Player** | 🔵 NIEDRIG | Web-Player für animierte Mindmaps |

---

## 3. Architektur

### 3.1 Aktuelle Architektur

```
src/adapters/notebooklm/
├── client.py              # Browser-Core (Playwright + CDP)
├── config.py              # Selektoren + Config
├── notebook_manager.py    # Notebook CRUD + Sources
├── content_extractor.py   # FAQ, Study Guide, etc.
├── audio_downloader.py    # Podcast Download
├── video_downloader.py    # Video Download
├── mindmap_extractor.py   # SVG + JSON Extraktion
├── cli.py                 # CLI Entry Point
└── __init__.py
```

### 3.2 Geplante Erweiterungen

```
src/adapters/notebooklm/
├── ... (bestehende Module)
├── mindmap_animator.py    # 🆕 Mindmap Navigation + Animation
├── audio_sync.py          # 🆕 Audio-Timestamp-Synchronisation
├── video_recorder.py      # 🆕 Screen Recording der Animation
├── h5p_transformer.py     # 🆕 NotebookLM → H5P Konvertierung
└── orchestrator.py        # 🆕 Workflow-Koordination
```

---

## 4. Feature-Spezifikationen

### 4.1 Mindmap Node-Extraktion (Fix)

**Ziel:** Nodes aus NotebookLM Mindmap SVG korrekt extrahieren.

**Schritte:**
1. SVG-Struktur von NotebookLM analysieren (2025-11 Version)
2. Regex-Patterns für `<text>`, `<g>`, `<path>` aktualisieren
3. Node-Hierarchie aus `transform` Attributen ableiten
4. Connections aus Path-Elementen extrahieren
5. JSON-Output mit vollständiger Struktur

**Erwarteter Output:**
```json
{
  "nodes": [
    {"id": "node_0", "text": "Corporate LLMs", "level": 0, "x": 0, "y": 300},
    {"id": "node_1", "text": "Private KI-Modelle", "level": 1, "x": 460, "y": 150},
    ...
  ],
  "connections": [
    {"source": "node_0", "target": "node_1"},
    ...
  ],
  "hierarchy": {
    "id": "node_0",
    "text": "Corporate LLMs",
    "children": [...]
  }
}
```

### 4.2 Mindmap Animation (Neu)

**Ziel:** Mindmap interaktiv explorieren und aufnehmen.

**Konzept:**
```
┌────────────────────────────────────────────────────────────────┐
│  MINDMAP ANIMATION ENGINE                                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Input:                                                        │
│  ├─ mindmap.json (Nodes + Hierarchie)                         │
│  ├─ audio.mp3 (NotebookLM Podcast)                            │
│  └─ transcript.txt (mit Timestamps, optional)                  │
│                                                                │
│  Process:                                                       │
│  1. Audio analysieren → Keywords pro Zeitabschnitt             │
│  2. Keywords → Mindmap-Nodes matchen                           │
│  3. Animation-Timeline generieren                              │
│  4. Browser-Automation: Nodes klicken/expandieren              │
│  5. Screen Recording der Animation                             │
│                                                                │
│  Output:                                                        │
│  └─ animated_mindmap.mp4                                       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Animation-Ablauf:**
1. Starte mit Root-Node (alle anderen collapsed)
2. Wenn Audio Thema X erwähnt → Node X expandieren
3. Kurze Pause (2-3 Sek) für Leser
4. Wenn neues Thema → vorheriges Node collapsieren, neues expandieren
5. Am Ende: Alle Nodes expanded, Gesamtübersicht

**Technischer Ansatz:**
```python
class MindmapAnimator:
    """Animiert Mindmap basierend auf Audio-Timeline"""

    async def animate(
        self,
        mindmap_data: MindmapData,
        audio_timeline: List[AudioSegment],
        recording: bool = True
    ) -> Optional[Path]:
        """
        1. Mindmap im Browser öffnen
        2. Collapse all außer Root
        3. Für jeden Audio-Segment:
           - Node finden der zum Content passt
           - Node expandieren (click)
           - Warten (segment.duration)
           - Optional: Highlight-Animation
        4. Recording stoppen
        5. Video zurückgeben
        """
```

### 4.3 Audio-Transcript Synchronisation (Neu)

**Ziel:** Audio-Timestamps mit Mindmap-Nodes synchronisieren.

**Ansatz 1: Transcript-basiert (falls verfügbar)**
```python
# NotebookLM Podcast hat manchmal Transcript
# Parse: "At 0:45 we discuss Private KI-Modelle..."
async def parse_audio_timestamps(transcript: str) -> List[AudioSegment]:
    pass
```

**Ansatz 2: Speech-to-Text (Whisper)**
```python
# Whisper liefert word-level timestamps
async def transcribe_with_timestamps(audio_path: Path) -> List[AudioSegment]:
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(str(audio_path), word_timestamps=True)
    return result["segments"]
```

**Ansatz 3: Keyword-Matching**
```python
# Mindmap-Nodes als Keywords, dann im Transcript suchen
async def match_keywords_to_audio(
    mindmap_nodes: List[MindmapNode],
    transcript_segments: List[AudioSegment]
) -> Dict[str, float]:  # node_id -> timestamp
    pass
```

### 4.4 Video Recording (Neu)

**Ziel:** Mindmap-Animation als Video aufnehmen.

**Technologie-Optionen:**

| Option | Pros | Cons |
|--------|------|------|
| **Playwright Recording** | Integriert, einfach | Nur Viewport, keine System-Audio |
| **FFmpeg Screen Capture** | System-Audio möglich | Separates Tool, Setup |
| **OBS CLI** | Professionell | Schwer zu automatisieren |

**Empfehlung:** Playwright Recording + FFmpeg Audio-Merge

```python
class VideoRecorder:
    async def record_animation(
        self,
        page: Page,
        duration_seconds: int,
        output_path: Path
    ) -> Path:
        # Playwright kann Videos aufnehmen
        context = await browser.new_context(
            record_video_dir=str(output_path.parent),
            record_video_size={"width": 1920, "height": 1080}
        )
        # ... Animation abspielen ...
        await context.close()  # Video wird gespeichert

    async def merge_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path
    ) -> Path:
        # FFmpeg: Video + Audio zusammenfügen
        cmd = f"ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac {output_path}"
```

### 4.5 Moodle/H5P Integration (Später)

**Ziel:** NotebookLM-Content als H5P-Aktivitäten in Moodle.

| NotebookLM Content | H5P Content-Type |
|-------------------|------------------|
| FAQ | Accordion |
| Study Guide | Interactive Book |
| Mindmap Animation | Interactive Video |
| Audio Podcast | Audio + Summary |
| Quiz | MultiChoice |

---

## 5. Implementation Roadmap

### Phase 1: Bugfixes & Stabilisierung (1-2 Tage)

| Task | Issue | Status |
|------|-------|--------|
| 1.1 SVG-Struktur analysieren | - | ⏳ |
| 1.2 Mindmap Node-Extraktion fixen | Fix: Regex Patterns | ⏳ |
| 1.3 Content-Selektoren aktualisieren | Nov 2025 UI | ⏳ |
| 1.4 Audio Download E2E-Test | Verifizieren | ⏳ |
| 1.5 Video Download E2E-Test | Verifizieren | ⏳ |
| 1.6 Test-Suite erweitern | Mocked + Integration | ⏳ |

### Phase 2: Mindmap Animation (3-5 Tage)

| Task | Status |
|------|--------|
| 2.1 `MindmapAnimator` Klasse erstellen | ⏳ |
| 2.2 Node-Click Automation implementieren | ⏳ |
| 2.3 Animation-Timeline Generator | ⏳ |
| 2.4 Playwright Video Recording | ⏳ |
| 2.5 FFmpeg Audio-Merge | ⏳ |

### Phase 3: Audio-Sync (2-3 Tage)

| Task | Status |
|------|--------|
| 3.1 Whisper Integration | ⏳ |
| 3.2 Keyword-Matching Algorithm | ⏳ |
| 3.3 Timeline-Generation aus Audio | ⏳ |
| 3.4 End-to-End Test: Audio → Animation → Video | ⏳ |

### Phase 4: Moodle Integration (3-5 Tage)

| Task | Status |
|------|--------|
| 4.1 NotebookLM → H5P Transformer | ⏳ |
| 4.2 Animated Mindmap als Interactive Video | ⏳ |
| 4.3 FAQ → Accordion Converter | ⏳ |
| 4.4 Study Guide → Course Presentation | ⏳ |
| 4.5 Pipeline: YouTube → NotebookLM → Moodle | ⏳ |

---

## 6. CLI Erweiterungen

### Aktuelle CLI

```bash
python -m src.adapters.notebooklm.cli \
  --youtube-url-id 3420 \
  --all \
  --output ./output
```

### Geplante CLI Erweiterungen

```bash
# Mindmap Animation generieren
python -m src.adapters.notebooklm.cli \
  --youtube-url-id 3420 \
  --mindmap \
  --animate \
  --record-video \
  --output ./output

# Mit Audio-Sync
python -m src.adapters.notebooklm.cli \
  --youtube-url-id 3420 \
  --mindmap \
  --animate \
  --sync-audio \
  --output ./output

# Direkt nach Moodle
python -m src.adapters.notebooklm.cli \
  --youtube-url-id 3420 \
  --all \
  --export-h5p \
  --moodle-course 2 \
  --output ./output
```

### Neue CLI Flags

| Flag | Beschreibung |
|------|--------------|
| `--animate` | Mindmap-Animation durchführen |
| `--sync-audio` | Audio-Timestamps mit Mindmap synchronisieren |
| `--record-video` | Animation als Video aufnehmen |
| `--export-h5p` | H5P-Pakete generieren |
| `--moodle-course ID` | Direkt in Moodle-Kurs importieren |
| `--animation-speed FACTOR` | Geschwindigkeit (0.5 = langsam, 2.0 = schnell) |
| `--node-pause SECONDS` | Pause pro Node (default: 3) |

---

## 7. Test-Strategie

### 7.1 Test-Material

| ID | Titel | Zweck |
|----|-------|-------|
| Supabase 3420 | Corporate LLMs - Private KI | Standard E2E Test |

### 7.2 Test-Typen

```
tests/
├── test_notebooklm_adapter.py     # ✅ Existiert (Mocked)
├── test_mindmap_extraction.py     # 🆕 SVG Parsing Tests
├── test_mindmap_animation.py      # 🆕 Animation Logic Tests
├── test_audio_sync.py             # 🆕 Timestamp Matching Tests
├── test_video_recording.py        # 🆕 Recording Tests
└── test_e2e_notebooklm.py         # 🆕 Full Pipeline Tests
```

### 7.3 E2E Test Workflow

```bash
# 1. Notebook erstellen + Content
# 2. Mindmap extrahieren (SVG + JSON mit Nodes)
# 3. Audio generieren + downloaden
# 4. Audio transkribieren (Whisper)
# 5. Timestamps matchen
# 6. Animation ausführen + aufnehmen
# 7. Video + Audio mergen
# 8. Ergebnis verifizieren
```

---

## 8. Risiken & Mitigations

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| NotebookLM UI ändert sich | 🔴 Hoch | 🔴 Hoch | Selektoren abstrahieren, regelmäßig testen |
| Audio-Generation dauert zu lange | 🟡 Mittel | 🟡 Mittel | Timeout erhöhen, Retry-Logic |
| Whisper nicht verfügbar | 🟢 Niedrig | 🟡 Mittel | Fallback auf Keyword-Matching |
| Video-Recording Performance | 🟡 Mittel | 🟢 Niedrig | Hardware-Beschleunigung, niedrigere Auflösung |
| Google Rate-Limiting | 🟡 Mittel | 🔴 Hoch | Delays einbauen, human-like Verhalten |

---

## 9. Abhängigkeiten

### Python Packages

```
playwright>=1.40
httpx>=0.25
pydantic>=2.0
python-dotenv>=1.0
whisper (openai-whisper)>=1.0  # Für Audio-Sync
ffmpeg-python>=0.2             # Für Video-Merge
```

### System

- Chrome Browser (mit Pre-Auth Session)
- FFmpeg (für Video/Audio Processing)
- CUDA (optional, für Whisper GPU)

---

## 10. Referenzen

- [notebookllm-mindmap-exporter](https://github.com/rootsongjc/notebookllm-mindmap-exporter) - Inspiration für SVG-Extraktion
- [Playwright Recording](https://playwright.dev/python/docs/videos) - Video Recording Docs
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech-to-Text

---

## Changelog

| Datum | Änderung |
|-------|----------|
| 2025-11-30 | Initial: Gesamtplan erstellt |
| 2025-11-30 | Status-Analyse der existierenden Module |
| 2025-11-30 | Feature-Spezifikationen für Animation + Sync |
| 2025-11-30 | Roadmap mit 4 Phasen definiert |
| 2025-11-30 | **IMPLEMENTIERT:** Mindmap Node-Extraktion gefixt (8 Tests passed) |
| 2025-11-30 | **IMPLEMENTIERT:** MindmapAnimator Klasse (14 Tests passed) |
| 2025-11-30 | **IMPLEMENTIERT:** AudioTranscriber Klasse (Whisper Integration) |
| 2025-11-30 | **IMPLEMENTIERT:** CLI erweitert (--animate, --sync-audio, --record-video) |

## Implementierungsstand

### Phase 1: Bugfixes & Stabilisierung

| Task | Status |
|------|--------|
| 1.1 SVG-Struktur analysieren | ✅ Erledigt |
| 1.2 Mindmap Node-Extraktion fixen | ✅ Erledigt (Regex für Nov 2025 SVG-Format) |
| 1.3 Content-Selektoren aktualisieren | ⏳ Ausstehend |
| 1.4 Audio Download E2E-Test | ⏳ Ausstehend |
| 1.5 Video Download E2E-Test | ⏳ Ausstehend |

### Phase 2: Mindmap Animation

| Task | Status |
|------|--------|
| 2.1 `MindmapAnimator` Klasse | ✅ Erledigt |
| 2.2 Sequentielle Timeline | ✅ Erledigt |
| 2.3 Transcript-synced Timeline | ✅ Erledigt |
| 2.4 Keyword-Matching | ✅ Erledigt |
| 2.5 Node expand/collapse | ✅ Implementiert (Browser-Teil ausstehend) |
| 2.6 Video Recording | ⏳ Stub vorhanden, FFmpeg-Integration ausstehend |

### Phase 3: Audio-Sync

| Task | Status |
|------|--------|
| 3.1 Whisper Integration | ✅ AudioTranscriber Klasse erstellt |
| 3.2 Keyword-Matching Algorithm | ✅ Erledigt |
| 3.3 CLI Integration | ✅ --sync-audio Flag |
