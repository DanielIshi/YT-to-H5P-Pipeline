"""H5P Package Generator"""
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Union, Dict, Any

from .content_types import MultiChoiceContent, CoursePresentationContent


class H5PGenerator:
    """Generates H5P packages from content models"""

    # Path to H5P library templates
    LIBRARY_PATH = Path("/tmp/h5p_build")

    def __init__(self, library_path: str = None):
        if library_path:
            self.library_path = Path(library_path)
        else:
            self.library_path = self.LIBRARY_PATH

    def generate(
        self,
        content: Union[MultiChoiceContent, CoursePresentationContent],
        output_path: str
    ) -> str:
        """Generate H5P package from content model"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create content directory
            content_dir = tmppath / "content"
            content_dir.mkdir()

            # Write content.json
            content_json = content.to_content_json()
            with open(content_dir / "content.json", "w", encoding="utf-8") as f:
                json.dump(content_json, f, ensure_ascii=False, indent=2)

            # Write h5p.json
            h5p_json = content.to_h5p_json()
            with open(tmppath / "h5p.json", "w", encoding="utf-8") as f:
                json.dump(h5p_json, f, ensure_ascii=False, indent=2)

            # Copy required libraries
            self._copy_libraries(tmppath, h5p_json)

            # Create ZIP
            self._create_zip(tmppath, output_path)

        return output_path

    def _copy_libraries(self, dest: Path, h5p_json: Dict[str, Any]):
        """Copy required H5P libraries to package directory"""
        for dep in h5p_json.get("preloadedDependencies", []):
            machine_name = dep["machineName"]
            lib_src = self.library_path / machine_name

            if lib_src.exists():
                lib_dest = dest / machine_name
                shutil.copytree(lib_src, lib_dest, dirs_exist_ok=True)

                # Remove .git if exists
                git_dir = lib_dest / ".git"
                if git_dir.exists():
                    shutil.rmtree(git_dir)

    # Allowed file extensions in H5P packages (Moodle whitelist)
    # Note: md/textile are technically allowed but we skip README files anyway
    ALLOWED_EXTENSIONS = {
        'json', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tif', 'tiff', 'svg',
        'eot', 'ttf', 'woff', 'woff2', 'otf',
        'webm', 'mp4', 'ogg', 'mp3', 'm4a', 'wav',
        'txt', 'pdf', 'rtf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'odt', 'ods', 'odp', 'xml', 'csv', 'diff', 'patch', 'swf',
        'md', 'textile', 'vtt', 'webvtt', 'js', 'css'
    }

    # Files to exclude even if extension is allowed
    EXCLUDED_FILES = {
        'crowdin.yml', 'README.md', 'LICENCE.md', 'LICENSE.md',
        'package.json', 'package-lock.json', 'webpack.config.js',
        '.gitignore', '.eslintrc.json', '.babelrc', '.h5pignore'
    }

    def _create_zip(self, source_dir: Path, output_path: str):
        """Create H5P ZIP archive"""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                # Skip .git and .github directories
                dirs[:] = [d for d in dirs if d not in ('.git', '.github')]

                for file in files:
                    # Skip hidden files
                    if file.startswith('.'):
                        continue
                    # Skip specifically excluded files
                    if file in self.EXCLUDED_FILES:
                        continue
                    # Filter out files with disallowed extensions
                    ext = file.rsplit('.', 1)[-1].lower() if '.' in file else ''
                    if ext and ext not in self.ALLOWED_EXTENSIONS:
                        continue

                    file_path = Path(root) / file
                    arcname = file_path.relative_to(source_dir)
                    zf.write(file_path, arcname)


def generate_multichoice_h5p(
    question: str,
    answers: list,
    title: str = "Quiz",
    output_path: str = "/tmp/quiz.h5p"
) -> str:
    """Convenience function to generate Multiple Choice H5P

    Args:
        question: The quiz question
        answers: List of dicts with keys: text, correct (bool), feedback (optional)
        title: Title for the H5P content
        output_path: Where to save the .h5p file

    Returns:
        Path to the generated .h5p file
    """
    from content_types import Answer

    answer_objects = [
        Answer(
            text=a["text"],
            correct=a.get("correct", False),
            feedback=a.get("feedback", "")
        )
        for a in answers
    ]

    content = MultiChoiceContent(
        question=question,
        answers=answer_objects,
        title=title
    )

    generator = H5PGenerator()
    return generator.generate(content, output_path)


def generate_course_presentation_h5p(
    content: CoursePresentationContent,
    output_path: str = "/tmp/presentation.h5p"
) -> str:
    """Convenience function to generate Course Presentation H5P

    Args:
        content: CoursePresentationContent object with slides
        output_path: Where to save the .h5p file

    Returns:
        Path to the generated .h5p file
    """
    generator = H5PGenerator()
    return generator.generate(content, output_path)
