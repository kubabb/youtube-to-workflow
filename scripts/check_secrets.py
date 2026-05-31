#!/usr/bin/env python3
"""
Local pre-push secret scanner.
Run: python scripts/check_secrets.py
Exits 1 if secrets found, 0 if clean.
"""
import re
import sys
from pathlib import Path

SCAN_EXTENSIONS = {".py", ".md", ".json", ".yml", ".yaml", ".txt", ".sh"}

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


def scan_file(path: Path) -> list:
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
            print(f"  {fpath}:{lineno} [{name}] {line[:120]}", file=sys.stderr)
        print(
            "\nFix before pushing. If false positive, add pattern to SKIP_PATHS in scripts/check_secrets.py",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print("Secrets scan: CLEAN")
        sys.exit(0)


if __name__ == "__main__":
    main()
