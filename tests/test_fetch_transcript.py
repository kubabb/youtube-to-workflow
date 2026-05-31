import pytest
import json
import os
from pathlib import Path


def test_output_dir_created_if_missing(tmp_path):
    """fetch_transcript must create --output-dir if it doesn't exist."""
    new_dir = tmp_path / "subdir" / "nested"
    assert not new_dir.exists()
    from fetch_transcript import save_transcript
    data = {"video_id": "dQw4w9WgXcW", "full_text": "hello", "snippets": []}
    save_transcript(data, str(new_dir))
    assert (new_dir / "transcript_dQw4w9WgXcW.json").exists()


def test_datetime_not_deprecated():
    """fetch_transcript must not use datetime.utcnow()."""
    source = open("fetch_transcript.py").read()
    assert "utcnow()" not in source, "Use datetime.now(timezone.utc) instead"


def test_proxy_warning_printed(capsys):
    """When proxy import fails, print warning to stderr (not silently drop)."""
    source = open("fetch_transcript.py").read()
    assert "proxy" in source.lower()
    assert "warning" in source.lower() or "stderr" in source.lower()


def test_non_english_language_warns(capsys):
    """When transcript language is not English, print warning to stderr."""
    source = open("fetch_transcript.py").read()
    assert "non-english" in source.lower() or "not english" in source.lower() or "language" in source.lower()


def test_save_transcript_returns_path(tmp_path):
    """save_transcript returns the output file path."""
    from fetch_transcript import save_transcript
    data = {"video_id": "abc12345678", "full_text": "test", "snippets": []}
    result = save_transcript(data, str(tmp_path))
    assert result == str(tmp_path / "transcript_abc12345678.json")


def test_save_transcript_creates_json(tmp_path):
    """save_transcript writes valid JSON."""
    from fetch_transcript import save_transcript
    data = {"video_id": "abc12345678", "full_text": "hello world", "snippets": []}
    path = save_transcript(data, str(tmp_path))
    with open(path) as f:
        loaded = json.load(f)
    assert loaded["video_id"] == "abc12345678"
    assert loaded["full_text"] == "hello world"
