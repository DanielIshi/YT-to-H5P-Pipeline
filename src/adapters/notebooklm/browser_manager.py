
import asyncio
from playwright.async_api import async_playwright, Browser, Page

class BrowserManager:
    """
    Manages a Playwright browser instance, ensuring it is properly launched and closed.
    This class is designed to be used as a singleton to provide a single browser instance.
    """
    _browser: Browser = None
    _playwright = None

    @classmethod
    async def get_browser(cls) -> Browser:
        """
        Launches and returns a Playwright browser instance. If a browser is already running,
        it returns the existing instance.
        """
        if cls._browser is None:
            cls._playwright = await async_playwright().start()
            cls._browser = await cls._playwright.chromium.launch(headless=False)
        return cls._browser

    @classmethod
    async def close_browser(cls):
        """
        Closes the browser and the Playwright instance if they are running.
        """
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None

    @classmethod
    async def new_page(cls) -> Page:
        """
        Creates a new page in the browser.
        """
        browser = await cls.get_browser()
        return await browser.new_page()

async def main():
    # Example of how to use the BrowserManager
    page = await BrowserManager.new_page()
    await page.goto("https://www.google.com")
    print(await page.title())
    await BrowserManager.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
