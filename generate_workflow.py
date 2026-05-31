"""
Stage 2 of youtube-to-workflow pipeline.
Renders workflow .md from LLM-extracted JSON + transcript metadata.
Usage: python generate_workflow.py <extracted_VIDEO_ID.json> [transcript_VIDEO_ID.json]
"""

import json
import sys
from datetime import date
from pathlib import Path

from templates.workflow_template import (
    WORKFLOW_TEMPLATE,
    render_prerequisites,
    render_steps,
    render_tips,
    render_tools,
    render_warnings,
)


def render_workflow(data: dict, transcript_meta: dict) -> str:
    """Render workflow markdown from extracted data dict and transcript metadata dict."""
    auto_warning = ""
    if transcript_meta.get("is_auto_generated"):
        auto_warning = "\n> \u26a0\ufe0f **Auto-generated captions** \u2014 transcript may contain errors. Review steps carefully.\n"

    return WORKFLOW_TEMPLATE.format(
        title=data["title"],
        video_id=transcript_meta.get("video_id", "unknown"),
        date=date.today().isoformat(),
        language=transcript_meta.get("language", "en"),
        duration=transcript_meta.get("duration_human", "unknown"),
        auto_generated_warning=auto_warning,
        summary=data["summary"],
        prerequisites=render_prerequisites(data.get("prerequisites", [])),
        tools=render_tools(data.get("tools_and_commands", [])),
        steps=render_steps(data.get("steps", [])),
        warnings=render_warnings(data.get("warnings", [])),
        tips=render_tips(data.get("tips", [])),
    )


def main_render(extracted_path: str, meta_path: str | None = None) -> str:
    """
    Render workflow from files. Returns path to written .md file.
    Raises FileNotFoundError if extracted_path does not exist.
    """
    ep = Path(extracted_path)
    if not ep.exists():
        raise FileNotFoundError(f"Extracted data not found: {ep}")

    with open(ep, encoding="utf-8") as f:
        data = json.load(f)

    # Infer transcript meta path if not provided
    if meta_path is None:
        video_id = ep.stem.replace("extracted_", "")
        inferred = ep.parent / f"transcript_{video_id}.json"
        meta_path = str(inferred) if inferred.exists() else None

    transcript_meta: dict = {}
    if meta_path and Path(meta_path).exists():
        with open(meta_path, encoding="utf-8") as f:
            transcript_meta = json.load(f)

    content = render_workflow(data, transcript_meta)

    video_id = transcript_meta.get("video_id", ep.stem.replace("extracted_", ""))
    out_path = ep.parent / f"workflow_{video_id}.md"

    try:
        out_path.write_text(content, encoding="utf-8")
    except OSError as e:
        print(f"Error writing {out_path}: {e}", file=sys.stderr)
        sys.exit(1)

    return str(out_path)


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python generate_workflow.py <extracted_VIDEO_ID.json> [transcript_VIDEO_ID.json]",
            file=sys.stderr,
        )
        sys.exit(1)

    extracted_path = sys.argv[1]
    meta_path = sys.argv[2] if len(sys.argv) >= 3 else None

    try:
        out_path = main_render(extracted_path, meta_path)
        print(f"Workflow written to: {out_path}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
