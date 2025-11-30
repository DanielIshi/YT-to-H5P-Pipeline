# H5P Content-Type Matrix & Didaktische Strategie

> **Schlüsseldokument für LLM-Generierung** - Definiert optimalen Einsatz jedes Content-Types für maximales Lernerlebnis.

---

## 1. Lernmodi: Passiv vs. Aktiv

### Passiv (Wissensvermittlung)
Der Lernende **konsumiert** Inhalte. Effektivität hängt stark vom Medium ab.

| Engagement-Level | Medium | Retention | Empfehlung |
|------------------|--------|-----------|------------|
| **Langweilig** | Langer Text, PDFs | ~10% | Vermeiden |
| **Neutral** | Accordion, Dialogcards | ~20% | Sparsam einsetzen |
| **Interessant** | Bilder, Infografiken | ~30% | Gut als Einstieg |
| **Sehr interessant** | Video mit Narration | ~50% | Bevorzugen |
| **Exzellent** | Interaktives Video | ~60% | Optimal für Vertiefung |

### Aktiv (Wissensanwendung)
Der Lernende **handelt** und wendet Wissen an. Höchste Retention.

| Engagement-Level | Aktivität | Retention | Empfehlung |
|------------------|-----------|-----------|------------|
| **Gut** | TrueFalse, MultiChoice | ~70% | Standard-Prüfung |
| **Sehr gut** | Blanks, DragText | ~80% | Aktive Anwendung |
| **Exzellent** | Eigene Erklärung, Spracheingabe | ~90% | Zukunft: Speech-Input |

> **Goldene Regel:** 30% Passiv (interessant!) → 60% Aktiv → 10% Reflexion

---

## 2. Content-Type Matrix

### 2.1 Passive Content-Types (Wissensvermittlung)

| Content-Type | Engagement | Optimaler Einsatz | Use Cases | NICHT verwenden |
|--------------|------------|-------------------|-----------|-----------------|
| **Dialogcards** | Neutral | Begriffe & Definitionen | Fachbegriffe, Glossar, "Was ist X?" | Komplexe Prozesse |
| **Accordion** | Neutral | Strukturierte Erklärungen | FAQ, Kapitel-Übersicht | Prüfungen, aktives Lernen |
| **ImageHotspots** | Interessant | Visuelle Exploration | Anatomie, Maschinen, UI-Erklärung | Abstrakte Konzepte |
| **MindMap** | Interessant | Zusammenhänge visualisieren | Themen-Überblick, Vernetzung | Detailwissen |
| **Video** | Sehr interessant | Erklärungen, Demonstrationen | Tutorials, Storytelling | Reine Faktenlisten |
| **InteractiveVideo** | Exzellent | Engagement + Prüfung kombiniert | Längere Videos (>5min) | Kurze Clips |
| **Audio Summary** | Interessant | Unterwegs lernen, Wiederholung | Podcast-Stil, Zusammenfassung | Visuelle Themen |

### 2.2 Aktive Content-Types (Wissensanwendung)

| Content-Type | Engagement | Optimaler Einsatz | Use Cases | NICHT verwenden |
|--------------|------------|-------------------|-----------|-----------------|
| **TrueFalse** | Gut | Schneller Faktencheck | Mythen klären, Schnelltest | Nuancierte Fragen |
| **MultiChoice** | Gut | Verständnisprüfung | Konzeptfragen, Anwendung | Einfache Ja/Nein |
| **Blanks** | Sehr gut | Begriffe einprägen | Definitionen, Formeln, Fachsprache | Kreative Antworten |
| **DragText** | Sehr gut | Zuordnungen, Kategorien | Begriff→Kategorie, Reihenfolgen | Visuelle Inhalte |
| **DragText auf Bild** | Exzellent | Visuelle Beschriftung | Organe, Flowcharts, Diagramme | Textlastige Inhalte |
| **Summary** | Gut | Kernaussagen identifizieren | Abschluss, Reflexion | Detailfragen |

### 2.3 MVP Content-Types (verfügbar)

| Content-Type | Status | Engagement | Optimaler Einsatz |
|--------------|--------|------------|-------------------|
| **TrueFalse** | ✅ MVP | Gut | Schneller Faktencheck |
| **Blanks** | ✅ MVP | Sehr gut | Begriffe einprägen |
| **DragText** | ✅ MVP | Sehr gut | Zuordnungen |
| **Summary** | ✅ MVP | Gut | Kernaussagen |
| **MultiChoice** | ✅ MVP | Gut | Verständnisprüfung |
| **Dialogcards** | ✅ MVP | Neutral | Begriffe & Definitionen |
| **Accordion** | ✅ MVP | Neutral | Strukturierte Erklärungen |

### 2.4 Post-MVP Content-Types (geplant)

| Content-Type | Engagement | Optimaler Einsatz | Technologie |
|--------------|------------|-------------------|-------------|
| **LernVideo (generiert)** | Sehr interessant | Automatische Video-Erstellung | ElevenLabs (Audio) + Flux/Gemini 3 (Grafiken) + ffmpeg |
| **ImageHotspots** | Interessant | Visuelle Exploration | Gemini 3 (Infografiken) |
| **DragText auf Bild** | Exzellent | Visuelle Beschriftung | Flux 1.5-2.0 / Gemini 3 |
| **InteractiveVideo** | Exzellent | Engagement + Prüfung kombiniert | YouTube + H5P Overlay |
| **MindMap (navigierbar)** | Sehr interessant | Themen-Exploration | Mermaid.js / D3.js |
| **Audio Summary** | Interessant | Kapitel-Zusammenfassung | ElevenLabs TTS |
| **Speech-Input Quiz** | Exzellent | Eigene Erklärung = höchste Retention | Web Speech API / Whisper |

### 2.5 Generierungs-Stack (Post-MVP)

```
┌─────────────────────────────────────────────────────┐
│              CONTENT GENERATION STACK               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  AUDIO:                                             │
│  └─ ElevenLabs TTS (Deutsch, professionell)        │
│                                                     │
│  GRAFIKEN:                                          │
│  ├─ Gemini 3 → Infografiken mit korrektem Text     │
│  └─ Flux 1.5-2.0 → Künstlerische Illustrationen    │
│                                                     │
│  VIDEO:                                             │
│  └─ ffmpeg → Audio + Grafiken zusammenbauen        │
│                                                     │
│  DIAGRAMME:                                         │
│  └─ Mermaid.js → Flowcharts, MindMaps              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 3. Didaktische Reihenfolge (Lernpfad)

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPTIMALER LERNPFAD                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE 1: NEUGIER WECKEN (5%)                                  │
│  ├─ MindMap / ImageHotspots                                    │
│  └─ "Was erwartet mich?" - Überblick                           │
│                                                                 │
│  PHASE 2: VERSTEHEN (25%)                                       │
│  ├─ Video / InteractiveVideo                                   │
│  ├─ Dialogcards (Begriffe)                                     │
│  └─ Accordion (Vertiefung)                                     │
│                                                                 │
│  PHASE 3: ANWENDEN (50%)                                        │
│  ├─ Blanks (Begriffe festigen)                                 │
│  ├─ DragText (Zuordnungen)                                     │
│  ├─ DragText auf Bild (visuell)                                │
│  └─ MultiChoice / TrueFalse (Prüfung)                          │
│                                                                 │
│  PHASE 4: REFLEKTIEREN (15%)                                    │
│  ├─ Summary (Kernaussagen)                                     │
│  └─ Audio Summary (Wiederholung)                               │
│                                                                 │
│  PHASE 5: VERTIEFEN (5%)                                        │
│  └─ Audio FAQ / Weiterführende Links                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Gewichtung für LLM-Generierung

### 4.1 Standard-Lernpfad (8-12 Aktivitäten)

| Phase | Gewicht | Anzahl | Content-Types |
|-------|---------|--------|---------------|
| Neugier | 5% | 0-1 | MindMap, ImageHotspots |
| Verstehen | 25% | 2-3 | Video, Dialogcards, Accordion |
| Anwenden | 50% | 4-6 | Blanks, DragText, MultiChoice, TrueFalse |
| Reflektieren | 15% | 1-2 | Summary |
| Vertiefen | 5% | 0-1 | Audio FAQ |

### 4.2 Engagement-Multiplikator

Bevorzuge Content-Types mit höherem Engagement:

```
Engagement Score (für LLM-Auswahl):
- Exzellent:      1.5x Gewicht (InteractiveVideo, DragText auf Bild, Speech-Input)
- Sehr interessant: 1.2x Gewicht (Video, MindMap, Blanks, DragText)
- Interessant:    1.0x Gewicht (ImageHotspots, Audio)
- Neutral:        0.7x Gewicht (Accordion, Dialogcards)
- Langweilig:     0.3x Gewicht (Langer Text) → VERMEIDEN
```

### 4.3 Varianz-Regel

> **Keine zwei gleichen Content-Types hintereinander!**
>
> Abwechslung hält das Engagement hoch.

---

## 5. Bildgenerierung-Strategie

### 5.1 Wann Bilder generieren?

| Trigger im Transcript | Bild-Typ | Generator |
|----------------------|----------|-----------|
| Anatomie, Körperteile | Beschriftetes Diagramm | Gemini 3 |
| Prozess, Ablauf, Schritte | Flowchart | Gemini 3 |
| Vergleich A vs B | Infografik | Gemini 3 |
| Technisches System | Technische Zeichnung | Gemini 3 |
| Geografisch, Ort | Karte mit Markierungen | Gemini 3 |
| Zeitlicher Ablauf | Timeline | Gemini 3 |

### 5.2 Gemini 3 Prompt-Template

```
Erstelle eine klare Infografik zum Thema: [THEMA]

Anforderungen:
- Beschriftungen müssen LESBAR und KORREKT sein
- Deutscher Text
- Professioneller, cleaner Stil
- Geeignet für interaktive Hotspots
- Auflösung: 1920x1080

Elemente: [LISTE DER ZU BESCHRIFTENDEN ELEMENTE]
```

---

## 6. Audio-Content-Strategie (NotebookLM)

### 6.1 Verfügbare Audio-Formate

| Format | Länge | Einsatz | Generierung |
|--------|-------|---------|-------------|
| **Deep Dive Podcast** | 10-20 min | Hauptinhalt als Gespräch | NotebookLM |
| **Audio Summary** | 2-3 min | Schnelle Wiederholung | NotebookLM |
| **Audio FAQ** | 5-10 min | Häufige Fragen | NotebookLM |

### 6.2 Integration in Lernpfad

- **Podcast:** Als Alternative zu Video (Phase 2)
- **Summary:** Am Ende jedes Moduls (Phase 4)
- **FAQ:** Optional für Vertiefung (Phase 5)

---

## 7. LLM-Prompt Regeln (für learning_path_generator.py)

```python
CONTENT_TYPE_RULES = {
    # Engagement-Priorität (höher = bevorzugen)
    "priority": {
        "interactivevideo": 10,
        "dragtext_image": 9,
        "blanks": 8,
        "dragtext": 7,
        "multichoice": 6,
        "truefalse": 5,
        "summary": 5,
        "imagehotspots": 4,
        "dialogcards": 3,
        "accordion": 2,
    },

    # Phasen-Zuordnung
    "phases": {
        "intro": ["imagehotspots", "mindmap"],
        "understand": ["interactivevideo", "dialogcards", "accordion"],
        "apply": ["blanks", "dragtext", "dragtext_image", "multichoice", "truefalse"],
        "reflect": ["summary"],
    },

    # Varianz: Max gleiche Types hintereinander
    "max_consecutive_same_type": 1,

    # Gewichtung
    "phase_weights": {
        "intro": 0.05,
        "understand": 0.25,
        "apply": 0.50,
        "reflect": 0.15,
        "extend": 0.05,
    }
}
```

---

## 8. Qualitätskriterien

### Was macht einen Lernpfad INTERESSANT?

1. **Visuell ansprechend** - Bilder, Videos statt Textwände
2. **Abwechslungsreich** - Verschiedene Content-Types
3. **Aktiv** - Mindestens 50% aktive Elemente
4. **Progressiv** - Vom Einfachen zum Komplexen
5. **Relevant** - Praxisnahe Beispiele aus dem Transcript
6. **Kurz** - Einzelne Aktivitäten < 3 Minuten

### Was macht einen Lernpfad LANGWEILIG?

1. ❌ Nur Text / Accordion
2. ❌ Zu viele gleiche Content-Types
3. ❌ Keine visuellen Elemente
4. ❌ Nur passive Inhalte
5. ❌ Zu lange Einzelaktivitäten
6. ❌ Generische Fragen ohne Bezug zum Inhalt

---

## Changelog

| Datum | Änderung |
|-------|----------|
| 2024-11-30 | Initial: Matrix mit allen aktuellen Content-Types |
| 2024-11-30 | Passiv/Aktiv Klassifizierung hinzugefügt |
| 2024-11-30 | Gewichtung und LLM-Regeln definiert |
| 2024-11-30 | Zukünftige Types (MindMap, Audio) vorbereitet |
