from templates.workflow_template import (
    WORKFLOW_TEMPLATE,
    render_prerequisites,
    render_tools,
    render_steps,
    render_warnings,
    render_tips,
)


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
    assert "> \u26a0\ufe0f Do not run as root" in result


def test_render_tips_empty():
    assert render_tips([]) == "_None_"


def test_render_tips_items():
    result = render_tips(["Use virtualenv"])
    assert "- Use virtualenv" in result


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
    assert "> \u26a0\ufe0f Never gonna give you up" in result
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
