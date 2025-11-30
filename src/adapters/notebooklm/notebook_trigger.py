"""
NotebookLM Trigger - Triggers ALL artifact generations for a notebook

Opens an existing notebook and triggers generation of all 8 artifact types:
- Audio, Video, Mindmap, Berichte
- Karteikarten, Quiz, Infografik, Präsentation

Usage:
    python -m src.adapters.notebooklm.notebook_trigger \
        --url "https://notebooklm.google.com/notebook/ABC123"
"""

import asyncio
import argparse
import json
import logging
from dataclasses import dataclass, asdict
from typing import List

from .client import NotebookLMClient
from .config import NotebookLMConfig, Selectors

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TriggerResult:
    """Result of notebook trigger operation"""
    notebook_url: str
    triggered: List[str]
    errors: List[str]


class NotebookTrigger:
    """
    Triggers all artifact generations for a NotebookLM notebook.

    Does NOT wait for completion - use NotebookHarvester to download results.
    """

    # All artifact types with their selectors (from config.py)
    ARTIFACTS = [
        ('Audio', Selectors.STUDIO_AUDIO),
        ('Video', Selectors.STUDIO_VIDEO),
        ('Mindmap', Selectors.STUDIO_MINDMAP),
        ('Berichte', Selectors.STUDIO_BERICHTE),
        ('Karteikarten', Selectors.STUDIO_KARTEIKARTEN),
        ('Quiz', Selectors.STUDIO_QUIZ),
        ('Infografik', Selectors.STUDIO_INFOGRAFIK),
        ('Präsentation', Selectors.STUDIO_PRAESENTATION),
    ]

    def __init__(self, client: NotebookLMClient):
        self.client = client

    async def trigger_all(self, notebook_url: str) -> TriggerResult:
        """
        Trigger generation of all artifact types for a notebook.

        Args:
            notebook_url: URL of the existing notebook

        Returns:
            TriggerResult with list of triggered artifacts and any errors
        """
        result = TriggerResult(
            notebook_url=notebook_url,
            triggered=[],
            errors=[]
        )

        page = self.client.page

        # Navigate to notebook
        logger.info(f"Opening notebook: {notebook_url}")
        await page.goto(notebook_url)
        await asyncio.sleep(5)

        # Trigger each artifact type
        for name, selector in self.ARTIFACTS:
            try:
                logger.info(f"Triggering {name}...")

                # Close any open dialog first
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)

                # Click the artifact button
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(1)

                    # Some artifacts open a dialog - click "Generieren" if present
                    try:
                        await page.click('button:has-text("Generieren")', timeout=2000)
                        logger.info(f"  ✓ {name} - clicked Generieren")
                    except:
                        logger.info(f"  ✓ {name} - triggered directly")

                    result.triggered.append(name)
                    await asyncio.sleep(1)

                    # Close any dialog that might still be open
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.5)
                else:
                    result.errors.append(f"{name}: Button not visible")
                    logger.warning(f"  ✗ {name}: Button not visible")

            except Exception as e:
                error_msg = f"{name}: {str(e)[:80]}"
                result.errors.append(error_msg)
                logger.error(f"  ✗ {error_msg}")

        logger.info(f"Triggered {len(result.triggered)}/{len(self.ARTIFACTS)} artifacts")
        return result


async def main():
    parser = argparse.ArgumentParser(description="NotebookLM Trigger - Start all artifact generations")
    parser.add_argument("--url", required=True, help="Notebook URL")
    parser.add_argument("--cdp-port", type=int, default=9223, help="Chrome CDP port")

    args = parser.parse_args()

    config = NotebookLMConfig(cdp_url=f"http://localhost:{args.cdp_port}")

    async with NotebookLMClient(config) as client:
        trigger = NotebookTrigger(client)
        result = await trigger.trigger_all(args.url)

    # Output JSON
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
