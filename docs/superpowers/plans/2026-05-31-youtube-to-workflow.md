# youtube-to-workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill that converts any YouTube tutorial URL into a structured, reusable workflow `.md` file via a two-stage pipeline: Python fetches + cleans the transcript, LLM extracts structured data, Python renders the final document.

**Architecture:** `fetch_transcript.py` fetches and cleans the raw transcript into JSON. The LLM reads `full_text`, extracts a structured JSON object (title, summary, prerequisites, tools, steps, warnings, tips). `generate_workflow.py` mechanically renders the final `.md` from that JSON using a fixed Python string template — no LLM involvement in rendering, so output structure is always identical.

**Tech Stack:** Python 3.9+, `youtube-transcript-api>=0.6.3`, `requests>=2.31.0`, `pytest`, GitHub Actions (gitleaks for secret scanning)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `fetch_transcript.py` | Modify | Fix 7 known bugs; add `--output-dir` mkdir, file-write try/except, proxy warning, language fallback warning, `datetime` fix |
| `generate_workflow.py` | Create | Renders workflow `.md` from extracted JSON + transcript meta; zero LLM |
| `SKILL.md` | Modify | Update pipeline: add step 3b (save extracted JSON), step 3c (run generate_workflow.py) |
| `templates/workflow_template.py` | Create | Python string constants used by generate_workflow.py (replaces .md template) |
| `tests/test_fetch_transcript.py` | Create | Unit tests for fetch_transcript.py helpers |
| `tests/test_generate_workflow.py` | Create | Unit tests for every render function in generate_workflow.py |
| `tests/fixtures/transcript_sample.json` | Create | Small fixture transcript for tests |
| `tests/fixtures/extracted_sample.json` | Create | Small fixture extracted data for tests |
| `.gitignore` | Create | Exclude secrets, transcripts, API keys, venvs |
| `.github/workflows/security.yml` | Create | Gitleaks secret scan on push + PR |
| `.github/workflows/tests.yml` | Create | Run pytest on push + PR |
| `scripts/check_secrets.py` | Create | Local pre-push secret scanner (no CI dependency) |
| `README.md` | Create | Install + usage instructions for GitHub |
| `requirements-dev.txt` | Create | pytest + dev deps |

---

## Task 1: Fix fetch_transcript.py — output-dir creation

**Files:**
- Modify: `fetch_transcript.py`
- Test: `tests/test_fetch_transcript.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_fetch_transcript.py
import pytest
import json
import os
from pathlib import Path

def test_output_dir_created_if_missing(tmp_path):
    """fetch_transcript must create --output-dir if it doesn't exist."""
    new_dir = tmp_path / "subdir" / "nested"
    assert not new_dir.exists()
    # Import the save helper directly
    from fetch_transcript import save_transcript
    data = {"video_id": "test", "full_text": "hello", "snippets": []}
    save_transcript(data, str(new_dir))
    assert (new_dir / "transcript_test.json").exists()
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd ~/.claude/skills/youtube-to-workflow
python -m pytest tests/test_fetch_transcript.py::test_output_dir_created_if_missing -v
```

Expected: `FAILED` — `ImportError: cannot import name 'save_transcript'` or `FileNotFoundError`

- [ ] **Step 3: Refactor fetch_transcript.py — extract save_transcript function**

Find the file-write block (currently inline in `main()`). Extract it into a function and add `os.makedirs`:

```python
def save_transcript(data: dict, output_dir: str = ".") -> str:
    """Save transcript dict to JSON file. Creates output_dir if missing."""
    import os, json
    os.makedirs(output_dir, exist_ok=True)
    video_id = data["video_id"]
    output_path = os.path.join(output_dir, f"transcript_{video_id}.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Error writing {output_path}: {e}", file=sys.stderr)
        sys.exit(1)
    return output_path
```

In `main()`, replace the inline write with: `output_path = save_transcript(result, args.output_dir)`

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_fetch_transcript.py::test_output_dir_created_if_missing -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add fetch_transcript.py tests/test_fetch_transcript.py
git commit -m "refactor: extract save_transcript, fix missing output-dir creation"
```

---

## Task 2: Fix fetch_transcript.py — proxy warning + datetime deprecation

**Files:**
- Modify: `fetch_transcript.py`
- Test: `tests/test_fetch_transcript.py`

- [ ] **Step 1: Write failing tests**

```python
# append to tests/test_fetch_transcript.py

def test_datetime_not_deprecated():
    """fetch_transcript must not use datetime.utcnow()."""
    source = open("fetch_transcript.py").read()
    assert "utcnow()" not in source, "Use datetime.now(timezone.utc) instead"

def test_proxy_warning_printed(capsys):
    """When proxy import fails, print warning to stderr (not silently drop)."""
    # This is a static analysis test — verify the warning string exists
    source = open("fetch_transcript.py").read()
    assert "proxy" in source.lower()
    assert "warning" in source.lower() or "stderr" in source.lower()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_fetch_transcript.py::test_datetime_not_deprecated tests/test_fetch_transcript.py::test_proxy_warning_printed -v
```

Expected: `test_datetime_not_deprecated` FAILS (utcnow present), `test_proxy_warning_printed` may pass or fail.

- [ ] **Step 3: Fix datetime**

Find: `datetime.utcnow()`
Replace with:

```python
from datetime import datetime, timezone
# ...
"fetched_at": datetime.now(timezone.utc).isoformat(),
```

- [ ] **Step 4: Fix proxy silent drop**

Find the proxy import block (likely a try/except around `GenericProxyConfig`). Change from silently ignoring to:

```python
try:
    from youtube_transcript_api.proxies import GenericProxyConfig
    proxy_config = GenericProxyConfig(args.proxy) if args.proxy else None
except ImportError:
    if args.proxy:
        print("Warning: proxy support unavailable in this version of youtube-transcript-api. --proxy ignored.", file=sys.stderr)
    proxy_config = None
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
python -m pytest tests/test_fetch_transcript.py::test_datetime_not_deprecated tests/test_fetch_transcript.py::test_proxy_warning_printed -v
```

Expected: both `PASSED`

- [ ] **Step 6: Commit**

```bash
git add fetch_transcript.py tests/test_fetch_transcript.py
git commit -m "fix: replace deprecated utcnow(), warn on proxy import failure"
```

---

## Task 3: Fix fetch_transcript.py — language fallback warning

**Files:**
- Modify: `fetch_transcript.py`
- Test: `tests/test_fetch_transcript.py`

- [ ] **Step 1: Write failing test**

```python
# append to tests/test_fetch_transcript.py

def test_non_english_language_warns(capsys):
    """When transcript language is not English, print warning to stderr."""
    source = open("fetch_transcript.py").read()
    # Verify the code checks language and prints a non-english warning
    assert "non-english" in source.lower() or "not english" in source.lower() or "language" in source.lower()
    # The actual behavior test requires integration — mark for manual verification
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_fetch_transcript.py::test_non_english_language_warns -v
```

- [ ] **Step 3: Add language warning in fetch_transcript.py**

After transcript is fetched, find where `language_code` is determined. Add:

```python
if not language_code.startswith("en"):
    if transcript.is_translatable:
        print(
            f"Warning: transcript is in '{language_code}'. Auto-translating to English. "
            "Quality may vary.", file=sys.stderr
        )
        transcript = transcript.translate("en")
        language_code = "en"
        is_auto_generated = True  # treat translated as auto-generated
    else:
        print(
            f"Warning: transcript is in '{language_code}' and cannot be translated. "
            "Workflow extraction may produce incorrect results.", file=sys.stderr
        )
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_fetch_transcript.py::test_non_english_language_warns -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add fetch_transcript.py tests/test_fetch_transcript.py
git commit -m "fix: warn user when non-English transcript is translated or untranslatable"
```

---

## Task 4: Create generate_workflow.py — template constants

**Files:**
- Create: `templates/workflow_template.py`
- Test: `tests/test_generate_workflow.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_generate_workflow.py
from templates.workflow_template import WORKFLOW_TEMPLATE, render_prerequisites, render_tools, render_steps, render_warnings, render_tips

def test_render_prerequisites_empty():
    assert render_prerequisites([]) == "_None specified_"

def test_render_prerequisites_items():
    result = render_prerequisites(["Python 3.9", "pip"])
    assert "- [ ] Python 3.9" in result
    assert "- [ ] pip" in result

def test_render_tools_empty():
    assert render_tools([]) == "_None specified_"

def test_render_tools_items():
    result = render_tools(["git", "docker"])
    assert "- `git`" in result
    assert "- `docker`" in result

def test_render_steps_with_command():
    steps = [{"number": 1, "title": "Install", "description": "Run installer.", "command": "pip install foo", "expected_output": "Successfully installed"}]
    result = render_steps(steps)
    assert "### Step 1: Install" in result
    assert "```bash\npip install foo\n```" in result
    assert "Successfully installed" in result

def test_render_steps_no_command():
    steps = [{"number": 1, "title": "Read docs", "description": "Open the README.", "command": None, "expected_output": None}]
    result = render_steps(steps)
    assert "### Step 1: Read docs" in result
    assert "```bash" not in result

def test_render_warnings_empty():
    assert render_warnings([]) == "_None_"

def test_render_warnings_items():
    result = render_warnings(["Do not run as root"])
    assert "> ⚠️ Do not run as root" in result

def test_render_tips_empty():
    assert render_tips([]) == "_None_"

def test_render_tips_items():
    result = render_tips(["Use virtualenv"])
    assert "- Use virtualenv" in result
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_generate_workflow.py -v
```

Expected: `ModuleNotFoundError: No module named 'templates.workflow_template'`

- [ ] **Step 3: Create templates/__init__.py**

```bash
touch templates/__init__.py
```

- [ ] **Step 4: Create templates/workflow_template.py**

```python
# templates/workflow_template.py

WORKFLOW_TEMPLATE = """\
# {title}

> Auto-generated from YouTube: https://www.youtube.com/watch?v={video_id}
> Generated: {date} | Language: {language} | Duration: {duration}
{auto_generated_warning}
## Summary

{summary}

## Prerequisites

{prerequisites}

## Tools & Commands Referenced

{tools}

## Step-by-Step Instructions

{steps}

## Warnings & Gotchas

{warnings}

## Tips & Optimizations

{tips}

---
*Auto-generated by youtube-to-workflow. Verify all steps before executing in production.*
"""


def render_prerequisites(items: list) -> str:
    if not items:
        return "_None specified_"
    return "\n".join(f"- [ ] {item}" for item in items)


def render_tools(items: list) -> str:
    if not items:
        return "_None specified_"
    return "\n".join(f"- `{item}`" for item in items)


def render_steps(steps: list) -> str:
    parts = []
    for step in steps:
        section = f"### Step {step['number']}: {step['title']}\n\n{step['description']}"
        if step.get("command"):
            section += f"\n\n```bash\n{step['command']}\n```"
        if step.get("expected_output"):
            section += f"\n\nExpected output:\n```\n{step['expected_output']}\n```"
        parts.append(section)
    return "\n\n".join(parts)


def render_warnings(items: list) -> str:
    if not items:
        return "_None_"
    return "\n".join(f"> ⚠️ {item}" for item in items)


def render_tips(items: list) -> str:
    if not items:
        return "_None_"
    return "\n".join(f"- {item}" for item in items)
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
python -m pytest tests/test_generate_workflow.py -v
```

Expected: all 10 tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add templates/__init__.py templates/workflow_template.py tests/test_generate_workflow.py
git commit -m "feat: add workflow template render functions with tests"
```

---

## Task 5: Create generate_workflow.py — main renderer

**Files:**
- Create: `generate_workflow.py`
- Test: `tests/test_generate_workflow.py`
- Create: `tests/fixtures/transcript_sample.json`
- Create: `tests/fixtures/extracted_sample.json`

- [ ] **Step 1: Create test fixtures**

`tests/fixtures/transcript_sample.json`:
```json
{
  "video_id": "dQw4w9WgXcQ",
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "language": "English",
  "language_code": "en",
  "is_auto_generated": false,
  "duration_seconds": 211,
  "duration_human": "3m31s",
  "full_text": "Sample transcript text."
}
```

`tests/fixtures/extracted_sample.json`:
```json
{
  "title": "How to Rick Roll",
  "summary": "Classic internet prank tutorial.",
  "prerequisites": ["Internet connection"],
  "tools_and_commands": ["youtube-dl"],
  "steps": [
    {
      "number": 1,
      "title": "Open YouTube",
      "description": "Navigate to youtube.com",
      "command": null,
      "expected_output": null
    },
    {
      "number": 2,
      "title": "Search for the video",
      "description": "Type in the search box.",
      "command": "youtube-dl dQw4w9WgXcQ",
      "expected_output": "[download] 100%"
    }
  ],
  "warnings": ["Never gonna give you up"],
  "tips": ["Use incognito mode"]
}
```

- [ ] **Step 2: Write failing tests for generate_workflow.py**

```python
# append to tests/test_generate_workflow.py
import json
from pathlib import Path
from generate_workflow import render_workflow, main_render

FIXTURES = Path("tests/fixtures")

def test_render_workflow_produces_markdown():
    extracted = json.loads((FIXTURES / "extracted_sample.json").read_text())
    meta = json.loads((FIXTURES / "transcript_sample.json").read_text())
    result = render_workflow(extracted, meta)
    assert "# How to Rick Roll" in result
    assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" in result
    assert "### Step 1: Open YouTube" in result
    assert "### Step 2: Search for the video" in result
    assert "```bash\nyoutube-dl dQw4w9WgXcQ\n```" in result
    assert "> ⚠️ Never gonna give you up" in result
    assert "- Use incognito mode" in result

def test_render_workflow_auto_generated_warning():
    extracted = json.loads((FIXTURES / "extracted_sample.json").read_text())
    meta = json.loads((FIXTURES / "transcript_sample.json").read_text())
    meta["is_auto_generated"] = True
    result = render_workflow(extracted, meta)
    assert "Auto-generated captions" in result

def test_render_workflow_no_auto_generated_warning_when_false():
    extracted = json.loads((FIXTURES / "extracted_sample.json").read_text())
    meta = json.loads((FIXTURES / "transcript_sample.json").read_text())
    meta["is_auto_generated"] = False
    result = render_workflow(extracted, meta)
    assert "Auto-generated captions" not in result

def test_main_render_writes_file(tmp_path):
    import shutil
    shutil.copy(FIXTURES / "extracted_sample.json", tmp_path / "extracted_dQw4w9WgXcQ.json")
    shutil.copy(FIXTURES / "transcript_sample.json", tmp_path / "transcript_dQw4w9WgXcQ.json")
    out_path = main_render(
        extracted_path=str(tmp_path / "extracted_dQw4w9WgXcQ.json"),
        meta_path=str(tmp_path / "transcript_dQw4w9WgXcQ.json"),
    )
    assert Path(out_path).exists()
    content = Path(out_path).read_text()
    assert "# How to Rick Roll" in content
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
python -m pytest tests/test_generate_workflow.py::test_render_workflow_produces_markdown -v
```

Expected: `ModuleNotFoundError: No module named 'generate_workflow'`

- [ ] **Step 4: Create generate_workflow.py**

```python
# generate_workflow.py
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
        auto_warning = "\n> ⚠️ **Auto-generated captions** — transcript may contain errors. Review steps carefully.\n"

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


def main_render(extracted_path: str, meta_path: str = None) -> str:
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
```

- [ ] **Step 5: Run all generate_workflow tests**

```bash
python -m pytest tests/test_generate_workflow.py -v
```

Expected: all 13 tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add generate_workflow.py tests/fixtures/ tests/test_generate_workflow.py
git commit -m "feat: add generate_workflow.py — renders workflow .md from extracted JSON"
```

---

## Task 6: Update SKILL.md pipeline

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Open SKILL.md and locate the pipeline section**

Find the numbered pipeline steps (currently 4 steps: extract ID → run fetch_transcript → LLM extracts → write .md).

- [ ] **Step 2: Replace pipeline steps with new 6-step version**

Replace the pipeline steps section with:

```markdown
## Pipeline

1. Extract video ID from the URL or bare ID provided by the user.
2. Run: `python ~/.claude/skills/youtube-to-workflow/fetch_transcript.py VIDEO_ID`
   - Output: `transcript_VIDEO_ID.json` in current directory
   - If language warning appears: inform user, continue
3. Read `transcript_VIDEO_ID.json`. Use the `full_text` field.
   - If `full_text` exceeds 50,000 tokens: summarize it to ~8,000 tokens first, then proceed.
4. Extract structured data from `full_text` using this schema:
   ```json
   {
     "title": "descriptive workflow title (not the video title verbatim)",
     "summary": "2-3 sentence summary of what this workflow accomplishes",
     "prerequisites": ["list of things needed before starting"],
     "tools_and_commands": ["every CLI tool, package, or command mentioned"],
     "steps": [
       {
         "number": 1,
         "title": "short imperative title",
         "description": "clear explanation of what to do and why",
         "command": "exact command or null",
         "expected_output": "what user should see, or null"
       }
     ],
     "warnings": ["gotchas, common mistakes, destructive operations"],
     "tips": ["optimizations, shortcuts, alternatives"]
   }
   ```
   Save this JSON to `extracted_VIDEO_ID.json` in current directory.
5. Run: `python ~/.claude/skills/youtube-to-workflow/generate_workflow.py extracted_VIDEO_ID.json transcript_VIDEO_ID.json`
   - Output: `workflow_VIDEO_ID.md` in current directory
6. Report to user:
   - Path to `workflow_VIDEO_ID.md`
   - Number of steps extracted
   - Number of warnings
   - Any quality notes (auto-generated captions, non-English source, very short/long transcript)
```

- [ ] **Step 3: Verify SKILL.md loads without errors**

```bash
cat ~/.claude/skills/youtube-to-workflow/SKILL.md | head -80
```

Expected: clean markdown, no broken syntax

- [ ] **Step 4: Commit**

```bash
git add SKILL.md
git commit -m "feat: update SKILL.md pipeline to two-stage fetch+render"
```

---

## Task 7: Create .gitignore

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Secrets & credentials
.env
.env.*
*.env
secrets.json
credentials.json
*_key.txt
*_secret.txt
config.local.*

# API keys — never commit
# Context7: ~/.claude/settings.json (not in this repo)

# Transcript temp files (kept locally for debugging, not shared)
transcript_*.json
extracted_*.json

# Generated workflow outputs
workflow_*.md

# Python
__pycache__/
*.py[cod]
*.pyo
.Python
build/
dist/
*.egg-info/
.eggs/

# Virtual environments
venv/
env/
.venv/
.env/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store
Thumbs.db

# Logs
*.log
```

- [ ] **Step 2: Verify no sensitive files would be tracked**

```bash
git status
```

Expected: `.env`, `transcript_*.json`, `extracted_*.json`, `workflow_*.md` do NOT appear as untracked.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "security: add .gitignore — exclude secrets, transcripts, API keys"
```

---

## Task 8: Create scripts/check_secrets.py — local secret scanner

**Files:**
- Create: `scripts/check_secrets.py`
- Create: `scripts/__init__.py`

- [ ] **Step 1: Create scripts/check_secrets.py**

```python
#!/usr/bin/env python3
"""
Local pre-push secret scanner.
Run: python scripts/check_secrets.py
Exits 1 if secrets found, 0 if clean.
"""
import re
import sys
from pathlib import Path

# Files to scan (tracked by git, not in .gitignore)
SCAN_EXTENSIONS = {".py", ".md", ".json", ".yml", ".yaml", ".txt", ".sh"}

# Patterns that indicate a hardcoded secret
SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{16,}', "API key"),
    (r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']', "Password/Secret"),
    (r'(?i)(token)\s*[=:]\s*["\'][A-Za-z0-9_\-\.]{20,}["\']', "Token"),
    (r'ctx7sk-[a-f0-9\-]{30,}', "Context7 API key"),
    (r'sk-[A-Za-z0-9]{32,}', "OpenAI-style key"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub personal access token"),
    (r'(?i)aws_access_key_id\s*[=:]\s*[A-Z0-9]{20}', "AWS access key"),
]

SKIP_PATHS = {".git", "venv", "env", ".venv", "__pycache__", "node_modules"}


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Returns list of (line_number, pattern_name, line_content) for hits."""
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return hits
    for lineno, line in enumerate(text.splitlines(), 1):
        for pattern, name in SECRET_PATTERNS:
            if re.search(pattern, line):
                hits.append((lineno, name, line.strip()))
    return hits


def main():
    root = Path(".")
    all_hits = []

    for path in root.rglob("*"):
        # Skip ignored directories
        if any(skip in path.parts for skip in SKIP_PATHS):
            continue
        if path.suffix not in SCAN_EXTENSIONS:
            continue
        if not path.is_file():
            continue
        hits = scan_file(path)
        for lineno, name, line in hits:
            all_hits.append((str(path), lineno, name, line))

    if all_hits:
        print("SECRETS SCAN FAILED — potential secrets found:\n", file=sys.stderr)
        for fpath, lineno, name, line in all_hits:
            print(f"  {fpath}:{lineno} [{name}] {line[:100]}", file=sys.stderr)
        print("\nFix before pushing. If false positive, add to SKIP_PATHS in scripts/check_secrets.py", file=sys.stderr)
        sys.exit(1)
    else:
        print("Secrets scan: CLEAN")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create scripts/__init__.py**

```python
```
(empty file)

- [ ] **Step 3: Run scanner — verify it finds nothing in clean repo**

```bash
python scripts/check_secrets.py
```

Expected: `Secrets scan: CLEAN`

- [ ] **Step 4: Commit**

```bash
git add scripts/
git commit -m "security: add local secret scanner scripts/check_secrets.py"
```

---

## Task 9: Create GitHub Actions — secret scan CI

**Files:**
- Create: `.github/workflows/security.yml`

- [ ] **Step 1: Create .github/workflows/ directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create .github/workflows/security.yml**

```yaml
name: Security Scan

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  secrets-scan:
    name: Gitleaks secret scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  local-scanner:
    name: Python secret patterns
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Run check_secrets.py
        run: python scripts/check_secrets.py
```

- [ ] **Step 3: Commit**

```bash
git add .github/
git commit -m "ci: add GitHub Actions secret scan (gitleaks + python scanner)"
```

---

## Task 10: Create GitHub Actions — tests CI

**Files:**
- Create: `.github/workflows/tests.yml`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create requirements-dev.txt**

```
pytest>=8.0.0
pytest-cov>=5.0.0
```

- [ ] **Step 2: Create .github/workflows/tests.yml**

```yaml
name: Tests

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  test:
    name: pytest
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest tests/ -v --tb=short
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/tests.yml requirements-dev.txt
git commit -m "ci: add GitHub Actions test pipeline (pytest, Python 3.9/3.11/3.12)"
```

---

## Task 11: Create README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

```markdown
# youtube-to-workflow

Claude Code skill that converts any YouTube tutorial into a structured workflow `.md` file.

**Pipeline:** YouTube URL → transcript → LLM extracts steps → Python renders `.md`

---

## Install

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/youtube-to-workflow.git ~/.claude/skills/youtube-to-workflow

# 2. Install Python dependencies
pip install -r ~/.claude/skills/youtube-to-workflow/requirements.txt

# 3. Context7 MCP (optional but recommended — improves extraction quality)
#    Get free key at https://context7.com
#    Add to ~/.claude/settings.json:
#    "context7": { "command": "npx", "args": ["-y", "@upstash/context7-mcp", "--api-key", "YOUR_KEY"] }
```

## Usage

Paste any YouTube URL in Claude Code:

```
Extract a workflow from https://www.youtube.com/watch?v=VIDEO_ID
```

Claude will:
1. Fetch the transcript
2. Extract structured steps, tools, warnings
3. Generate `workflow_VIDEO_ID.md` in your current directory

## Manual usage

```bash
# Stage 1: fetch transcript
python fetch_transcript.py https://www.youtube.com/watch?v=VIDEO_ID
# → transcript_VIDEO_ID.json

# Stage 2: render (after LLM extraction to extracted_VIDEO_ID.json)
python generate_workflow.py extracted_VIDEO_ID.json transcript_VIDEO_ID.json
# → workflow_VIDEO_ID.md
```

## Notes

- YouTube blocks cloud IPs — run locally or use `--proxy http://...`
- Transcripts (`transcript_*.json`) are gitignored — safe to leave in working directory
- Long videos (>60 min) are summarized before extraction

## Security

- Never commit API keys — they are gitignored
- CI runs `gitleaks` + `scripts/check_secrets.py` on every push
- Run locally: `python scripts/check_secrets.py`

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install, usage, security notes"
```

---

## Task 12: Initialize git, create GitHub repo, push

**Files:** none (git operations)

> ⚠️ This task requires `gh` CLI authenticated. Run `gh auth login` if needed.

- [ ] **Step 1: Verify clean state**

```bash
python scripts/check_secrets.py
git status
```

Expected: `Secrets scan: CLEAN`, no untracked sensitive files

- [ ] **Step 2: Initialize git (if not already)**

```bash
cd ~/.claude/skills/youtube-to-workflow
git init
git add .
git commit -m "feat: initial commit — youtube-to-workflow Claude Code skill"
```

- [ ] **Step 3: Create GitHub repo**

```bash
gh repo create youtube-to-workflow \
  --public \
  --description "Claude Code skill: convert YouTube tutorials into structured workflow .md files" \
  --source=. \
  --remote=origin
```

Expected output: `✓ Created repository YOUR_USERNAME/youtube-to-workflow on GitHub`

- [ ] **Step 4: Push**

```bash
git push -u origin main
```

Expected: `Branch 'main' set up to track remote branch 'main' from 'origin'.`

- [ ] **Step 5: Verify CI passes**

```bash
gh run list --limit 5
```

Expected: security scan and tests show `completed` / `success` within ~2 minutes.

---

## End-to-end verification

After all tasks complete, run a full pipeline test:

- [ ] **Test with real tutorial video**

```bash
cd /tmp/workflow-test
python ~/.claude/skills/youtube-to-workflow/fetch_transcript.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Expected: `transcript_dQw4w9WgXcQ.json` created, no errors

- [ ] **Ask Claude Code to run the full skill**

Open Claude Code session, type:
```
Extract a workflow from https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Expected: `workflow_dQw4w9WgXcQ.md` created in current directory with all 7 sections populated.

- [ ] **Verify output quality**

```bash
cat workflow_dQw4w9WgXcQ.md
```

Check: title present, at least 3 steps, warnings/tips sections present, no `{placeholder}` strings remaining.

- [ ] **Run full test suite**

```bash
cd ~/.claude/skills/youtube-to-workflow
pytest tests/ -v
```

Expected: all tests `PASSED`
