# YouTube to H5P E-Learning Pipeline

## Zweck

Automatische Generierung von H5P E-Learning-Modulen aus YouTube-Untertiteln. Ein LLM analysiert das Transcript und erstellt einen didaktisch strukturierten Lernpfad mit verschiedenen interaktiven Content-Types.

## Tech Stack

| Komponente | Technologie | Ort |
|------------|-------------|-----|
| **Entwicklung** | Python 3.12, Windows | Lokal |
| **VPS** | Ubuntu, SSH | 148.230.71.150 |
| **Moodle** | Docker (bitnami/moodle) | VPS :8080 |
| **Supabase** | Docker (PostgreSQL + REST) | VPS :8000 |
| **LLM** | OpenAI gpt-4o-mini | API |

## Architektur

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Supabase   │────▶│   Python     │────▶│   Moodle    │
│ (Transcripts)│     │ (Generator)  │     │ (H5P Import)│
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       ▼                   ▼                    ▼
  youtube_urls      OpenAI API           H5P Activities
  (subtitles)       (LLM Prompt)         (7 Typen)
```

## H5P Content-Types (7 implementiert)

| Typ | Zweck | Didaktische Phase |
|-----|-------|-------------------|
| **Dialogcards** | Karteikarten für Begriffe | Passiv - Einführung |
| **Accordion** | Aufklappbare Erklärungen | Passiv - Vertiefung |
| **MultiChoice** | Multiple Choice Quiz | Aktiv - Prüfung |
| **TrueFalse** | Wahr/Falsch Aussagen | Aktiv - Schnellcheck |
| **Blanks** | Lückentext ausfüllen | Aktiv - Anwendung |
| **DragAndDrop** | Begriffe zuordnen | Aktiv - Verknüpfung |
| **Summary** | Kernpunkte auswählen | Abschluss |

### Noch nicht implementiert:
- **InteractiveVideo** - YouTube mit eingebetteten Quizfragen (benötigt Timestamps)
- **ImageHotspots** - Bild mit klickbaren Annotationen (benötigt Bild-URL)

## Dateien

```
src/services/h5p/
├── learning_path_generator.py  # Hauptgenerator (7 Content-Types)
├── multi_quiz_generator.py     # Legacy: Nur MultiChoice
├── cli_youtube_to_h5p.py       # CLI v1
├── cli_youtube_to_h5p_v2.py    # CLI v2
├── content_types.py            # Pydantic Models
├── package_builder.py          # H5P ZIP Builder
└── __init__.py
```

## CLI Nutzung

```bash
# Auf VPS ausführen:
cd /home/claude/python-modules/src/services/h5p

# Mit YouTube URL ID aus Supabase:
python3 learning_path_generator.py \
  --youtube-url-id 2454 \
  --courseid 2

# Mit Transcript-Datei:
python3 learning_path_generator.py \
  --transcript-file transcript.txt \
  --title "Mein Kurs" \
  --courseid 2

# Neuen Kurs erstellen:
python3 learning_path_generator.py \
  --youtube-url-id 2454 \
  --createcourse \
  --coursename "KI Grundlagen"
```

## Deployment

### Lokal → VPS:
```bash
scp learning_path_generator.py root@148.230.71.150:/home/claude/python-modules/src/services/h5p/
```

### VPS Pfade:
- **Python Code:** `/home/claude/python-modules/`
- **Moodle Container:** `moodle-app`
- **H5P Import Script:** `/opt/bitnami/moodle/local/import_h5p.php`

## Supabase Schema

```sql
-- youtube_urls Tabelle
CREATE TABLE youtube_urls (
  id SERIAL PRIMARY KEY,
  url TEXT,
  title TEXT,
  subtitles TEXT,  -- Transcript für LLM
  created_at TIMESTAMP
);
```

## Moodle H5P Import

Der Import erfolgt via PHP-Script im Moodle-Container:

```bash
docker exec moodle-app php /opt/bitnami/moodle/local/import_h5p.php \
  --file=/tmp/generated.h5p \
  --title="Quiz Titel" \
  --course=2
```

## H5P Package Struktur

```
activity.h5p (ZIP)
├── h5p.json           # Manifest mit Library-Dependencies
└── content/
    └── content.json   # Eigentlicher Inhalt
```

### Beispiel h5p.json (MultiChoice):
```json
{
  "title": "Quiz",
  "language": "de",
  "mainLibrary": "H5P.MultiChoice",
  "preloadedDependencies": [
    {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 16},
    {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
    {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5}
  ]
}
```

## LLM Prompt Struktur

Der `LEARNING_PATH_PROMPT` instruiert das LLM:
1. Transcript analysieren
2. 8-12 Aktivitäten in didaktischer Reihenfolge erstellen
3. Mit passiven Elementen beginnen (Dialogcards, Accordion)
4. Aktive Elemente folgen (Quiz, Blanks, TrueFalse)
5. Mit Summary abschließen
6. JSON Output mit allen Aktivitätsdaten

## Environment Variables (.env)

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=http://148.230.71.150:8000
SUPABASE_SERVICE_KEY=eyJ...
```

## Bekannte Einschränkungen

1. **Course Presentation funktioniert nicht** - JavaScript-Kompatibilitätsprobleme in Moodle
   - **Workaround:** Separate H5P-Aktivitäten statt einer Course Presentation

2. **InteractiveVideo benötigt Timestamps** - LLM kann keine genauen Video-Timestamps ableiten
   - **TODO:** Timestamps aus YouTube-Untertiteln extrahieren

3. **ImageHotspots benötigt Bild-URLs** - Keine automatische Bildextraktion
   - **TODO:** YouTube Thumbnails als Fallback

## Typischer Workflow

1. YouTube-Video in Supabase speichern (mit Untertiteln)
2. `learning_path_generator.py --youtube-url-id X --courseid Y` ausführen
3. LLM generiert Lernpfad-Struktur
4. Builder-Funktionen erstellen H5P-Pakete
5. Import in Moodle via PHP-Script
6. 7 H5P-Aktivitäten im Kurs verfügbar

## Generiertes Ergebnis (Beispiel)

```
Moodle Kurs "KI Updates 2024":
├── 1. Wichtige Begriffe (Dialogcards)
├── 2. Kernaussagen (Accordion)
├── 3. Verständnischeck (MultiChoice)
├── 4. Lückentext (Blanks)
├── 5. Faktencheck (TrueFalse)
├── 6. Zuordnung (DragAndDrop)
└── 7. Zusammenfassung (Summary)
```

### Repo rules

No scripts/, logs/, kb/, data/ at repo root.

Experiments live in src/ with tests.

Root‑level run_*.py are allowed as entry points only.




### Tech Stack & Architecture (Single Source of Truth)

Core: Python 3.12, FFmpeg, Playwright, httpx, pydantic

Orchestration: n8n (Docker)

Storage/DB: Supabase (Postgres + Storage + pgvector)

Host code path (canonical):

Host: /home/claude/python-modules (actual Python execution location)

High Level Flow
n8n (Docker) → SSH Node → Python on HOST (/home/claude/python-modules) → Supabase

Rule: Python code runs on HOST as user 'claude'. n8n uses SSH Node to execute Python commands. Docker is ONLY for n8n itself (irrelevant implementation detail for Python execution).

3) Environments

Local (Windows): dev + tests; optional local Docker Compose

VPS: Linux host; Dockerized n8n; volume mounts as above

Keep OS details abstract here; scripts infer host specifics. Don’t hardcode distro names.


Docker Compose (optional for full stack)

docker compose up -d
curl http://localhost:5678/ # n8n health


SSH Node executes Python module on HOST in working dir /home/claude/python-modules

Python prints compact JSON to stdout for n8n to parse

NEVER use "Execute Command" node - ALWAYS use SSH node (User: claude, Credential: SSH Password account).

Expressions: prefer $json.foo and string concatenation. Avoid template literals like ${}.







