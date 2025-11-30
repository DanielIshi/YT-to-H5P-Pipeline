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

    # Browser settings
    headless: bool = False  # NotebookLM requires visible browser for auth
    slow_mo: int = 100  # Milliseconds between actions (avoid rate limiting)

    # Timeouts (milliseconds)
    default_timeout: int = 30000
    upload_timeout: int = 60000
    audio_generation_timeout: int = 300000  # 5 min for audio generation

    # Chrome profile for persistent login
    user_data_dir: Optional[Path] = None
    profile_name: str = "Default"

    # Limits
    max_sources_per_notebook: int = 50
    max_retries: int = 3

    # Output directories
    output_dir: Path = field(default_factory=lambda: Path("output/notebooklm"))
    audio_dir: Path = field(default_factory=lambda: Path("output/notebooklm/audio"))

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


# Selectors for NotebookLM UI elements (may need updates if UI changes)
class Selectors:
    """CSS/XPath selectors for NotebookLM UI elements"""

    # Navigation & Auth
    SIGN_IN_BUTTON = 'button:has-text("Sign in")'
    CREATE_NOTEBOOK_BUTTON = 'button:has-text("Create")'
    NEW_NOTEBOOK_BUTTON = 'button:has-text("New notebook")'

    # Notebook management
    NOTEBOOK_TITLE_INPUT = 'input[aria-label="Notebook title"]'
    NOTEBOOK_LIST = '[data-testid="notebook-list"]'
    NOTEBOOK_ITEM = '[data-testid="notebook-item"]'
    DELETE_NOTEBOOK = 'button:has-text("Delete")'

    # Source upload
    ADD_SOURCE_BUTTON = 'button:has-text("Add source")'
    UPLOAD_FILE_OPTION = 'button:has-text("Upload")'
    PASTE_TEXT_OPTION = 'button:has-text("Paste text")'
    YOUTUBE_OPTION = 'button:has-text("YouTube")'
    WEBSITE_OPTION = 'button:has-text("Website")'

    FILE_INPUT = 'input[type="file"]'
    TEXT_INPUT_AREA = 'textarea[placeholder*="Paste"]'
    URL_INPUT = 'input[placeholder*="URL"]'
    INSERT_BUTTON = 'button:has-text("Insert")'

    # Studio panel (right side)
    STUDIO_PANEL = '[data-testid="studio-panel"]'
    AUDIO_OVERVIEW_TAB = 'button:has-text("Audio Overview")'
    GENERATE_AUDIO_BUTTON = 'button:has-text("Generate")'
    AUDIO_PLAYER = 'audio'
    DOWNLOAD_AUDIO_BUTTON = 'button[aria-label*="Download"]'

    # Content generation
    FAQ_TAB = 'button:has-text("FAQ")'
    STUDY_GUIDE_TAB = 'button:has-text("Study Guide")'
    BRIEFING_TAB = 'button:has-text("Briefing Doc")'
    TIMELINE_TAB = 'button:has-text("Timeline")'

    # Content extraction
    GENERATED_CONTENT = '[data-testid="generated-content"]'
    COPY_BUTTON = 'button[aria-label*="Copy"]'

    # Loading states
    LOADING_SPINNER = '[data-testid="loading"]'
    PROGRESS_BAR = '[role="progressbar"]'

    # Error states
    ERROR_MESSAGE = '[data-testid="error-message"]'
    RETRY_BUTTON = 'button:has-text("Retry")'
