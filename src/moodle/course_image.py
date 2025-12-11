"""
Moodle Course Image Service

Uploads course images via Moodle Web Services API.
Supports YouTube thumbnails and DALL-E generated images.
"""

import os
import base64
import httpx
import re
from typing import Optional
from pathlib import Path


# Configuration from environment
MOODLE_URL = os.getenv("MOODLE_URL", "https://moodle.srv947487.hstgr.cloud")
MOODLE_TOKEN = os.getenv("MOODLE_TOKEN", "")


def get_youtube_thumbnail_url(video_url: str) -> Optional[str]:
    """Extract YouTube video ID and return maxres thumbnail URL."""
    if not video_url:
        return None

    match = re.search(
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        video_url
    )
    if match:
        video_id = match.group(1)
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    return None


def download_image(url: str) -> Optional[bytes]:
    """Download image from URL and return bytes."""
    try:
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Failed to download image: {e}")
        return None


def generate_course_thumbnail(title: str, transcript: str = "") -> Optional[str]:
    """
    Generate a course thumbnail using DALL-E.
    Returns the URL of the generated image.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None

    # Create a focused prompt for course thumbnail
    context = transcript[:300] if transcript else ""

    prompt = f"""Create a professional e-learning course thumbnail image.

Topic: {title}
Context: {context}

Style requirements:
- Clean, modern design with vibrant colors
- Professional look suitable for online learning platform
- Include subtle visual elements representing the topic
- No text or labels in the image
- Suitable as a course card thumbnail (16:9 aspect ratio)
- Eye-catching but not cluttered
- Use blues, teals, and professional accent colors"""

    try:
        response = httpx.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1792x1024",
                "quality": "standard",
                "response_format": "url"
            },
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()["data"][0]["url"]
    except Exception as e:
        print(f"DALL-E generation failed: {e}")
        return None


def upload_course_image(course_id: int, image_data: bytes, filename: str = "course_image.jpg") -> bool:
    """
    Upload course image to Moodle via Web Services API.

    Uses core_files_upload to upload the file, then core_course_update_courses
    to set it as the course overview image.
    """
    if not MOODLE_TOKEN:
        print("No MOODLE_TOKEN configured")
        return False

    try:
        # Step 1: Upload file to user draft area
        upload_url = f"{MOODLE_URL}/webservice/upload.php"

        files = {
            'file_1': (filename, image_data, 'image/jpeg')
        }
        data = {
            'token': MOODLE_TOKEN,
            'filearea': 'draft',
            'itemid': 0
        }

        response = httpx.post(upload_url, data=data, files=files, timeout=30.0)
        response.raise_for_status()

        upload_result = response.json()
        if isinstance(upload_result, list) and len(upload_result) > 0:
            item_id = upload_result[0].get('itemid')
        else:
            print(f"Upload failed: {upload_result}")
            return False

        # Step 2: Update course with the uploaded image
        update_url = f"{MOODLE_URL}/webservice/rest/server.php"

        params = {
            'wstoken': MOODLE_TOKEN,
            'wsfunction': 'core_course_update_courses',
            'moodlewsrestformat': 'json',
            'courses[0][id]': course_id,
            'courses[0][overviewfiles_filemanager]': item_id
        }

        response = httpx.post(update_url, data=params, timeout=30.0)
        response.raise_for_status()

        result = response.json()
        if 'exception' in result:
            print(f"Moodle API error: {result.get('message', 'Unknown error')}")
            return False

        print(f"Course image uploaded successfully for course {course_id}")
        return True

    except Exception as e:
        print(f"Failed to upload course image: {e}")
        return False


def set_course_image_from_youtube(course_id: int, video_url: str) -> bool:
    """
    Set course image from YouTube video thumbnail.
    """
    thumbnail_url = get_youtube_thumbnail_url(video_url)
    if not thumbnail_url:
        print("Could not extract YouTube video ID")
        return False

    image_data = download_image(thumbnail_url)
    if not image_data:
        return False

    return upload_course_image(course_id, image_data, "youtube_thumbnail.jpg")


def set_course_image_generated(course_id: int, title: str, transcript: str = "") -> bool:
    """
    Generate and set course image using DALL-E.
    """
    image_url = generate_course_thumbnail(title, transcript)
    if not image_url:
        return False

    image_data = download_image(image_url)
    if not image_data:
        return False

    return upload_course_image(course_id, image_data, "generated_thumbnail.jpg")


def set_course_image(course_id: int, video_url: str = "", title: str = "", transcript: str = "", use_ai: bool = False) -> bool:
    """
    Set course image - tries YouTube thumbnail first, falls back to DALL-E if enabled.

    Args:
        course_id: Moodle course ID
        video_url: YouTube video URL (for thumbnail extraction)
        title: Course title (for DALL-E prompt)
        transcript: Course transcript (for DALL-E context)
        use_ai: If True, generate image with DALL-E; otherwise use YouTube thumbnail

    Returns:
        True if image was set successfully
    """
    # Try YouTube thumbnail first (free, fast)
    if video_url:
        if set_course_image_from_youtube(course_id, video_url):
            return True
        print("YouTube thumbnail failed, trying DALL-E...")

    # Fall back to DALL-E if enabled
    if use_ai and title:
        return set_course_image_generated(course_id, title, transcript)

    return False


# CLI for testing
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 3:
        print("Usage: python course_image.py <course_id> <youtube_url_or_title>")
        print("Example: python course_image.py 25 'https://youtube.com/watch?v=...'")
        sys.exit(1)

    course_id = int(sys.argv[1])
    source = sys.argv[2]

    if 'youtube' in source or 'youtu.be' in source:
        success = set_course_image_from_youtube(course_id, source)
    else:
        success = set_course_image_generated(course_id, source)

    print(f"Result: {'Success' if success else 'Failed'}")
    sys.exit(0 if success else 1)
