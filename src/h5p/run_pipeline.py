#!/usr/bin/env python3
"""
3-Stage H5P Learning Path Pipeline

CLI entry point for the new modular pipeline:
- Stage 1: Transcript → Structured Script (with caching)
- Stage 2: Script → Learning Path Plan (milestone-specific)
- Stage 3: Plan → H5P Content + Moodle Import
"""
import asyncio
import json
import os
from datetime import datetime
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
import httpx
from dotenv import load_dotenv

# Load environment early
load_dotenv()

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.h5p.pipeline.stage1_summarizer import summarize_transcript
from src.h5p.pipeline.stage2_planner import plan_learning_path, validate_learning_path
from src.h5p.pipeline.stage3_generator import generate_all_content
from src.h5p.config.milestones import get_milestone_config, MILESTONE_CONFIGS
from src.h5p.builders import build_h5p, build_column_h5p, prepare_activity_for_column, BUILDERS


def log_info(msg: str):
    """Print info message to stderr as JSON."""
    print(json.dumps({"status": "info", "message": msg}), file=sys.stderr)


def log_progress(msg: str, **extra):
    """Print progress message to stderr as JSON."""
    print(json.dumps({"status": "progress", "message": msg, **extra}), file=sys.stderr)


def log_error(msg: str):
    """Print error message to stderr as JSON."""
    print(json.dumps({"status": "error", "message": msg}), file=sys.stderr)


def delete_moodle_course(courseid: int) -> dict:
    """Delete a Moodle course via CLI (used to clean up previous runs)."""
    try:
        cmd = [
            "docker", "exec", "moodle-app", "php",
            "/opt/bitnami/moodle/admin/cli/delete_course.php",
            f"--courseid={courseid}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def fetch_youtube_data(youtube_url_id: int) -> dict:
    """Fetch YouTube data from Supabase by ID."""
    supabase_url = os.environ.get("SUPABASE_URL", "http://148.230.71.150:8000")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))

    url = f"{supabase_url}/rest/v1/youtube_urls?id=eq.{youtube_url_id}&select=id,title,subtitles,url"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

    if not data:
        raise ValueError(f"YouTube URL with ID {youtube_url_id} not found in Supabase")

    return data[0]


def import_h5p_to_moodle(
    h5p_path: str,
    courseid: Optional[int],
    title: str,
    *,
    create_course: bool = False,
    course_name: Optional[str] = None,
    section: int = 0
) -> dict:
    """Import H5P to Moodle via PHP script."""
    try:
        # Copy file to container
        subprocess.run(
            ["docker", "cp", h5p_path, "moodle-app:/tmp/generated.h5p"],
            check=True, capture_output=True
        )

        # Run import script
        cmd = [
            "docker", "exec", "moodle-app", "php",
            "/opt/bitnami/moodle/local/import_h5p.php",
            f"--file=/tmp/generated.h5p",
            f"--title={title}",
            f"--section={section}"
        ]
        if create_course:
            cmd.append("--createcourse")
            if course_name:
                cmd.append(f"--coursename={course_name}")
        else:
            cmd.append(f"--courseid={courseid}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse JSON result
        for line in result.stdout.split("\n"):
            if line.startswith("{"):
                return json.loads(line)

        return {"status": "error", "message": result.stderr or result.stdout}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def validate_mix(learning_path: dict, milestone: str) -> dict:
    """Validate the learning path mix against milestone rules."""
    config = get_milestone_config(milestone)
    is_valid, errors = validate_learning_path(learning_path, config)

    activities = learning_path.get("learning_path", [])

    # Calculate phase distribution
    passive_types = config["phases"].get("passive", {}).get("types", [])
    active_types = config["phases"].get("active", {}).get("types", [])
    reflect_types = config["phases"].get("reflect", {}).get("types", [])

    passive = sum(1 for a in activities if a.get("content_type") in passive_types)
    active = sum(1 for a in activities if a.get("content_type") in active_types)
    reflect = sum(1 for a in activities if a.get("content_type") in reflect_types)
    total = len(activities)

    return {
        "all_ok": is_valid,
        "errors": errors,
        "distribution": {
            "passive": passive,
            "active": active,
            "reflect": reflect,
            "total": total
        },
        "percentages": {
            "passive": f"{passive/total*100:.1f}%" if total > 0 else "0%",
            "active": f"{active/total*100:.1f}%" if total > 0 else "0%",
            "reflect": f"{reflect/total*100:.1f}%" if total > 0 else "0%"
        }
    }


async def run_full_pipeline(
    youtube_url_id: int,
    milestone: str,
    courseid: Optional[int],
    create_course: bool = True,
    course_name: Optional[str] = None,
    delete_old_courseid: Optional[int] = None,
    target_section: int = 0,
    skip_cache: bool = False,
    output_dir: str = "/tmp/h5p_pipeline"
) -> dict:
    """
    Run the complete 3-stage pipeline.

    Args:
        youtube_url_id: Supabase ID of the YouTube URL
        milestone: Milestone config to use (mvp, 1.1, 1.2, 1.3)
        courseid: Moodle course ID for import (ignored if create_course is True)
        create_course: If True, create a fresh Moodle course for this run
        course_name: Optional course name (defaults to video title + timestamp)
        delete_old_courseid: Optional course ID to delete after successful import
        target_section: Moodle section number to place activities (0 = General)
        skip_cache: If True, ignore cached structured script
        output_dir: Directory for H5P files

    Returns:
        Dict with results
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Fetch transcript from Supabase
    log_info(f"Fetching transcript for youtube_url_id={youtube_url_id}")
    yt_data = await fetch_youtube_data(youtube_url_id)
    transcript = yt_data.get("subtitles", "")
    title = yt_data.get("title", "Lernmodul")
    video_url = yt_data.get("url", "")

    if not transcript:
        return {"status": "error", "message": "No transcript found"}

    log_info(f"Transcript: {len(transcript)} chars - '{title}'")

    # 2. Stage 1: Transcript → Structured Script
    log_info("Stage 1: Summarizing transcript...")
    structured_script = await summarize_transcript(
        transcript,
        youtube_url_id=youtube_url_id,
        force=skip_cache
    )
    log_progress(
        "Stage 1 complete",
        sections=len(structured_script.get("sections", [])),
        key_terms=len(structured_script.get("key_terms", []))
    )

    # 3. Stage 2: Script → Learning Path Plan
    log_info(f"Stage 2: Planning learning path (milestone={milestone})...")
    learning_path = await plan_learning_path(structured_script, milestone=milestone)
    activities = learning_path.get("learning_path", [])
    log_progress(
        "Stage 2 complete",
        activities=len(activities),
        types=[a.get("content_type") for a in activities]
    )

    # 4. Validate mix
    validation = validate_mix(learning_path, milestone)
    if not validation["all_ok"]:
        log_info(f"Mix validation warnings: {validation['errors']}")
    log_progress(
        "Mix validation",
        distribution=validation["percentages"]
    )

    # 5. Stage 3: Plan → H5P Content
    log_info("Stage 3: Generating H5P content...")
    h5p_contents = await generate_all_content(learning_path, structured_script)
    log_progress("Stage 3 complete", generated=len(h5p_contents))

    # 6. Build H5P packages and import to Moodle
    config = get_milestone_config(milestone)
    auto_check = config.get("rules", {}).get("auto_advance_on_correct", True)
    if auto_check:
        log_info("Auto-check enabled (default)")

    # Determine course handling
    current_courseid = courseid if (courseid and not create_course) else None
    course_title = course_name or f"{title or 'Lernmodul'} {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"

    if not create_course and current_courseid is None:
        return {"status": "error", "message": "Provide --courseid or enable --create-course"}

    results = []

    # Map generated content by activity order for quick lookup
    content_by_order = {}
    for activity, content in zip(activities, h5p_contents):
        order = activity.get("order")
        if order is not None:
            content_by_order[order] = content

    # Check if LLM returned columns structure (new format)
    columns = learning_path.get("columns", [])

    if columns:
        # NEW: Column-based import (3-4 Moodle entries instead of 7)
        log_info(f"Building {len(columns)} Column packages...")

        for col_idx, column in enumerate(columns):
            col_title = column.get("title", f"Teil {col_idx + 1}")
            col_activities = column.get("activities", [])

            # Collect content for each activity in this column
            column_activities = []
            for activity in col_activities:
                order = activity.get("order", 0)
                content_type = activity.get("content_type")

                content = content_by_order.get(order)

                if not content:
                    log_info(f"No generated content for order {order} ({content_type})")
                    continue

                if "_error" in content:
                    log_info(f"Skipping activity with generation error (order={order}, type={content_type})")
                    continue

                prepared = prepare_activity_for_column(
                    content_type,
                    content,
                    auto_check=auto_check
                )
                column_activities.append(prepared)

            if not column_activities:
                log_info(f"Skipping empty column: {col_title}")
                continue

            # Build Column H5P
            h5p_path = os.path.join(output_dir, f"column_{col_idx + 1}_{col_title[:20]}.h5p")
            column_data = {
                "title": col_title,
                "activities": column_activities
            }

            try:
                build_column_h5p(column_data, h5p_path)
                moodle_result = import_h5p_to_moodle(
                    h5p_path,
                    current_courseid,
                    col_title,
                    create_course=create_course and current_courseid is None,
                    course_name=course_title,
                    section=target_section
                )

                if moodle_result.get("courseid") and current_courseid is None:
                    current_courseid = moodle_result.get("courseid")

                    if delete_old_courseid:
                        delete_moodle_course(delete_old_courseid)

                results.append({
                    "column": col_idx + 1,
                    "title": col_title,
                    "activities_count": len(column_activities),
                    "h5p_path": h5p_path,
                    "moodle": moodle_result
                })

                log_progress(
                    f"Imported Column '{col_title}'",
                    column=col_idx + 1,
                    activities=len(column_activities)
                )

            except Exception as e:
                results.append({
                    "column": col_idx + 1,
                    "title": col_title,
                    "error": str(e)
                })
                log_error(f"Column build failed: {e}")

    else:
        # LEGACY: Separate activity import (7 Moodle entries)
        log_info("Building separate H5P packages (legacy mode)...")

        for i, (activity, content) in enumerate(zip(activities, h5p_contents)):
            content_type = activity.get("content_type")
            act_title = f"{i+1}. {activity.get('brief', content_type)[:50]}"

            if "_error" in content:
                results.append({
                    "order": i + 1,
                    "type": content_type,
                    "title": act_title,
                    "error": content["_error"]
                })
                continue

            h5p_path = os.path.join(output_dir, f"activity_{i+1}_{content_type}.h5p")

            try:
                build_data = {**content}
                build_data["title"] = act_title
                if not build_data.get("video_url") and video_url:
                    build_data["video_url"] = video_url

                if auto_check and content_type in ["multichoice", "truefalse", "blanks"]:
                    build_data["auto_check"] = True

                build_h5p(content_type, build_data, h5p_path)
                moodle_result = import_h5p_to_moodle(
                    h5p_path,
                    current_courseid,
                    act_title,
                    create_course=create_course and current_courseid is None,
                    course_name=course_title,
                    section=target_section
                )

                if moodle_result.get("courseid") and current_courseid is None:
                    current_courseid = moodle_result.get("courseid")

                    if delete_old_courseid:
                        delete_moodle_course(delete_old_courseid)

                results.append({
                    "order": i + 1,
                    "type": content_type,
                    "title": act_title,
                    "h5p_path": h5p_path,
                    "moodle": moodle_result
                })

                log_progress(
                    f"Imported {content_type}",
                    order=i + 1
                )

            except Exception as e:
                results.append({
                    "order": i + 1,
                    "type": content_type,
                    "title": act_title,
                    "error": str(e)
                })

    # 7. Summary
    successful = sum(1 for r in results if "moodle" in r and r["moodle"].get("status") == "success")

    return {
        "status": "success" if successful > 0 else "error",
        "pipeline_version": "3-stage",
        "milestone": milestone,
        "youtube_url_id": youtube_url_id,
        "title": title,
        "total_activities": len(activities),
        "successful_imports": successful,
        "validation": validation,
        "activities": results
    }


@click.command()
@click.option("--youtube-url-id", type=int, required=True, help="Supabase youtube_urls.id")
@click.option(
    "--milestone",
    type=click.Choice(list(MILESTONE_CONFIGS.keys())),
    default="mvp",
    help="Milestone configuration to use"
)
@click.option("--courseid", type=int, default=None, help="Moodle course ID (ignored if --create-course)")
@click.option("--create-course/--no-create-course", default=True, help="Create a fresh Moodle course for this run")
@click.option("--course-name", default=None, help="Name for newly created course")
@click.option("--delete-old-courseid", type=int, default=None, help="Optional course ID to delete after successful import")
@click.option("--target-section", type=int, default=0, help="Moodle section number to place activities (0 = General)")
@click.option("--skip-cache", is_flag=True, help="Ignore cached structured script")
@click.option("--output-dir", default="/tmp/h5p_pipeline", help="Output directory for H5P files")
@click.option("--dry-run", is_flag=True, help="Generate content but don't import to Moodle")
def main(
    youtube_url_id: int,
    milestone: str,
    courseid: Optional[int],
    create_course: bool,
    course_name: Optional[str],
    delete_old_courseid: Optional[int],
    target_section: int,
    skip_cache: bool,
    output_dir: str,
    dry_run: bool
):
    """
    3-Stage H5P Learning Path Pipeline.

    Generates H5P activities from YouTube transcripts using:
    - Stage 1: Transcript summarization
    - Stage 2: Learning path planning
    - Stage 3: H5P content generation
    """
    async def _run():
        if dry_run:
            log_info("DRY RUN - Will not import to Moodle")
            # TODO: Implement dry run mode
            return {"status": "error", "message": "Dry run not yet implemented"}

        return await run_full_pipeline(
            youtube_url_id=youtube_url_id,
            milestone=milestone,
            courseid=courseid,
            create_course=create_course,
            course_name=course_name,
            delete_old_courseid=delete_old_courseid,
            target_section=target_section,
            skip_cache=skip_cache,
            output_dir=output_dir
        )

    result = asyncio.run(_run())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
