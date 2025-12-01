"""
E2E Test: Mindmap Animation synchronized with Audio

This test records a mindmap animation where nodes expand ONLY when
the audio mentions them - creating a "follow along" experience.

Requirements:
- Chrome running with --remote-debugging-port=9223
- NotebookLM notebook with existing mindmap
- Audio file from NotebookLM (or will be downloaded)

Usage:
    python -m pytest tests/e2e/test_mindmap_audio_sync.py -v -s
"""

import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime

import pytest
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
NOTEBOOK_URL = "https://notebooklm.google.com/notebook/08fc4557-e64c-4fc1-9bca-3782338426e2"
CDP_PORT = 9223
OUTPUT_DIR = Path("tests/output/recordings")
# Use Jobmesse-specific audio directory
AUDIO_DIR = Path("tests/output/notebooklm/jobmesse/audio")


class AudioSyncedMindmapRecorder:
    """
    Records mindmap animation synchronized with audio narration.

    Key principle: Nodes expand ONLY when audio mentions their content,
    NOT at the beginning. This creates a "follow along" experience.
    """

    def __init__(self, page, output_dir: Path):
        self.page = page
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Animation state
        self._expanded_nodes = set()
        self._all_nodes = []

    async def extract_mindmap_structure(self) -> dict:
        """Extract mindmap nodes from SVG."""
        logger.info("Extracting mindmap structure...")

        # Wait for mindmap to be visible
        await self.page.wait_for_selector('svg g.node', timeout=10000)
        await asyncio.sleep(1)

        # Extract all nodes using JavaScript
        nodes_data = await self.page.evaluate('''
            () => {
                const nodes = [];
                const nodeGroups = document.querySelectorAll('g.node');

                nodeGroups.forEach((group, index) => {
                    const textEl = group.querySelector('text.node-name');
                    const transform = group.getAttribute('transform') || '';
                    const expandSymbol = group.querySelector('text.expand-symbol');

                    // Parse transform to get position
                    const match = transform.match(/translate\\(([^,]+),\\s*([^)]+)\\)/);
                    const x = match ? parseFloat(match[1]) : 0;
                    const y = match ? parseFloat(match[2]) : 0;

                    // Check if node is expandable (has children)
                    const isExpandable = expandSymbol !== null;
                    const isExpanded = expandSymbol && expandSymbol.textContent.includes('<');

                    nodes.push({
                        id: `node_${index}`,
                        text: textEl ? textEl.textContent.trim() : '',
                        x: x,
                        y: y,
                        isExpandable: isExpandable,
                        isExpanded: isExpanded
                    });
                });

                return nodes;
            }
        ''')

        self._all_nodes = nodes_data
        logger.info(f"Found {len(nodes_data)} nodes")

        # Log node hierarchy
        for node in sorted(nodes_data, key=lambda n: (n['x'], n['y'])):
            level = 0 if node['x'] < 100 else (1 if node['x'] < 500 else 2)
            prefix = "  " * level
            expand_state = "[+]" if node['isExpandable'] and not node['isExpanded'] else "[-]" if node['isExpanded'] else ""
            logger.info(f"{prefix}{expand_state} {node['text'][:50]}")

        return {"nodes": nodes_data}

    async def collapse_all_nodes(self):
        """Collapse all nodes to initial state (only root visible)."""
        logger.info("Collapsing all nodes to initial state...")

        collapse_js = """
        () => {
            let totalCollapsed = 0;

            // Repeat until no more nodes to collapse
            for (let iter = 0; iter < 10; iter++) {
                const expandSymbols = document.querySelectorAll('text.expand-symbol');
                let collapsedThisRound = 0;

                // Collapse from deepest (rightmost) first
                const symbolsArray = Array.from(expandSymbols).reverse();

                symbolsArray.forEach(symbol => {
                    if (symbol.textContent && symbol.textContent.includes('<')) {
                        const nodeGroup = symbol.closest('g.node');
                        if (nodeGroup) {
                            const circle = nodeGroup.querySelector('circle');
                            if (circle) {
                                circle.dispatchEvent(new MouseEvent('click', {
                                    bubbles: true, cancelable: true, view: window
                                }));
                                collapsedThisRound++;
                            }
                        }
                    }
                });

                totalCollapsed += collapsedThisRound;
                if (collapsedThisRound === 0) break;
            }

            return totalCollapsed;
        }
        """

        collapsed = await self.page.evaluate(collapse_js)
        logger.info(f"Collapsed {collapsed} nodes")
        await asyncio.sleep(1)

        self._expanded_nodes.clear()

    async def expand_node_by_text(self, node_text: str) -> bool:
        """
        Expand a specific node by its text content.

        Args:
            node_text: Text to match (partial match)

        Returns:
            True if node was expanded
        """
        # Escape special characters for JavaScript
        safe_text = node_text.replace("'", "\\'").replace('"', '\\"')[:30]

        expand_js = f'''
            () => {{
                const nodes = document.querySelectorAll('g.node');
                for (const node of nodes) {{
                    const textEl = node.querySelector('text.node-name');
                    if (textEl && textEl.textContent.includes("{safe_text}")) {{
                        const expandSymbol = node.querySelector('text.expand-symbol');
                        if (expandSymbol && expandSymbol.textContent.includes('>')) {{
                            const circle = node.querySelector('circle');
                            if (circle) {{
                                // Visual highlight before click
                                const rect = node.querySelector('rect');
                                if (rect) {{
                                    rect.style.stroke = '#FFD700';
                                    rect.style.strokeWidth = '3px';
                                }}

                                circle.dispatchEvent(new MouseEvent('click', {{
                                    bubbles: true, cancelable: true, view: window
                                }}));
                                return textEl.textContent;
                            }}
                        }}
                    }}
                }}
                return null;
            }}
        '''

        result = await self.page.evaluate(expand_js)
        if result:
            logger.info(f"Expanded node: {result[:50]}")
            self._expanded_nodes.add(result)
            await asyncio.sleep(0.8)  # Wait for expand animation
            return True
        return False

    async def highlight_node_by_text(self, node_text: str):
        """Highlight a node without expanding it."""
        safe_text = node_text.replace("'", "\\'").replace('"', '\\"')[:30]

        highlight_js = f'''
            () => {{
                // Remove previous highlights
                document.querySelectorAll('g.node rect').forEach(rect => {{
                    rect.style.stroke = '';
                    rect.style.strokeWidth = '';
                }});

                const nodes = document.querySelectorAll('g.node');
                for (const node of nodes) {{
                    const textEl = node.querySelector('text.node-name');
                    if (textEl && textEl.textContent.includes("{safe_text}")) {{
                        const rect = node.querySelector('rect');
                        if (rect) {{
                            rect.style.stroke = '#FFD700';
                            rect.style.strokeWidth = '3px';
                            return true;
                        }}
                    }}
                }}
                return false;
            }}
        '''
        await self.page.evaluate(highlight_js)


class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper with word-level timestamps."""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                import whisper
                logger.info(f"Loading Whisper model: {self.model_name}")
                self._model = whisper.load_model(self.model_name)
            except ImportError:
                raise ImportError("Whisper not installed. Run: pip install openai-whisper")

    def transcribe(self, audio_path: Path) -> list:
        """
        Transcribe audio file to segments with timestamps.

        Returns:
            List of segments: [{"start": float, "end": float, "text": str}, ...]
        """
        self._load_model()

        logger.info(f"Transcribing: {audio_path}")
        result = self._model.transcribe(
            str(audio_path),
            word_timestamps=True,
            language="de"  # German
        )

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "text": seg.get("text", "").strip()
            })

        logger.info(f"Transcribed {len(segments)} segments, total duration: {segments[-1]['end']:.1f}s")
        return segments


def match_segment_to_node(segment_text: str, nodes: list) -> str | None:
    """
    Match a transcript segment to the most relevant mindmap node.

    Uses keyword matching to find which node the audio is talking about.
    Enhanced with synonyms and partial matching for German content.
    """
    segment_lower = segment_text.lower()

    # German stop words to ignore
    stop_words = {
        'der', 'die', 'das', 'und', 'in', 'zu', 'den', 'für', 'mit', 'von',
        'ist', 'sind', 'ein', 'eine', 'als', 'auf', 'auch', 'bei', 'oder',
        'wie', 'was', 'wir', 'sie', 'es', 'kann', 'können', 'werden', 'haben',
        'hat', 'wird', 'dem', 'nicht', 'im', 'an', 'so', 'noch', 'dann',
        'aber', 'wenn', 'denn', 'weil', 'also', 'nur', 'schon', 'mal', 'ja'
    }

    # Keyword synonyms/variations for better matching
    keyword_synonyms = {
        'zeitplan': ['zeit', 'termin', 'datum', 'tag', 'uhrzeit', 'ablauf', 'schedule'],
        'abbau': ['abbauen', 'abreise', 'ende', 'schluss', 'rückbau'],
        'aufbau': ['aufbauen', 'anreise', 'start', 'beginn', 'vorbereitung'],
        'technik': ['strom', 'wlan', 'internet', 'anschluss', 'versorgung', 'technisch'],
        'parken': ['parkplatz', 'auto', 'fahrzeug', 'anfahrt', 'parkhaus', 'zoo'],
        'logistik': ['lieferung', 'anlieferung', 'transport', 'ware', 'standnummer'],
        'catering': ['essen', 'trinken', 'verpflegung', 'speisen', 'getränke'],
        'sicherheit': ['sicher', 'brandschutz', 'notfall', 'feuer', 'vorschrift'],
        'service': ['hilfe', 'unterstützung', 'betreuung', 'team'],
        'kontakt': ['ansprechpartner', 'telefon', 'email', 'frage', 'erreich'],
        'messe': ['jobmesse', 'veranstaltung', 'aussteller', 'stand', 'leipzig'],
    }

    best_match = None
    best_score = 0

    for node in nodes:
        node_text = node['text'].lower()
        node_words = set(node_text.split()) - stop_words
        segment_words = set(segment_lower.split()) - stop_words

        if not node_words:
            continue

        # Direct word matching
        matches = node_words & segment_words
        score = len(matches) / len(node_words) if node_words else 0

        # Bonus for exact substring match
        if node_text[:15] in segment_lower:
            score += 0.6

        # Check synonym matches
        for node_word in node_words:
            synonyms = keyword_synonyms.get(node_word, [])
            for synonym in synonyms:
                if synonym in segment_lower:
                    score += 0.25
                    break

        # Partial word matching (stems)
        for node_word in node_words:
            if len(node_word) > 4:
                stem = node_word[:5]
                if stem in segment_lower:
                    score += 0.15

        if score > best_score and score >= 0.25:
            best_score = score
            best_match = node['text']

    return best_match


def create_audio_synced_timeline(segments: list, nodes: list) -> list:
    """
    Create animation timeline from transcript segments.

    Each timeline entry specifies WHEN to expand WHICH node,
    based on what the audio is saying at that moment.

    Returns:
        List of timeline entries: [{"time": float, "action": "expand", "node": str}, ...]
    """
    timeline = []
    expanded_nodes = set()

    for segment in segments:
        matched_node = match_segment_to_node(segment['text'], nodes)

        if matched_node and matched_node not in expanded_nodes:
            timeline.append({
                "time": segment['start'],
                "action": "expand",
                "node": matched_node,
                "trigger_text": segment['text'][:50]
            })
            expanded_nodes.add(matched_node)
            logger.info(f"Timeline: {segment['start']:.1f}s -> expand '{matched_node[:40]}' (trigger: {segment['text'][:30]}...)")

    logger.info(f"Created timeline with {len(timeline)} expansion events")
    return timeline


@pytest.mark.asyncio
async def test_mindmap_audio_sync_recording():
    """
    Test: Record mindmap animation synchronized with audio.

    This is the main E2E test that:
    1. Connects to existing Chrome with NotebookLM
    2. Opens the mindmap
    3. Transcribes the audio (or loads cached transcript)
    4. Creates audio-synced timeline
    5. Records animation with proper timing
    """
    logger.info("=" * 60)
    logger.info("Mindmap Audio-Sync Recording Test")
    logger.info("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as p:
        # Connect to existing Chrome
        logger.info(f"Connecting to Chrome on CDP port {CDP_PORT}...")
        browser = await p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")

        # Get existing context and page
        contexts = browser.contexts
        if not contexts:
            pytest.fail("No browser contexts found. Open Chrome with the notebook first.")

        context = contexts[0]
        pages = context.pages

        # Find or create page with notebook
        page = None
        for p_item in pages:
            if "notebooklm" in p_item.url:
                page = p_item
                break

        if not page:
            page = pages[0] if pages else await context.new_page()
            await page.goto(NOTEBOOK_URL)
            await asyncio.sleep(5)

        logger.info(f"Using page: {page.url}")

        # Take initial screenshot
        await page.screenshot(path=str(OUTPUT_DIR / f"01_initial_{timestamp}.png"))

        # Initialize recorder
        recorder = AudioSyncedMindmapRecorder(page, OUTPUT_DIR)

        # Step 1: Open mindmap if not already visible
        logger.info("Step 1: Opening mindmap...")

        # Check if mindmap is already visible
        mindmap_svg = await page.query_selector('svg g.node')
        if not mindmap_svg:
            # Look for EXISTING mindmap cards in Studio panel (not the generate button)
            # These have 'quelle' text and are NOT 'wird erstellt'
            buttons = await page.query_selector_all('button')
            mindmap_opened = False

            for btn in buttons:
                text = await btn.text_content()
                if not text:
                    continue

                text_lower = text.lower()

                # Skip mindmaps that are still being generated
                if 'wird erstellt' in text_lower or 'generating' in text_lower:
                    continue

                # Look for completed mindmap with flowchart icon and 'quelle' count
                # Also match specific keywords like 'jobmesse', 'ausstellerleitfaden', etc.
                has_flowchart = 'flowchart' in text_lower
                has_quelle = 'quelle' in text_lower
                has_keyword = any(kw in text_lower for kw in ['jobmesse', 'aussteller', 'organis', 'hinweise'])

                if has_flowchart and has_quelle and has_keyword:
                    await btn.click()
                    logger.info(f"Clicked existing mindmap: {text[:60]}")
                    mindmap_opened = True
                    await asyncio.sleep(3)
                    break

            if not mindmap_opened:
                # Fallback: Click any mindmap with flowchart icon
                for btn in buttons:
                    text = await btn.text_content()
                    if text and 'flowchart' in text.lower() and 'quelle' in text.lower():
                        await btn.click()
                        logger.info(f"Clicked mindmap (fallback): {text[:60]}")
                        await asyncio.sleep(3)
                        break

        await page.screenshot(path=str(OUTPUT_DIR / f"02_mindmap_open_{timestamp}.png"))

        # Step 2: Extract mindmap structure
        logger.info("Step 2: Extracting mindmap structure...")
        mindmap_data = await recorder.extract_mindmap_structure()

        # Save structure for reference
        structure_path = OUTPUT_DIR / f"mindmap_structure_{timestamp}.json"
        structure_path.write_text(json.dumps(mindmap_data, indent=2, ensure_ascii=False))
        logger.info(f"Structure saved: {structure_path}")

        # Step 3: Find audio file
        logger.info("Step 3: Locating audio file...")
        audio_files = list(AUDIO_DIR.glob("*.mp3"))
        if not audio_files:
            pytest.skip("No audio file found. Download audio first.")

        audio_path = max(audio_files, key=lambda p: p.stat().st_mtime)  # Most recent
        logger.info(f"Using audio: {audio_path}")

        # Step 4: Transcribe audio (or load cached)
        logger.info("Step 4: Transcribing audio...")
        transcript_cache = OUTPUT_DIR / f"transcript_{audio_path.stem}.json"

        if transcript_cache.exists():
            logger.info("Loading cached transcript...")
            segments = json.loads(transcript_cache.read_text())
        else:
            transcriber = WhisperTranscriber(model_name="base")
            segments = transcriber.transcribe(audio_path)
            transcript_cache.write_text(json.dumps(segments, indent=2, ensure_ascii=False))
            logger.info(f"Transcript cached: {transcript_cache}")

        # Step 5: Create audio-synced timeline
        logger.info("Step 5: Creating audio-synced timeline...")
        timeline = create_audio_synced_timeline(segments, mindmap_data['nodes'])

        # Save timeline
        timeline_path = OUTPUT_DIR / f"timeline_{timestamp}.json"
        timeline_path.write_text(json.dumps(timeline, indent=2, ensure_ascii=False))
        logger.info(f"Timeline saved: {timeline_path}")

        # Step 6: Collapse all nodes (prepare for animation)
        logger.info("Step 6: Collapsing all nodes...")
        await recorder.collapse_all_nodes()
        await page.screenshot(path=str(OUTPUT_DIR / f"03_collapsed_{timestamp}.png"))

        # Step 7: Simulate animation (without actual recording for now)
        logger.info("Step 7: Simulating animation timeline...")
        logger.info("-" * 40)

        # For demonstration, show when each node would expand
        for entry in timeline[:10]:  # First 10 events
            logger.info(f"  {entry['time']:6.1f}s: EXPAND '{entry['node'][:40]}'")
            logger.info(f"          Trigger: '{entry['trigger_text']}'")

        if len(timeline) > 10:
            logger.info(f"  ... and {len(timeline) - 10} more events")

        logger.info("-" * 40)

        # Step 8: Run actual animation (expand nodes at timeline times)
        logger.info("Step 8: Running animation preview (first 5 nodes)...")

        for entry in timeline[:5]:
            logger.info(f"Expanding: {entry['node'][:40]}...")
            await recorder.expand_node_by_text(entry['node'])
            await asyncio.sleep(1)
            await page.screenshot(path=str(OUTPUT_DIR / f"expand_{entry['time']:.0f}s_{timestamp}.png"))

        # Final screenshot
        await page.screenshot(path=str(OUTPUT_DIR / f"99_final_{timestamp}.png"))

        logger.info("=" * 60)
        logger.info("Test completed!")
        logger.info(f"Output directory: {OUTPUT_DIR}")
        logger.info(f"Total timeline events: {len(timeline)}")
        logger.info("=" * 60)

        # Return results for assertion
        return {
            "nodes": len(mindmap_data['nodes']),
            "timeline_events": len(timeline),
            "audio_duration": segments[-1]['end'] if segments else 0
        }


if __name__ == "__main__":
    asyncio.run(test_mindmap_audio_sync_recording())
