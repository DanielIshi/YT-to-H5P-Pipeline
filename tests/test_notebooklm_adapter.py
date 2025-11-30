"""
Tests for NotebookLM Adapter

Note: These tests require manual authentication on first run.
Run with: pytest tests/test_notebooklm_adapter.py -v -s
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.notebooklm.config import NotebookLMConfig, Selectors
from src.adapters.notebooklm.notebook_manager import (
    NotebookManager, Notebook, Source, SourceType
)
from src.adapters.notebooklm.content_extractor import (
    ContentExtractor, ContentType, GeneratedContent, ExtractedData
)
from src.adapters.notebooklm.audio_downloader import AudioDownloader, AudioOverview


class TestNotebookLMConfig:
    """Tests for configuration"""

    def test_default_config(self):
        config = NotebookLMConfig()
        assert config.base_url == "https://notebooklm.google.com"
        assert config.headless is False
        assert config.max_sources_per_notebook == 50

    def test_output_dirs_created(self, tmp_path):
        config = NotebookLMConfig(
            output_dir=tmp_path / "output",
            audio_dir=tmp_path / "audio"
        )
        assert config.output_dir.exists()
        assert config.audio_dir.exists()


class TestSelectors:
    """Tests for UI selectors"""

    def test_selectors_defined(self):
        assert Selectors.SIGN_IN_BUTTON
        assert Selectors.CREATE_NOTEBOOK_BUTTON
        assert Selectors.ADD_SOURCE_BUTTON
        assert Selectors.AUDIO_OVERVIEW_TAB


class TestNotebook:
    """Tests for Notebook dataclass"""

    def test_notebook_creation(self):
        notebook = Notebook(
            id="test-123",
            title="Test Notebook",
            url="https://notebooklm.google.com/notebook/test-123"
        )
        assert notebook.id == "test-123"
        assert notebook.title == "Test Notebook"
        assert notebook.sources == []

    def test_notebook_with_sources(self):
        source = Source(type=SourceType.TEXT, content="Test content")
        notebook = Notebook(
            id="test-123",
            title="Test",
            sources=[source]
        )
        assert len(notebook.sources) == 1
        assert notebook.sources[0].type == SourceType.TEXT


class TestSource:
    """Tests for Source dataclass"""

    def test_text_source(self):
        source = Source(
            type=SourceType.TEXT,
            content="Learning about AI...",
            title="AI Basics"
        )
        assert source.type == SourceType.TEXT
        assert "AI" in source.content

    def test_youtube_source(self):
        source = Source(
            type=SourceType.YOUTUBE,
            content="https://youtube.com/watch?v=abc123"
        )
        assert source.type == SourceType.YOUTUBE
        assert "youtube" in source.content

    def test_file_source(self):
        source = Source(
            type=SourceType.FILE,
            content="/path/to/document.pdf"
        )
        assert source.type == SourceType.FILE


class TestContentType:
    """Tests for ContentType enum"""

    def test_content_types(self):
        assert ContentType.FAQ.value == "faq"
        assert ContentType.STUDY_GUIDE.value == "study_guide"
        assert ContentType.BRIEFING_DOC.value == "briefing_doc"
        assert ContentType.TIMELINE.value == "timeline"


class TestGeneratedContent:
    """Tests for GeneratedContent dataclass"""

    def test_generated_content(self):
        content = GeneratedContent(
            type=ContentType.FAQ,
            title="Test FAQ",
            content="Q: What is AI?\nA: Artificial Intelligence..."
        )
        assert content.type == ContentType.FAQ
        assert "What is AI" in content.content
        assert content.generated_at is not None


class TestExtractedData:
    """Tests for ExtractedData dataclass"""

    def test_extracted_data(self):
        data = ExtractedData(
            notebook_id="test-123",
            notebook_title="AI Basics"
        )
        assert data.notebook_id == "test-123"
        assert data.faq is None
        assert data.study_guide is None
        assert data.key_topics == []


class TestAudioOverview:
    """Tests for AudioOverview dataclass"""

    def test_audio_overview(self):
        audio = AudioOverview(
            notebook_id="test-123",
            notebook_title="AI Podcast"
        )
        assert audio.notebook_id == "test-123"
        assert audio.status == "pending"
        assert audio.file_path is None


class TestNotebookManagerMocked:
    """Mocked tests for NotebookManager"""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.page = MagicMock()
        client.config = NotebookLMConfig()
        client.wait_for_loading = AsyncMock()
        client.get_current_url = AsyncMock(return_value="https://notebooklm.google.com/notebook/new-id")
        client.type_with_clear = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_create_notebook(self, mock_client):
        mock_client.page.click = AsyncMock()
        mock_client.page.query_selector = AsyncMock(return_value=MagicMock())
        mock_client.page.keyboard = MagicMock()
        mock_client.page.keyboard.press = AsyncMock()

        manager = NotebookManager(mock_client)
        notebook = await manager.create_notebook("Test Notebook")

        assert notebook.title == "Test Notebook"
        assert notebook.id == "new-id"

    @pytest.mark.asyncio
    async def test_extract_notebook_id(self, mock_client):
        manager = NotebookManager(mock_client)

        # Test valid URL
        url = "https://notebooklm.google.com/notebook/abc123"
        assert manager._extract_notebook_id(url) == "abc123"

        # Test URL with trailing slash
        url = "https://notebooklm.google.com/notebook/abc123/"
        assert manager._extract_notebook_id(url) == "abc123"

        # Test None
        assert manager._extract_notebook_id(None) is None


class TestContentExtractorMocked:
    """Mocked tests for ContentExtractor"""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.page = MagicMock()
        client.config = NotebookLMConfig()
        client.wait_for_loading = AsyncMock()
        client.get_current_url = AsyncMock(return_value="https://notebooklm.google.com/notebook/test")
        client.check_for_error = AsyncMock(return_value=None)
        return client

    @pytest.mark.asyncio
    async def test_export_to_markdown(self, mock_client):
        extractor = ContentExtractor(mock_client)

        data = ExtractedData(
            notebook_id="test-123",
            notebook_title="AI Basics",
            summary="AI is transforming the world",
            key_topics=["Machine Learning", "Neural Networks"]
        )
        data.faq = GeneratedContent(
            type=ContentType.FAQ,
            title="FAQ",
            content="Q: What is AI?\nA: Artificial Intelligence"
        )

        markdown = await extractor.export_to_markdown(data)

        assert "# AI Basics" in markdown
        assert "AI is transforming" in markdown
        assert "Machine Learning" in markdown
        assert "## FAQ" in markdown
        assert "What is AI" in markdown


class TestAudioDownloaderMocked:
    """Mocked tests for AudioDownloader"""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.page = MagicMock()
        client.config = NotebookLMConfig()
        client.wait_for_loading = AsyncMock()
        client.get_current_url = AsyncMock(return_value="https://notebooklm.google.com/notebook/test")
        client.check_for_error = AsyncMock(return_value=None)
        return client

    def test_default_output_path(self, mock_client, tmp_path):
        mock_client.config.audio_dir = tmp_path

        downloader = AudioDownloader(mock_client)
        notebook = Notebook(id="test", title="My Test Notebook")

        path = downloader._default_output_path(notebook)

        assert path.parent == tmp_path
        # Title can have spaces or underscores depending on implementation
        assert "My" in path.name and "Test" in path.name and "Notebook" in path.name
        assert path.suffix == ".mp3"

    def test_default_output_path_long_title(self, mock_client, tmp_path):
        mock_client.config.audio_dir = tmp_path

        downloader = AudioDownloader(mock_client)
        notebook = Notebook(id="test", title="A" * 100)  # Very long title

        path = downloader._default_output_path(notebook)

        # Title should be truncated
        assert len(path.stem) <= 70  # 50 chars + timestamp


# Integration test (requires manual auth)
@pytest.mark.skip(reason="Integration test - requires manual authentication")
class TestNotebookLMIntegration:
    """Integration tests - run manually with authentication"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        from src.adapters.notebooklm.client import NotebookLMClient

        async with NotebookLMClient() as client:
            # This will require manual login
            authenticated = await client.ensure_authenticated()
            assert authenticated

            # Create notebook
            manager = NotebookManager(client)
            notebook = await manager.create_notebook("Integration Test")
            assert notebook.id

            # Add content
            test_content = """
            Artificial Intelligence (AI) is the simulation of human intelligence
            by machines. Key concepts include:
            - Machine Learning
            - Neural Networks
            - Natural Language Processing
            """
            await manager.add_text_source(notebook, test_content)

            # Extract FAQ
            extractor = ContentExtractor(client)
            faq = await extractor.extract_faq(notebook)
            assert faq is not None

            # Cleanup
            await manager.delete_notebook(notebook)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
