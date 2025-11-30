"""
E2E Test for NotebookLM Audio Overview - uses EXISTING notebook

Run: pytest tests/e2e/test_notebooklm_audio.py -v -s
"""

import asyncio
import pytest
import subprocess
import socket
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.adapters.notebooklm.client import NotebookLMClient
from src.adapters.notebooklm.config import NotebookLMConfig
from src.adapters.notebooklm.audio_downloader import AudioDownloader


# Chrome config
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_PROFILE = r"C:\demo_profiles\youtube_demos"
CDP_PORT = 9223

# EXISTING notebook with content
NOTEBOOK_URL = "https://notebooklm.google.com/notebook/fffb53c2-0280-45f3-a32b-f07c9cbaeddd"
NOTEBOOK_TITLE = "Corporate LLMs"


def is_chrome_running(port: int = CDP_PORT) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("localhost", port))
            return True
    except:
        return False


def start_chrome():
    if is_chrome_running():
        print(f"✅ Chrome running on port {CDP_PORT}")
        return True

    print(f"🚀 Starting Chrome...")
    subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={CHROME_PROFILE}",
        "--remote-allow-origins=*"
    ])

    for _ in range(10):
        time.sleep(1)
        if is_chrome_running():
            print(f"✅ Chrome started")
            return True
    return False


@pytest.fixture(scope="module", autouse=True)
def ensure_chrome():
    if not start_chrome():
        pytest.skip("Chrome not available")
    yield


@pytest.fixture
def config():
    return NotebookLMConfig(
        cdp_url=f"http://localhost:{CDP_PORT}",
        headless=False,
        audio_generation_timeout=300000  # 5 min
    )


class TestAudioDownload:
    """Test audio download from EXISTING notebook"""

    @pytest.mark.asyncio
    async def test_generate_audio(self, config):
        """Generate and download audio from existing notebook"""
        output_dir = Path(__file__).parent.parent / "output" / "notebooklm" / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{NOTEBOOK_TITLE}_audio.mp3"

        async with NotebookLMClient(config) as client:
            downloader = AudioDownloader(client)

            audio = await downloader.generate_and_download(
                notebook_url=NOTEBOOK_URL,
                output_path=output_path,
                notebook_title=NOTEBOOK_TITLE
            )

            print(f"\nResult: {audio.status}")
            if audio.file_path:
                print(f"File: {audio.file_path}")
                print(f"Size: {audio.file_path.stat().st_size / 1024:.1f} KB")

            assert audio.status == "ready", f"Failed: {audio.status}"
            assert audio.file_path and audio.file_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
