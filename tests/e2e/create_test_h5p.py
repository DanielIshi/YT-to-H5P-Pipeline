#!/usr/bin/env python3
"""
Create test H5P packages for the critical content types to verify the library patches.
Tests: TrueFalse, Blanks, Summary, DragText (the ones that were patched)
"""
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

# Content type builders
def build_truefalse(question: str, correct: bool) -> dict:
    """Build TrueFalse H5P package structure"""
    h5p_json = {
        "title": "TrueFalse Test",
        "language": "de",
        "mainLibrary": "H5P.TrueFalse",
        "embedTypes": ["iframe"],
        "preloadedDependencies": [
            {"machineName": "H5P.TrueFalse", "majorVersion": 1, "minorVersion": 8},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }
    content_json = {
        "question": f"<p>{question}</p>",
        "correct": "true" if correct else "false",
        "l10n": {
            "trueText": "Wahr",
            "falseText": "Falsch"
        },
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "confirmCheckDialog": False,
            "confirmRetryDialog": False
        }
    }
    return h5p_json, content_json


def build_blanks(text_with_blanks: str, title: str = "Blanks Test") -> dict:
    """Build Blanks H5P package structure"""
    h5p_json = {
        "title": title,
        "language": "de",
        "mainLibrary": "H5P.Blanks",
        "embedTypes": ["iframe"],
        "preloadedDependencies": [
            {"machineName": "H5P.Blanks", "majorVersion": 1, "minorVersion": 14},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }
    content_json = {
        "text": f"<p>{text_with_blanks}</p>",
        "overallFeedback": [{"from": 0, "to": 100, "feedback": "Gut gemacht!"}],
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "caseSensitive": False,
            "showSolutionsRequiresInput": True,
            "autoCheck": False,
            "separateLines": False
        }
    }
    return h5p_json, content_json


def build_summary(intro: str, statements: list) -> dict:
    """Build Summary H5P package structure"""
    h5p_json = {
        "title": "Summary Test",
        "language": "de",
        "mainLibrary": "H5P.Summary",
        "embedTypes": ["iframe"],
        "preloadedDependencies": [
            {"machineName": "H5P.Summary", "majorVersion": 1, "minorVersion": 10},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }
    # Build summary panels - each panel has statements, first is correct
    # H5P.Summary expects summary as array of HTML strings (first one is correct!)
    panels = []
    for stmt_group in statements:
        panel = {
            "summary": [f"<p>{s}</p>" for s in stmt_group],
            "tip": ""
        }
        panels.append(panel)

    content_json = {
        "intro": f"<p>{intro}</p>",
        "summaries": panels,
        "overallFeedback": [{"from": 0, "to": 100, "feedback": "Gut!"}]
    }
    return h5p_json, content_json


def build_dragtext(task_description: str, text_with_drag: str) -> dict:
    """Build DragText H5P package structure"""
    h5p_json = {
        "title": "DragText Test",
        "language": "de",
        "mainLibrary": "H5P.DragText",
        "embedTypes": ["iframe"],
        "preloadedDependencies": [
            {"machineName": "H5P.DragText", "majorVersion": 1, "minorVersion": 10},
            {"machineName": "H5P.Question", "majorVersion": 1, "minorVersion": 5},
            {"machineName": "H5P.JoubelUI", "majorVersion": 1, "minorVersion": 3},
            {"machineName": "FontAwesome", "majorVersion": 4, "minorVersion": 5}
        ]
    }
    content_json = {
        "taskDescription": f"<p>{task_description}</p>",
        "textField": text_with_drag,
        "overallFeedback": [{"from": 0, "to": 100, "feedback": "Gut gemacht!"}],
        "behaviour": {
            "enableRetry": True,
            "enableSolutionsButton": True,
            "instantFeedback": False
        }
    }
    return h5p_json, content_json


def create_h5p_package(h5p_json: dict, content_json: dict, output_path: str):
    """Create H5P ZIP package"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create content directory
        content_dir = Path(tmpdir) / "content"
        content_dir.mkdir()

        # Write h5p.json
        with open(Path(tmpdir) / "h5p.json", "w", encoding="utf-8") as f:
            json.dump(h5p_json, f, ensure_ascii=False, indent=2)

        # Write content/content.json
        with open(content_dir / "content.json", "w", encoding="utf-8") as f:
            json.dump(content_json, f, ensure_ascii=False, indent=2)

        # Create ZIP
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(Path(tmpdir) / "h5p.json", "h5p.json")
            zf.write(content_dir / "content.json", "content/content.json")

    return output_path


def upload_and_import(local_path: str, title: str, courseid: int = 22):
    """Upload H5P to VPS and import via PHP script"""
    filename = os.path.basename(local_path)
    remote_path = f"/tmp/{filename}"

    # SCP upload
    print(f"  Uploading {filename}...")
    result = subprocess.run(
        ["scp", local_path, f"root@148.230.71.150:{remote_path}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ERROR uploading: {result.stderr}")
        return None

    # Copy to container
    subprocess.run(
        ["ssh", "root@148.230.71.150",
         f"docker cp {remote_path} moodle-app:/tmp/{filename}"],
        capture_output=True
    )

    # Import via PHP
    print(f"  Importing as '{title}'...")
    result = subprocess.run(
        ["ssh", "root@148.230.71.150",
         f"docker exec moodle-app php /opt/bitnami/moodle/local/import_h5p.php "
         f"--file=/tmp/{filename} --title=\"{title}\" --courseid={courseid}"],
        capture_output=True, text=True
    )

    try:
        response = json.loads(result.stdout.strip().split('\n')[-1])
        if response.get('status') == 'success':
            print(f"  SUCCESS: cmid={response.get('cmid')}, url={response.get('url')}")
            return response
        else:
            print(f"  ERROR: {response.get('message')}")
            return None
    except:
        print(f"  ERROR parsing response: {result.stdout}")
        print(f"  STDERR: {result.stderr}")
        return None


def main():
    print("=" * 60)
    print("Creating test H5P packages for patched libraries")
    print("=" * 60)

    output_dir = Path(__file__).parent / "h5p_test_packages"
    output_dir.mkdir(exist_ok=True)

    results = []

    # Test 1: TrueFalse
    print("\n1. Creating TrueFalse test...")
    h5p, content = build_truefalse(
        "KI kann menschliche Sprache verstehen und generieren.",
        correct=True
    )
    pkg_path = str(output_dir / "test_truefalse.h5p")
    create_h5p_package(h5p, content, pkg_path)
    result = upload_and_import(pkg_path, "Test: TrueFalse")
    if result:
        results.append(("TrueFalse", result.get('cmid'), result.get('url')))

    # Test 2: Blanks
    print("\n2. Creating Blanks test...")
    h5p, content = build_blanks(
        "Machine Learning ist ein Teilbereich der *künstlichen Intelligenz*. "
        "Dabei lernt ein *Algorithmus* aus *Daten*."
    )
    pkg_path = str(output_dir / "test_blanks.h5p")
    create_h5p_package(h5p, content, pkg_path)
    result = upload_and_import(pkg_path, "Test: Blanks")
    if result:
        results.append(("Blanks", result.get('cmid'), result.get('url')))

    # Test 3: Summary
    print("\n3. Creating Summary test...")
    h5p, content = build_summary(
        "Wähle die korrekten Aussagen über KI aus:",
        [
            ["KI kann Muster in Daten erkennen", "KI kann nicht lernen", "KI braucht keine Daten"],
            ["Machine Learning nutzt Algorithmen", "ML ist keine KI", "ML funktioniert ohne Computer"]
        ]
    )
    pkg_path = str(output_dir / "test_summary.h5p")
    create_h5p_package(h5p, content, pkg_path)
    result = upload_and_import(pkg_path, "Test: Summary")
    if result:
        results.append(("Summary", result.get('cmid'), result.get('url')))

    # Test 4: DragText
    print("\n4. Creating DragText test...")
    h5p, content = build_dragtext(
        "Ziehe die Wörter an die richtige Stelle:",
        "*KI* steht für künstliche *Intelligenz*. Sie nutzt *Algorithmen* zum Lernen."
    )
    pkg_path = str(output_dir / "test_dragtext.h5p")
    create_h5p_package(h5p, content, pkg_path)
    result = upload_and_import(pkg_path, "Test: DragText")
    if result:
        results.append(("DragText", result.get('cmid'), result.get('url')))

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    for name, cmid, url in results:
        print(f"  {name}: cmid={cmid}")
        print(f"    URL: {url}")

    # Save CMIDs for testing
    cmids = [r[1] for r in results if r[1]]
    print(f"\nCMIDs for Playwright test: {cmids}")

    # Write to file for Playwright
    with open(output_dir / "test_cmids.json", "w") as f:
        json.dump({"cmids": cmids, "results": [{"name": r[0], "cmid": r[1], "url": r[2]} for r in results]}, f, indent=2)

    return cmids


if __name__ == "__main__":
    main()
