"""
NotebookLM Playwright Client - Browser automation core

Handles browser lifecycle, authentication, and base navigation.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from .config import NotebookLMConfig, Selectors

logger = logging.getLogger(__name__)


class NotebookLMClient:
    """
    Playwright-based client for NotebookLM browser automation.

    Usage:
        async with NotebookLMClient() as client:
            await client.ensure_authenticated()
            # ... use client

    Supports connecting to existing Chrome via CDP:
        config = NotebookLMConfig(cdp_url="http://localhost:9222")
        async with NotebookLMClient(config) as client:
            ...
    """

    def __init__(self, config: Optional[NotebookLMConfig] = None):
        self.config = config or NotebookLMConfig()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._connected_via_cdp: bool = False

    async def __aenter__(self) -> "NotebookLMClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self) -> None:
        """Initialize browser and navigate to NotebookLM"""
        logger.info("Starting NotebookLM client...")

        self._playwright = await async_playwright().start()

        # Option 1: Connect to existing Chrome via CDP (preferred for pre-authenticated sessions)
        if self.config.cdp_url:
            logger.info(f"Connecting to existing Chrome via CDP: {self.config.cdp_url}")
            try:
                self._browser = await self._playwright.chromium.connect_over_cdp(self.config.cdp_url)
                self._connected_via_cdp = True

                # Get the default context and page
                contexts = self._browser.contexts
                if contexts:
                    self._context = contexts[0]
                    if self._context.pages:
                        # Use existing page or create new one
                        self._page = await self._context.new_page()
                    else:
                        self._page = await self._context.new_page()
                else:
                    self._context = await self._browser.new_context()
                    self._page = await self._context.new_page()

                logger.info("Connected to existing Chrome browser")
            except Exception as e:
                logger.error(f"Failed to connect via CDP: {e}")
                logger.info("Falling back to launching new browser...")
                self._connected_via_cdp = False
                await self._launch_new_browser()
        else:
            await self._launch_new_browser()

        # Set default timeout
        self._page.set_default_timeout(self.config.default_timeout)

        # Navigate to NotebookLM
        await self._page.goto(self.config.base_url)
        logger.info(f"Navigated to {self.config.base_url}")

    async def _launch_new_browser(self) -> None:
        """Launch a new browser instance"""
        # Launch browser with persistent context for login persistence
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
        )

        # Use persistent context if user_data_dir exists
        if self.config.user_data_dir and self.config.user_data_dir.exists():
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.config.user_data_dir / self.config.profile_name),
                headless=self.config.headless,
                slow_mo=self.config.slow_mo,
            )
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        else:
            self._context = await self._browser.new_context()
            self._page = await self._context.new_page()

    async def close(self) -> None:
        """Clean up browser resources"""
        # Only close the page we created, not the entire browser (for CDP connections)
        if self._connected_via_cdp:
            if self._page:
                await self._page.close()
            logger.info("NotebookLM client closed (CDP page only, browser kept alive)")
        else:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            logger.info("NotebookLM client closed")

        if self._playwright:
            await self._playwright.stop()

    @property
    def page(self) -> Page:
        """Get the current page"""
        if not self._page:
            raise RuntimeError("Client not started. Use 'async with NotebookLMClient()' or call start()")
        return self._page

    async def ensure_authenticated(self) -> bool:
        """
        Check if user is authenticated, prompt for manual login if not.

        Returns:
            True if authenticated, False if login was cancelled
        """
        # Check if we're on the main NotebookLM page (authenticated)
        try:
            # Wait for either the create button (authenticated) or sign-in button
            await self.page.wait_for_selector(
                f"{Selectors.CREATE_NOTEBOOK_BUTTON}, {Selectors.SIGN_IN_BUTTON}",
                timeout=10000
            )

            # Check which state we're in
            create_btn = await self.page.query_selector(Selectors.CREATE_NOTEBOOK_BUTTON)
            if create_btn:
                logger.info("Already authenticated")
                return True

            # Need to sign in
            logger.warning("Not authenticated. Please sign in manually in the browser window.")
            logger.info("Waiting for authentication (timeout: 2 minutes)...")

            # Wait for user to complete sign-in
            await self.page.wait_for_selector(
                Selectors.CREATE_NOTEBOOK_BUTTON,
                timeout=120000  # 2 minutes for manual login
            )
            logger.info("Authentication successful")
            return True

        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return False

    async def wait_for_loading(self, timeout: Optional[int] = None) -> None:
        """Wait for any loading indicators to disappear"""
        timeout = timeout or self.config.default_timeout
        try:
            # Wait for loading spinner to disappear
            spinner = await self.page.query_selector(Selectors.LOADING_SPINNER)
            if spinner:
                await spinner.wait_for_element_state("hidden", timeout=timeout)

            # Also check for progress bar
            progress = await self.page.query_selector(Selectors.PROGRESS_BAR)
            if progress:
                await progress.wait_for_element_state("hidden", timeout=timeout)

        except Exception:
            pass  # Loading indicators may not always be present

    async def click_with_retry(
        self,
        selector: str,
        retries: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> bool:
        """Click an element with retry logic"""
        retries = retries or self.config.max_retries
        timeout = timeout or self.config.default_timeout

        for attempt in range(retries):
            try:
                await self.page.click(selector, timeout=timeout)
                return True
            except Exception as e:
                logger.warning(f"Click attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)

        return False

    async def type_with_clear(self, selector: str, text: str) -> None:
        """Clear an input field and type new text"""
        await self.page.fill(selector, "")
        await self.page.fill(selector, text)

    async def screenshot(self, name: str) -> Path:
        """Take a screenshot for debugging"""
        path = self.config.output_dir / f"{name}.png"
        await self.page.screenshot(path=str(path))
        logger.debug(f"Screenshot saved: {path}")
        return path

    async def get_current_url(self) -> str:
        """Get current page URL"""
        return self.page.url

    async def check_for_error(self) -> Optional[str]:
        """Check if there's an error message on the page"""
        error_elem = await self.page.query_selector(Selectors.ERROR_MESSAGE)
        if error_elem:
            return await error_elem.text_content()
        return None
