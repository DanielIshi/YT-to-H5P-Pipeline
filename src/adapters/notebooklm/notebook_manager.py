"""
NotebookLM Notebook Manager - Create, upload sources, manage notebooks
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Union
from dataclasses import dataclass
from enum import Enum

from .client import NotebookLMClient
from .config import Selectors

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Types of sources that can be added to NotebookLM"""
    FILE = "file"
    TEXT = "text"
    YOUTUBE = "youtube"
    WEBSITE = "website"


@dataclass
class Source:
    """A source to be added to a notebook"""
    type: SourceType
    content: str  # File path, URL, or text content
    title: Optional[str] = None


@dataclass
class Notebook:
    """Represents a NotebookLM notebook"""
    id: Optional[str] = None
    title: str = "Untitled Notebook"
    url: Optional[str] = None
    sources: List[Source] = None

    def __post_init__(self):
        if self.sources is None:
            self.sources = []


class NotebookManager:
    """
    Manages NotebookLM notebooks - create, add sources, delete.

    Usage:
        async with NotebookLMClient() as client:
            manager = NotebookManager(client)
            notebook = await manager.create_notebook("My Learning Module")
            await manager.add_text_source(notebook, "Content to learn...")
    """

    def __init__(self, client: NotebookLMClient):
        self.client = client

    async def create_notebook(self, title: str = "New Notebook") -> Notebook:
        """
        Create a new notebook.

        Args:
            title: Name for the notebook

        Returns:
            Notebook object with ID and URL
        """
        logger.info(f"Creating notebook: {title}")

        page = self.client.page

        # Click create/new notebook button
        try:
            # Try "Create" button first (main page)
            await page.click(Selectors.CREATE_NOTEBOOK_BUTTON, timeout=5000)
        except Exception:
            # Try "New notebook" if in notebook list view
            await page.click(Selectors.NEW_NOTEBOOK_BUTTON, timeout=5000)

        # Wait for notebook to be created and page to load
        await self.client.wait_for_loading()
        await asyncio.sleep(2)  # Extra wait for UI to stabilize

        # Set notebook title if there's an input field
        try:
            title_input = await page.query_selector(Selectors.NOTEBOOK_TITLE_INPUT)
            if title_input:
                await self.client.type_with_clear(Selectors.NOTEBOOK_TITLE_INPUT, title)
                await page.keyboard.press("Enter")
        except Exception as e:
            logger.warning(f"Could not set notebook title: {e}")

        # Extract notebook ID from URL
        url = await self.client.get_current_url()
        notebook_id = self._extract_notebook_id(url)

        notebook = Notebook(
            id=notebook_id,
            title=title,
            url=url
        )

        logger.info(f"Created notebook: {notebook.id}")
        return notebook

    async def add_source(self, notebook: Notebook, source: Source) -> bool:
        """
        Add a source to a notebook.

        Args:
            notebook: Target notebook
            source: Source to add

        Returns:
            True if successful
        """
        logger.info(f"Adding {source.type.value} source to notebook")

        page = self.client.page

        # Check if source dialog is already open (happens after notebook creation)
        paste_option = await page.query_selector(Selectors.PASTE_TEXT_OPTION)
        if not paste_option or not await paste_option.is_visible():
            # Click add source button only if dialog not already open
            try:
                await page.click(Selectors.ADD_SOURCE_BUTTON, timeout=5000)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug(f"Add source button click skipped: {e}")

        success = False

        if source.type == SourceType.FILE:
            success = await self._add_file_source(source.content)
        elif source.type == SourceType.TEXT:
            success = await self._add_text_source(source.content, source.title)
        elif source.type == SourceType.YOUTUBE:
            success = await self._add_url_source(source.content, is_youtube=True)
        elif source.type == SourceType.WEBSITE:
            success = await self._add_url_source(source.content, is_youtube=False)

        if success:
            notebook.sources.append(source)
            logger.info(f"Source added successfully")
        else:
            logger.error(f"Failed to add source")

        return success

    async def _add_file_source(self, file_path: str) -> bool:
        """Upload a file as source"""
        page = self.client.page

        try:
            # Click upload option
            await page.click(Selectors.UPLOAD_FILE_OPTION)

            # Handle file input
            file_input = await page.query_selector(Selectors.FILE_INPUT)
            if file_input:
                await file_input.set_input_files(file_path)

            # Wait for upload to complete
            await self.client.wait_for_loading(timeout=self.client.config.upload_timeout)
            return True

        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return False

    async def _add_text_source(self, text: str, title: Optional[str] = None) -> bool:
        """Paste text as source"""
        page = self.client.page

        try:
            # Click "Kopierter Text" chip (use mat-chip selector)
            chip = await page.query_selector('mat-chip:has-text("Kopierter Text")')
            if chip:
                await chip.click()
                logger.info("Clicked 'Kopierter Text' chip")
            else:
                # Fallback: text selector with force
                await page.click('text=Kopierter Text', force=True, timeout=10000)

            await asyncio.sleep(1)

            # Find the textarea in the dialog (it has no placeholder attribute)
            dialog = await page.query_selector('.cdk-overlay-container mat-dialog-container')
            if dialog:
                textarea = await dialog.query_selector('textarea')
                if textarea and await textarea.is_visible():
                    await textarea.fill(text)
                    logger.info(f"Filled textarea with {len(text)} chars")
                else:
                    logger.error("Textarea not found in dialog")
                    return False
            else:
                # Fallback: find textarea by general selector
                await page.fill('.cdk-overlay-container textarea', text)

            await asyncio.sleep(0.5)

            # Click insert/add button
            await page.click(Selectors.INSERT_BUTTON, timeout=10000)

            # Wait for processing (can take a while for large texts)
            logger.info("Waiting for text processing...")
            await asyncio.sleep(5)
            await self.client.wait_for_loading()

            # Check if source was added (dialog should close)
            await asyncio.sleep(2)
            logger.info("Text source added successfully")
            return True

        except Exception as e:
            logger.error(f"Text source failed: {e}")
            return False

    async def _add_url_source(self, url: str, is_youtube: bool = False) -> bool:
        """Add URL (YouTube or website) as source"""
        page = self.client.page

        try:
            # Click appropriate option
            if is_youtube:
                await page.click(Selectors.YOUTUBE_OPTION)
            else:
                await page.click(Selectors.WEBSITE_OPTION)

            await asyncio.sleep(0.5)

            # Enter URL
            await page.fill(Selectors.URL_INPUT, url)

            # Click insert/add button
            await page.click(Selectors.INSERT_BUTTON)

            # Wait for processing
            await self.client.wait_for_loading(timeout=self.client.config.upload_timeout)
            return True

        except Exception as e:
            logger.error(f"URL source failed: {e}")
            return False

    async def add_text_source(self, notebook: Notebook, text: str, title: Optional[str] = None) -> bool:
        """Convenience method to add text source"""
        source = Source(type=SourceType.TEXT, content=text, title=title)
        return await self.add_source(notebook, source)

    async def add_youtube_source(self, notebook: Notebook, youtube_url: str) -> bool:
        """Convenience method to add YouTube source"""
        source = Source(type=SourceType.YOUTUBE, content=youtube_url)
        return await self.add_source(notebook, source)

    async def add_website_source(self, notebook: Notebook, url: str) -> bool:
        """Convenience method to add website source"""
        source = Source(type=SourceType.WEBSITE, content=url)
        return await self.add_source(notebook, source)

    async def add_file_source(self, notebook: Notebook, file_path: Union[str, Path]) -> bool:
        """Convenience method to add file source"""
        source = Source(type=SourceType.FILE, content=str(file_path))
        return await self.add_source(notebook, source)

    async def delete_notebook(self, notebook: Notebook) -> bool:
        """
        Delete a notebook.

        Args:
            notebook: Notebook to delete

        Returns:
            True if successful
        """
        logger.info(f"Deleting notebook: {notebook.id}")

        page = self.client.page

        try:
            # Navigate to notebook if not already there
            if notebook.url and notebook.url not in await self.client.get_current_url():
                await page.goto(notebook.url)
                await self.client.wait_for_loading()

            # Find and click delete option (usually in menu)
            await page.click(Selectors.DELETE_NOTEBOOK)

            # Confirm deletion if there's a confirmation dialog
            try:
                await page.click('button:has-text("Delete")', timeout=5000)
            except Exception:
                pass  # No confirmation needed

            logger.info(f"Notebook deleted: {notebook.id}")
            return True

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    async def list_notebooks(self) -> List[Notebook]:
        """
        List all notebooks.

        Returns:
            List of Notebook objects
        """
        logger.info("Listing notebooks...")

        page = self.client.page

        # Navigate to main page
        await page.goto(self.client.config.base_url)
        await self.client.wait_for_loading()

        notebooks = []

        try:
            # Find all notebook items
            items = await page.query_selector_all(Selectors.NOTEBOOK_ITEM)

            for item in items:
                title_elem = await item.query_selector("h3, [data-testid='notebook-title']")
                title = await title_elem.text_content() if title_elem else "Untitled"

                link = await item.query_selector("a")
                url = await link.get_attribute("href") if link else None

                notebook = Notebook(
                    id=self._extract_notebook_id(url) if url else None,
                    title=title.strip(),
                    url=url
                )
                notebooks.append(notebook)

        except Exception as e:
            logger.error(f"Failed to list notebooks: {e}")

        logger.info(f"Found {len(notebooks)} notebooks")
        return notebooks

    def _extract_notebook_id(self, url: Optional[str]) -> Optional[str]:
        """Extract notebook ID from URL"""
        if not url:
            return None
        # URL format: https://notebooklm.google.com/notebook/NOTEBOOK_ID
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else None
