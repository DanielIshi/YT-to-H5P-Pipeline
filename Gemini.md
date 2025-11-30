# Gemini Project Guide: YouTube to H5P E-Learning Pipeline

## 1. Project Purpose

This project automates the generation of interactive H5P e-learning modules from YouTube video transcripts. An LLM analyzes the transcript to create a didactically structured learning path with various H5P content types, which can then be imported into Moodle.

## 2. Tech Stack

| Component | Technology | Environment |
|---|---|---|
| **Core Logic** | Python 3.12 | Local (Windows) / VPS (Linux) |
| **Orchestration** | n8n (via Docker) | VPS |
| **Database/Storage** | Supabase (Postgres, Storage) | VPS (Docker) |
| **LMS** | Moodle (Bitnami Docker image) | VPS |
| **LLM** | OpenAI API (e.g., gpt-4o-mini) | Remote API |
| **E2E Testing**| Playwright | Local / VPS |

## 3. Architecture

The basic workflow is as follows:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Supabase   │────▶│   Python     │────▶│   Moodle    │
│ (Transcripts)│     │ (Generator)  │     │ (H5P Import)│
└─────────────┘     └──────────────┘     └─────────────┘
```

1.  A YouTube video URL is added to Supabase, and its transcript (subtitles) is stored.
2.  The Python generator script is triggered, which fetches the transcript.
3.  The script prompts an LLM to generate a structured learning path from the transcript.
4.  The Python script then uses this LLM output to build one or more `.h5p` package files (ZIP archives).
5.  A PHP script imports the generated `.h5p` files into a Moodle course.

## 4. Key Files & Directories

-   `src/h5p/learning_path_generator.py`: The main script that orchestrates the entire generation process.
-   `src/h5p/cli_youtube_to_h5p_v2.py`: The primary command-line interface for the generator.
-   `src/h5p/package_builder.py`: Builds the final `.h5p` ZIP archive.
-   `src/h5p/content_types.py`: Pydantic models defining the structure for each H5P content type.
-   `src/h5p/builders/`: Directory containing individual builder scripts for each H5P content type.
-   `src/scripts/deployment/deploy_h5p_26.php`: PHP script to import H5P packages into Moodle.
-   `tests/`: Contains unit and end-to-end tests.
-   `src/doc/CONTENT_TYPE_MATRIX.md`: **Crucial document** defining the strategy for using each content type.

## 5. H5P Content-Types

The pipeline supports generating multiple H5P content types to create a varied learning experience.

| Type | Purpose | Didactic Phase | Status |
|---|---|---|---|
| **Dialogcards** | Flashcards for terms/definitions | Introduction (Passive) | Implemented |
| **Accordion** | Collapsible sections for detailed explanations | Deepening (Passive) | Implemented |
| **MultiChoice** | Multiple choice quiz | Assessment (Active) | Implemented |
| **TrueFalse** | True/False statements | Quick Check (Active) | Implemented |
| **Blanks** | Fill-in-the-blanks text | Application (Active) | Implemented |
| **DragAndDrop**| Match terms to definitions | Association (Active) | Implemented |
| **Summary** | Select key summary points | Conclusion (Active) | Implemented |
| **InteractiveVideo**| Video with embedded questions | (Not Implemented) | Needs Timestamps |
| **ImageHotspots**| Image with clickable annotations | (Not Implemented) | Needs Image URL |

**Strategy:** Refer to `src/doc/CONTENT_TYPE_MATRIX.md` for the pedagogical strategy behind the selection and sequencing of these types.

## 6. CLI Usage

The primary entry point is `learning_path_generator.py`.

**Execute on the VPS:**
```bash
# Navigate to the correct directory on the VPS
cd /home/claude/python-modules/src/services/h5p

# Generate from a YouTube URL ID in Supabase
python3 learning_path_generator.py --youtube-url-id 2454 --courseid 2

# Generate from a local transcript file
python3 learning_path_generator.py --transcript-file transcript.txt --title "My Course" --courseid 2
```

## 7. Testing

### E2E Tests
The project uses Playwright for end-to-end testing against a live Moodle instance.

**To run E2E tests:**
- Ensure your `.env` file is configured with Moodle credentials.
- Run specific test files from the `tests/e2e/` directory. For example:
  ```bash
  python tests/e2e/test_h5p_rendering.py
  ```

### H5P Testing Rules
- **DO NOT** add new test activities when fixing a bug.
- **Test Course ID:** `22` (Name: `KIQuizKurs_1764356017`)
- Each content type should have only **ONE** corresponding test activity (e.g., "Test: TrueFalse", "Test: Blanks").

**Workflow for fixing a bug:**
1.  In Moodle, **delete** the faulty H5P activity.
2.  Fix the code.
3.  Re-run the generator to create the **same activity** with the same name.
4.  Verify the fix from a **student's perspective**, not as an admin. Admin preview can be misleading.

## 8. Environment & Deployment

-   **Environment Variables**: Copy `.env.example` to `.env` and fill in the required API keys and URLs (`OPENAI_API_KEY`, `SUPABASE_URL`, etc.).
-   **Deployment**: Code is developed locally (Windows) and deployed to a Linux VPS.
    ```bash
    # Example SCP command to copy a file to the VPS
    scp src/h5p/learning_path_generator.py root@148.230.71.150:/home/claude/python-modules/src/services/h5p/
    ```
-   **VPS Path**: The canonical execution path for Python code on the host is `/home/claude/python-modules`.

## 9. Project Conventions

-   No `scripts/`, `logs/`, `kb/`, or `data/` directories at the project root.
-   Experiments and new features belong in `src/` and must include tests.
-   Root-level `run_*.py` files are allowed only as simple entry points.
-   The Moodle Admin preview is not reliable. **Always test from a student's view.**
-   `embedTypes: ["iframe"]` is a mandatory field in the `h5p.json` manifest for all content types to ensure validation passes in Moodle.
