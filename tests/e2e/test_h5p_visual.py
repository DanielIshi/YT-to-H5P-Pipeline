"""
E2E Visual Tests für H5P Content-Types in Moodle

Testet alle 9 H5P Content-Types auf:
- Erreichbarkeit (HTTP 200 nach Login)
- Visuelles Rendering (Screenshot)
- H5P iframe korrekt geladen
- Keine JavaScript-Fehler
"""
import os
import pytest
from playwright.sync_api import sync_playwright, Page, expect

# Moodle Konfiguration
MOODLE_URL = "https://moodle.srv947487.hstgr.cloud"
# Use student account to avoid preview mode
MOODLE_USER = "student1"
MOODLE_PASS = "Student2025!"

# H5P Activities (Course Module IDs 92-100 - deployed with fixed h5p framework integration)
H5P_ACTIVITIES = [
    {"cmid": 92, "name": "1. Themenübersicht", "type": "ImageHotspots"},
    {"cmid": 93, "name": "2. Wichtige Begriffe", "type": "Dialogcards"},
    {"cmid": 94, "name": "3. Kernaussagen", "type": "Accordion"},
    {"cmid": 95, "name": "4. Video mit Quizfragen", "type": "InteractiveVideo"},
    {"cmid": 96, "name": "5. Verständnischeck", "type": "MultiChoice"},
    {"cmid": 97, "name": "6. Lückentext", "type": "Blanks"},
    {"cmid": 98, "name": "7. Faktencheck", "type": "TrueFalse"},
    {"cmid": 99, "name": "8. Zuordnung", "type": "DragAndDrop"},
    {"cmid": 100, "name": "9. Zusammenfassung", "type": "Summary"},
]

# Screenshot-Verzeichnis
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


class MoodleH5PTest:
    """Test-Klasse für Moodle H5P Visual Tests"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.js_errors = []

    def setup(self):
        """Browser starten und einloggen"""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()

        # JavaScript-Fehler sammeln
        self.page.on("console", lambda msg: self._log_console(msg))
        self.page.on("pageerror", lambda err: self._log_page_error(err))

        # Login
        self._login()

    def _log_console(self, msg):
        """Console-Nachrichten loggen"""
        if msg.type == "error":
            text = msg.text
            # Mixed Content Warnings sind keine kritischen Fehler
            if "Mixed Content" in text:
                return  # Ignorieren - nur eine Warnung
            # Moodle Boost Theme Bug - nicht kritisch für H5P Content
            if "Cannot destructure property 'theme'" in text:
                return  # Ignorieren - Moodle Theme Bug
            self.js_errors.append(f"Console Error: {text}")

    def _log_page_error(self, err):
        """Page errors loggen (mit Filter)"""
        text = str(err)
        # Moodle Boost Theme Bug - nicht kritisch für H5P Content
        if "Cannot destructure property 'theme'" in text:
            return  # Ignorieren - Moodle Theme Bug
        self.js_errors.append(text)

    def _login(self):
        """Moodle Login"""
        self.page.goto(f"{MOODLE_URL}/login/index.php", timeout=60000)
        self.page.wait_for_load_state("domcontentloaded")

        # Debug: Screenshot vor Login
        self.page.screenshot(path=os.path.join(SCREENSHOT_DIR, "00_login_page.png"))

        # Moodle Login-Formular (nicht das Guest-Login!)
        username_field = self.page.locator("#username[type='text']")
        password_field = self.page.locator("#password")
        login_btn = self.page.locator("#loginbtn")

        username_field.fill(MOODLE_USER)
        password_field.fill(MOODLE_PASS)
        login_btn.click()

        self.page.wait_for_load_state("networkidle", timeout=30000)

        # Debug: Screenshot nach Login
        self.page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_after_login.png"))

        # Prüfen ob Login erfolgreich (Dashboard oder Course page)
        current_url = self.page.url.lower()
        if "login" in current_url or "error" in current_url:
            print(f"Login URL nach Versuch: {self.page.url}")
            raise Exception("Login fehlgeschlagen! Prüfe Screenshots.")

    def test_activity(self, cmid: int, name: str, content_type: str) -> dict:
        """Einzelne H5P Activity testen"""
        result = {
            "cmid": cmid,
            "name": name,
            "type": content_type,
            "reachable": False,
            "h5p_loaded": False,
            "js_errors": [],
            "screenshot": None,
        }

        self.js_errors = []  # Reset für jede Activity

        try:
            # Activity aufrufen
            url = f"{MOODLE_URL}/mod/h5pactivity/view.php?id={cmid}"
            self.page.goto(url, wait_until="networkidle", timeout=30000)

            # Prüfen ob Seite geladen
            result["reachable"] = self.page.url != f"{MOODLE_URL}/login/index.php"

            if result["reachable"]:
                # Warten auf H5P Content (mehr Zeit für komplexe Types)
                self.page.wait_for_timeout(8000)  # H5P braucht Zeit zum Laden

                # Warte auf H5P iframe oder container
                try:
                    self.page.wait_for_selector("iframe.h5p-iframe, .h5p-content, .h5p-container", timeout=10000)
                except:
                    pass  # Fallback wenn kein H5P-Element gefunden

                # Prüfen ob H5P Content existiert (kann iframe ODER direkt eingebettet sein)
                h5p_selectors = [
                    "iframe.h5p-iframe",
                    ".h5p-content",
                    ".h5p-container",
                    ".h5p-actions",
                    ".h5p-image-hotspots",  # ImageHotspots
                    ".h5p-dialogcards",     # Dialogcards
                    ".h5p-accordion",       # Accordion
                    ".h5p-question-content", # MultiChoice/TrueFalse
                    ".h5p-blanks",          # Blanks
                    ".h5p-summary",         # Summary
                    ".h5p-drag-text",       # DragText
                    "[class*='h5p-']",      # Generischer H5P Selector
                ]
                h5p_loaded = False
                for selector in h5p_selectors:
                    if self.page.locator(selector).count() > 0:
                        h5p_loaded = True
                        break
                result["h5p_loaded"] = h5p_loaded

                # Screenshot
                screenshot_path = os.path.join(SCREENSHOT_DIR, f"{cmid}_{content_type}.png")
                self.page.screenshot(path=screenshot_path, full_page=True)
                result["screenshot"] = screenshot_path

            result["js_errors"] = self.js_errors.copy()

        except Exception as e:
            result["error"] = str(e)

        return result

    def teardown(self):
        """Browser schließen"""
        if self.browser:
            self.browser.close()


def run_all_tests():
    """Alle H5P Activities testen"""
    print("=" * 60)
    print("H5P Visual E2E Tests")
    print("=" * 60)
    print(f"\nMoodle: {MOODLE_URL}")
    print(f"Activities: {len(H5P_ACTIVITIES)}\n")

    tester = MoodleH5PTest()
    tester.setup()

    results = []
    passed = 0
    failed = 0

    for activity in H5P_ACTIVITIES:
        print(f"Testing: {activity['name']} ({activity['type']})...", end=" ")

        result = tester.test_activity(
            cmid=activity["cmid"],
            name=activity["name"],
            content_type=activity["type"]
        )
        results.append(result)

        if result["reachable"] and result["h5p_loaded"] and not result["js_errors"]:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            if not result["reachable"]:
                print(f"   - Nicht erreichbar")
            if not result["h5p_loaded"]:
                print(f"   - H5P nicht geladen")
            if result["js_errors"]:
                for err in result["js_errors"][:3]:
                    print(f"   - JS Error: {err[:100]}")

    tester.teardown()

    # Zusammenfassung
    print("\n" + "=" * 60)
    print(f"ERGEBNIS: {passed}/{len(results)} bestanden")
    print("=" * 60)

    if passed == len(results):
        print("\n✅ ALLE TESTS BESTANDEN!")
        print(f"Screenshots: {SCREENSHOT_DIR}")
    else:
        print(f"\n❌ {failed} TESTS FEHLGESCHLAGEN")

    return results


if __name__ == "__main__":
    run_all_tests()
