"""
NotebookLM Content Extractor - Extract generated content (FAQ, Study Guide, etc.)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .client import NotebookLMClient
from .notebook_manager import Notebook
from .config import Selectors

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of content that can be generated from NotebookLM"""
    FAQ = "faq"
    STUDY_GUIDE = "study_guide"
    BRIEFING_DOC = "briefing_doc"
    TIMELINE = "timeline"
    TABLE_OF_CONTENTS = "toc"


@dataclass
class GeneratedContent:
    """Container for extracted content"""
    type: ContentType
    title: str
    content: str
    html_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExtractedData:
    """All extracted data from a notebook"""
    notebook_id: str
    notebook_title: str
    faq: Optional[GeneratedContent] = None
    study_guide: Optional[GeneratedContent] = None
    briefing_doc: Optional[GeneratedContent] = None
    timeline: Optional[GeneratedContent] = None
    mindmap_data: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    key_topics: List[str] = field(default_factory=list)


class ContentExtractor:
    """
    Extracts generated content from NotebookLM notebooks.

    Usage:
        async with NotebookLMClient() as client:
            extractor = ContentExtractor(client)
            content = await extractor.extract_faq(notebook)
    """

    def __init__(self, client: NotebookLMClient):
        self.client = client

    async def extract_all(self, notebook: Notebook) -> ExtractedData:
        """
        Extract all available content from a notebook.

        Args:
            notebook: Target notebook

        Returns:
            ExtractedData with all generated content
        """
        logger.info(f"Extracting all content from notebook: {notebook.id}")

        data = ExtractedData(
            notebook_id=notebook.id or "",
            notebook_title=notebook.title
        )

        # Navigate to notebook if needed
        await self._ensure_notebook_open(notebook)

        # Extract each content type
        data.faq = await self.extract_faq(notebook)
        data.study_guide = await self.extract_study_guide(notebook)
        data.briefing_doc = await self.extract_briefing_doc(notebook)
        data.timeline = await self.extract_timeline(notebook)

        # Extract summary from chat/overview
        data.summary = await self._extract_summary()
        data.key_topics = await self._extract_key_topics()

        logger.info(f"Extraction complete for notebook: {notebook.id}")
        return data

    async def extract_faq(self, notebook: Notebook) -> Optional[GeneratedContent]:
        """
        Generate and extract FAQ content.

        Args:
            notebook: Target notebook

        Returns:
            GeneratedContent with FAQ
        """
        return await self._extract_content_type(notebook, ContentType.FAQ, Selectors.FAQ_TAB)

    async def extract_study_guide(self, notebook: Notebook) -> Optional[GeneratedContent]:
        """
        Generate and extract Study Guide content.

        Args:
            notebook: Target notebook

        Returns:
            GeneratedContent with Study Guide
        """
        return await self._extract_content_type(notebook, ContentType.STUDY_GUIDE, Selectors.STUDY_GUIDE_TAB)

    async def extract_briefing_doc(self, notebook: Notebook) -> Optional[GeneratedContent]:
        """
        Generate and extract Briefing Document.

        Args:
            notebook: Target notebook

        Returns:
            GeneratedContent with Briefing Doc
        """
        return await self._extract_content_type(notebook, ContentType.BRIEFING_DOC, Selectors.BRIEFING_TAB)

    async def extract_timeline(self, notebook: Notebook) -> Optional[GeneratedContent]:
        """
        Generate and extract Timeline.

        Args:
            notebook: Target notebook

        Returns:
            GeneratedContent with Timeline
        """
        return await self._extract_content_type(notebook, ContentType.TIMELINE, Selectors.TIMELINE_TAB)

    async def _extract_content_type(
        self,
        notebook: Notebook,
        content_type: ContentType,
        tab_selector: str
    ) -> Optional[GeneratedContent]:
        """Generic content extraction for studio panel tabs"""
        logger.info(f"Extracting {content_type.value} from notebook")

        page = self.client.page

        try:
            await self._ensure_notebook_open(notebook)

            # Open Studio panel if not visible
            studio_panel = await page.query_selector(Selectors.STUDIO_PANEL)
            if not studio_panel or not await studio_panel.is_visible():
                # Try to open studio panel (might be a button or automatic)
                pass

            # Click the content type tab
            await page.click(tab_selector, timeout=10000)
            await asyncio.sleep(1)

            # Wait for content to generate (may take time)
            await self._wait_for_generation()

            # Extract the generated content
            content_elem = await page.query_selector(Selectors.GENERATED_CONTENT)
            if not content_elem:
                # Try alternative selectors
                content_elem = await page.query_selector('[class*="content"], [class*="output"]')

            if content_elem:
                text_content = await content_elem.text_content()
                html_content = await content_elem.inner_html()

                return GeneratedContent(
                    type=content_type,
                    title=f"{notebook.title} - {content_type.value}",
                    content=text_content.strip() if text_content else "",
                    html_content=html_content
                )

            logger.warning(f"No content found for {content_type.value}")
            return None

        except Exception as e:
            logger.error(f"Failed to extract {content_type.value}: {e}")
            return None

    async def _ensure_notebook_open(self, notebook: Notebook) -> None:
        """Navigate to notebook if not already open"""
        current_url = await self.client.get_current_url()
        if notebook.url and notebook.url not in current_url:
            await self.client.page.goto(notebook.url)
            await self.client.wait_for_loading()

    async def _wait_for_generation(self, timeout: int = 60000) -> None:
        """Wait for content generation to complete"""
        page = self.client.page

        try:
            # Wait for loading to finish
            await self.client.wait_for_loading(timeout=timeout)

            # Additional wait for content to render
            await asyncio.sleep(2)

            # Check for error
            error = await self.client.check_for_error()
            if error:
                logger.warning(f"Generation warning: {error}")

        except Exception as e:
            logger.warning(f"Generation wait issue: {e}")

    async def _extract_summary(self) -> Optional[str]:
        """Extract summary from notebook overview"""
        page = self.client.page

        try:
            # Look for summary section
            summary_selectors = [
                '[data-testid="summary"]',
                '[class*="summary"]',
                '.overview-content',
            ]

            for selector in summary_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.text_content()
                    if text:
                        return text.strip()

        except Exception as e:
            logger.debug(f"Summary extraction: {e}")

        return None

    async def _extract_key_topics(self) -> List[str]:
        """Extract key topics/tags from notebook"""
        page = self.client.page
        topics = []

        try:
            # Look for topic tags
            topic_selectors = [
                '[data-testid="topic-tag"]',
                '[class*="topic"]',
                '[class*="tag"]',
            ]

            for selector in topic_selectors:
                elems = await page.query_selector_all(selector)
                for elem in elems:
                    text = await elem.text_content()
                    if text:
                        topics.append(text.strip())

        except Exception as e:
            logger.debug(f"Topic extraction: {e}")

        return list(set(topics))  # Remove duplicates

    async def copy_to_clipboard(self, content_type: ContentType) -> Optional[str]:
        """
        Use the copy button to get content (as fallback).

        Args:
            content_type: Type of content to copy

        Returns:
            Copied text content
        """
        page = self.client.page

        try:
            # Click copy button
            await page.click(Selectors.COPY_BUTTON)
            await asyncio.sleep(0.5)

            # Get clipboard content (requires browser permissions)
            content = await page.evaluate("navigator.clipboard.readText()")
            return content

        except Exception as e:
            logger.warning(f"Clipboard copy failed: {e}")
            return None

    async def export_to_markdown(self, data: ExtractedData) -> str:
        """
        Export extracted data to Markdown format.

        Args:
            data: Extracted data to export

        Returns:
            Markdown formatted string
        """
        md_parts = [
            f"# {data.notebook_title}",
            f"\n*Generated: {datetime.now().isoformat()}*\n",
        ]

        if data.summary:
            md_parts.append(f"## Summary\n\n{data.summary}\n")

        if data.key_topics:
            md_parts.append(f"## Key Topics\n\n" + ", ".join(data.key_topics) + "\n")

        if data.faq:
            md_parts.append(f"## FAQ\n\n{data.faq.content}\n")

        if data.study_guide:
            md_parts.append(f"## Study Guide\n\n{data.study_guide.content}\n")

        if data.briefing_doc:
            md_parts.append(f"## Briefing Document\n\n{data.briefing_doc.content}\n")

        if data.timeline:
            md_parts.append(f"## Timeline\n\n{data.timeline.content}\n")

        return "\n".join(md_parts)
