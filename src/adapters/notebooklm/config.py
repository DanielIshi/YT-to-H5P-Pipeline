"""
Configuration for NotebookLM Adapter
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class NotebookLMConfig:
    """Configuration for NotebookLM browser automation"""

    # URLs
    base_url: str = "https://notebooklm.google.com"

    # CDP connection (for connecting to existing Chrome with pre-authenticated session)
    cdp_url: Optional[str] = None  # e.g., "http://localhost:9222"

    # Browser settings
    headless: bool = False  # NotebookLM requires visible browser for auth
    slow_mo: int = 100  # Milliseconds between actions (avoid rate limiting)

    # Timeouts (milliseconds)
    default_timeout: int = 30000
    upload_timeout: int = 60000
    audio_generation_timeout: int = 300000  # 5 min for audio generation
    video_generation_timeout: int = 600000  # 10 min for video generation

    # Chrome profile for persistent login
    user_data_dir: Optional[Path] = None
    profile_name: str = "Default"

    # Limits
    max_sources_per_notebook: int = 50
    max_retries: int = 3

    # Output directories
    output_dir: Path = field(default_factory=lambda: Path("output/notebooklm"))
    audio_dir: Path = field(default_factory=lambda: Path("output/notebooklm/audio"))
    video_dir: Path = field(default_factory=lambda: Path("output/notebooklm/video"))
    mindmap_dir: Path = field(default_factory=lambda: Path("output/notebooklm/mindmap"))

    def __post_init__(self):
        """Setup directories and defaults"""
        if self.user_data_dir is None:
            # Use default Chrome profile location
            if os.name == 'nt':  # Windows
                self.user_data_dir = Path(os.environ.get(
                    'LOCALAPPDATA', ''
                )) / "Google" / "Chrome" / "User Data"
            else:  # Linux/Mac
                self.user_data_dir = Path.home() / ".config" / "google-chrome"

        # Ensure output directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.mindmap_dir.mkdir(parents=True, exist_ok=True)


# Selectors for NotebookLM UI elements (may need updates if UI changes)
class Selectors:
    """CSS/XPath selectors for NotebookLM UI elements"""

    # Navigation & Auth (supports English and German UI)
    SIGN_IN_BUTTON = 'button:has-text("Sign in"), button:has-text("Anmelden")'
    CREATE_NOTEBOOK_BUTTON = 'button:has-text("Create"), button:has-text("Neu erstellen"), button:has-text("add")'
    NEW_NOTEBOOK_BUTTON = 'button:has-text("New notebook"), button:has-text("Neues Notebook")'

    # Notebook management
    NOTEBOOK_TITLE_INPUT = 'input[aria-label="Notebook title"]'
    NOTEBOOK_LIST = '[data-testid="notebook-list"]'
    NOTEBOOK_ITEM = '[data-testid="notebook-item"]'
    DELETE_NOTEBOOK = 'button:has-text("Delete")'

    # Source upload (EN/DE)
    ADD_SOURCE_BUTTON = 'button:has-text("Add source"), button:has-text("Quelle hinzufügen"), button:has-text("Quellen hinzufügen")'
    UPLOAD_FILE_OPTION = 'button:has-text("Upload"), button:has-text("Hochladen"), button:has-text("Quellen hochladen")'
    PASTE_TEXT_OPTION = 'text=Paste text, text=Kopierter Text, text=Text einfügen'
    YOUTUBE_OPTION = 'text=YouTube'
    WEBSITE_OPTION = 'text=Website'

    FILE_INPUT = 'input[type="file"]'
    TEXT_INPUT_AREA = 'textarea[placeholder*="Paste"], textarea[placeholder*="Text hier einfügen"], textarea[placeholder*="einfügen"]'
    URL_INPUT = 'input[placeholder*="URL"]'
    INSERT_BUTTON = 'button:has-text("Insert"), button:has-text("Einfügen")'

    # Studio panel (right side) - EN/DE - Updated Nov 2025 UI
    STUDIO_PANEL = '[data-testid="studio-panel"]'
    AUDIO_OVERVIEW_TAB = 'button:has-text("Audio Overview"), button:has-text("Audio-Zusammenfassung")'
    GENERATE_AUDIO_BUTTON = 'button:has-text("Generate"), button:has-text("Generieren"), button:has-text("Erstellen")'
    AUDIO_PLAYER = 'audio'
    DOWNLOAD_AUDIO_BUTTON = 'button[aria-label*="Download"], button[aria-label*="Herunterladen"]'

    # Content generation - EN/DE - Updated Nov 2025 UI
    # New Studio panel cards (not tabs anymore)
    REPORTS_CARD = 'button:has-text("Reports"), button:has-text("Berichte")'
    FLASHCARDS_CARD = 'button:has-text("Flashcards"), button:has-text("Karteikarten")'
    QUIZ_CARD = 'button:has-text("Quiz")'
    INFOGRAPHIC_CARD = 'button:has-text("Infographic"), button:has-text("Infografik")'
    PRESENTATION_CARD = 'button:has-text("Presentation"), button:has-text("Präsentation")'

    # Legacy selectors (may still work in some regions)
    FAQ_TAB = 'button:has-text("FAQ"), button:has-text("Häufig gestellte Fragen")'
    STUDY_GUIDE_TAB = 'button:has-text("Study Guide"), button:has-text("Lernhilfe"), button:has-text("Lernleitfaden")'
    BRIEFING_TAB = 'button:has-text("Briefing Doc"), button:has-text("Briefing-Dok"), button:has-text("Briefing")'
    TIMELINE_TAB = 'button:has-text("Timeline"), button:has-text("Zeitleiste")'

    # Content extraction
    GENERATED_CONTENT = '[data-testid="generated-content"]'
    COPY_BUTTON = 'button[aria-label*="Copy"]'

    # Loading states
    LOADING_SPINNER = '[data-testid="loading"]'
    PROGRESS_BAR = '[role="progressbar"]'

    # Error states
    ERROR_MESSAGE = '[data-testid="error-message"]'
    RETRY_BUTTON = 'button:has-text("Retry")'

    # Mindmap (Studio panel) - EN/DE
    MINDMAP_TAB = 'button:has-text("Mind map"), button:has-text("Mindmap"), button:has-text("Gedankenkarte")'
    MINDMAP_CONTAINER = '[class*="mindmap"], [data-testid="mindmap"]'
    MINDMAP_SVG = 'svg[class*="mindmap"], svg'
    MINDMAP_NODE = 'g[class*="node"], g[data-node]'
    MINDMAP_EXPAND_ALL = 'button:has-text("Expand all"), button:has-text("Alle erweitern"), button:has-text("Alle einblenden")'
    MINDMAP_COLLAPSE_ALL = 'button:has-text("Collapse"), button:has-text("Zuklappen"), button:has-text("Einklappen")'
    MINDMAP_NODE_TEXT = 'text, [class*="label"]'
    MINDMAP_CONNECTION = 'path[class*="link"], line'

    # Video Overview (Studio panel) - EN/DE - Updated Nov 2025 UI
    VIDEO_OVERVIEW_TAB = 'button:has-text("Video Overview"), button:has-text("Videoübersicht"), button:has-text("Video-Zusammenfassung")'
    VIDEO_FORMAT_EXPLAINER = 'button:has-text("Explainer"), button:has-text("Erklärvideo")'
    VIDEO_FORMAT_BRIEF = 'button:has-text("Brief"), button:has-text("Kurz")'
    VIDEO_STYLE_SELECTOR = '[class*="style-selector"], [data-testid="style-selector"]'
    VIDEO_STYLE_CLASSIC = 'button:has-text("Classic"), button:has-text("Klassisch")'
    VIDEO_STYLE_WHITEBOARD = 'button:has-text("Whiteboard")'
    VIDEO_STYLE_WATERCOLOR = 'button:has-text("Watercolor"), button:has-text("Aquarell")'
    GENERATE_VIDEO_BUTTON = 'button:has-text("Generate"), button:has-text("Generieren"), button:has-text("Erstellen")'
    VIDEO_PLAYER = 'video'
    DOWNLOAD_VIDEO_BUTTON = 'button[aria-label*="Download"], button[aria-label*="Herunterladen"]'
