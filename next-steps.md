# Next Steps - YT-to-H5P Pipeline

> Stand: 2025-12-01 | Priorisiert nach Abhängigkeiten und Impact

## Übersicht

| # | Step | Issue | Aufwand | Priorität |
|---|------|-------|---------|-----------|
| 1 | Audio-Merge E2E Test | #7 | 30 min | HIGH |
| 2 | Issue #7 schließen | #7 | 5 min | HIGH |
| 3 | Video Overview Downloader | #5 | 2-3h | HIGH |
| 4 | NotebookLM Full Pipeline Test | #5 | 1h | HIGH |
| 5 | Moodle H5P Video Import | #5 | 2h | MEDIUM |
| 6 | Video mit Narration (Szenen-Script) | #6 | 3h | MEDIUM |
| 7 | ElevenLabs TTS Integration | #6 | 2h | MEDIUM |
| 8 | Flux/Gemini Infografik-Generator | #6 | 3h | MEDIUM |
| 9 | FFmpeg Video Assembly | #6 | 2h | MEDIUM |
| 10 | UX Auto-Weiter Feature | #3 | 1h | LOW |

---

## Step 1: Audio-Merge E2E Test (Issue #7)

**Ziel:** Verifizieren dass `merge_audio()` funktioniert

**Tasks:**
- [ ] Kurzen Test-Clip aufnehmen (30s statt 14min)
- [ ] `MindmapAnimator.merge_audio(video_path, audio_path)` testen
- [ ] FFmpeg Output prüfen (A/V Sync)

**Command:**
```bash
python -m src.adapters.notebooklm.mindmap_recorder \
  --notebook-url "https://notebooklm.google.com/notebook/08fc4557-e64c-4fc1-9bca-3782338426e2" \
  --audio-path "tests/output/notebooklm/jobmesse/audio/audio_20251201_120827.mp3" \
  --output "tests/output/recordings/short_test.mp4" \
  --pause 1.0
```

**Akzeptanzkriterium:** MP4 mit Audio abspielbar

---

## Step 2: Issue #7 schließen

**Voraussetzung:** Step 1 erfolgreich

**Tasks:**
- [ ] Finalen Kommentar mit Ergebnis
- [ ] Issue schließen mit `gh issue close 7`

---

## Step 3: Video Overview Downloader (Issue #5)

**Ziel:** NotebookLM Video Overview als MP4 downloaden

**Datei:** `src/adapters/notebooklm/video_downloader.py`

**Tasks:**
- [ ] Video-Tab in NotebookLM Studio öffnen
- [ ] "Generate Video" triggern (falls nicht vorhanden)
- [ ] Download-Button finden und klicken
- [ ] MP4 speichern in `tests/output/notebooklm/{notebook}/video/`

**Herausforderungen:**
- Video-Generierung dauert 5-10 Minuten
- Polling für "Ready" Status nötig
- Blob-URL für Download extrahieren

---

## Step 4: NotebookLM Full Pipeline Test

**Ziel:** Kompletter Flow: Trigger → Harvest → Export

**Workflow:**
```
1. NotebookTrigger.generate_all()
   ├── Audio Overview
   ├── Mindmap
   └── Video Overview (NEU)
2. NotebookHarvester.harvest()
   ├── FAQ, Study Guide, Briefing
   ├── Audio MP3
   ├── Mindmap SVG + JSON
   └── Video MP4 (NEU)
3. Output: tests/output/notebooklm/{notebook}/
```

**Test-Notebook:** `08fc4557-e64c-4fc1-9bca-3782338426e2` (Jobmesse)

---

## Step 5: Moodle H5P Video Import

**Ziel:** NotebookLM Video als H5P InteractiveVideo in Moodle

**Tasks:**
- [ ] H5P InteractiveVideo Package Builder
- [ ] Video-URL oder Embed in H5P
- [ ] Quiz-Timestamps aus Transcript ableiten
- [ ] Import-Test in Moodle Kurs 22

---

## Step 6: Video mit Narration - Szenen-Script (Issue #6)

**Ziel:** LLM generiert JSON-Script aus Transcript

**Datei:** `src/services/video/scene_generator.py`

**Output:**
```json
{
  "scenes": [
    {
      "duration": 10,
      "narration": "Text für TTS",
      "visual_prompt": "Infografik: 3 Säulen von KI"
    }
  ]
}
```

**LLM Prompt:** Transcript → 5-10 Szenen mit je 10-30s

---

## Step 7: ElevenLabs TTS Integration

**Ziel:** Narration-Audio für jede Szene

**Datei:** `src/services/audio/elevenlabs_tts.py`

**API:** ElevenLabs (Key vorhanden)

**Output:** `scene_01.mp3`, `scene_02.mp3`, ...

---

## Step 8: Flux/Gemini Infografik-Generator

**Ziel:** Infografiken für jede Szene

**Datei:** `src/services/image/infographic_generator.py`

**Optionen:**
- **Gemini 3 Imagen:** Für Text-in-Bild (korrekte Labels)
- **Flux 1.5-2.0:** Für künstlerische Visuals

**Output:** `scene_01.png`, `scene_02.png`, ...

---

## Step 9: FFmpeg Video Assembly

**Ziel:** Szenen zu finalem Video zusammenbauen

**Datei:** `src/services/video/assembler.py`

**Pipeline:**
```
scene_01.mp3 + scene_01.png → scene_01.mp4
scene_02.mp3 + scene_02.png → scene_02.mp4
...
concat → final_video.mp4
```

**Effekte:** Ken Burns (langsamer Zoom/Pan)

---

## Step 10: UX Auto-Weiter Feature (Issue #3)

**Ziel:** Nach korrekter Antwort automatisch zum nächsten Content

**Scope:** H5P Column Builder anpassen

**Tasks:**
- [ ] H5P behaviourSettings analysieren
- [ ] `autoAdvance` Option implementieren
- [ ] Delay konfigurierbar (1-3s)

---

## Priorisierung Begründung

1. **Steps 1-2:** Issue #7 abschließen - 90% fertig, schneller Win
2. **Steps 3-5:** NotebookLM Integration vervollständigen - Kernfeature
3. **Steps 6-9:** Video mit Narration - Post-MVP, aber high-value
4. **Step 10:** UX Polish - Nice-to-have

## Dependencies

```
Step 1 → Step 2 (sequentiell)
Step 3 → Step 4 → Step 5 (sequentiell)
Steps 6-9 (parallel möglich, dann sequentiell für Assembly)
Step 10 (unabhängig)
```
