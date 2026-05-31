# youtube-to-workflow

Claude Code skill that converts any YouTube tutorial into a structured workflow `.md` file.

**Pipeline:** YouTube URL → transcript JSON → LLM extracts structured data → Python renders `.md`

---

## Install

```bash
# 1. Clone into Claude skills directory
git clone https://github.com/kubabb/youtube-to-workflow.git ~/.claude/skills/youtube-to-workflow

# 2. Install Python dependencies
pip install -r ~/.claude/skills/youtube-to-workflow/requirements.txt
```

### Optional: Context7 MCP (improves extraction quality)

Get a free key at https://context7.com, then add to `~/.claude/settings.json`:

```json
"mcpServers": {
  "context7": {
    "command": "npx",
    "args": ["-y", "@upstash/context7-mcp", "--api-key", "YOUR_KEY_HERE"]
  }
}
```

> ⚠️ Never commit your API key. It belongs in `~/.claude/settings.json`, not in this repo.

---

## Usage

Paste any YouTube URL in a Claude Code session:

```
Extract a workflow from https://www.youtube.com/watch?v=VIDEO_ID
```

Claude will:
1. Fetch the transcript → `transcript_VIDEO_ID.json`
2. Extract structured steps, tools, warnings → `extracted_VIDEO_ID.json`
3. Render → `workflow_VIDEO_ID.md` in your current directory

### Manual usage

```bash
# Stage 1: fetch transcript
python ~/.claude/skills/youtube-to-workflow/fetch_transcript.py https://www.youtube.com/watch?v=VIDEO_ID

# Stage 2: render (after LLM saves extracted_VIDEO_ID.json)
python ~/.claude/skills/youtube-to-workflow/generate_workflow.py extracted_VIDEO_ID.json transcript_VIDEO_ID.json
```

---

## Notes

- YouTube blocks cloud/VPN IPs — run locally or use `--proxy http://...`
- `transcript_*.json` and `extracted_*.json` are gitignored — safe to leave in working dir
- Long videos (>60 min) are summarized before extraction to fit context window
- Non-English transcripts: Claude warns you and auto-translates to English

---

## Security

- API keys are gitignored — never commit them
- CI runs [Gitleaks](https://github.com/gitleaks/gitleaks) + a Python pattern scanner on every push
- Run locally before pushing: `python scripts/check_secrets.py`

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Implementation Plan

See [`docs/superpowers/plans/2026-05-31-youtube-to-workflow.md`](docs/superpowers/plans/2026-05-31-youtube-to-workflow.md) for the full task-by-task implementation plan (intended for agentic execution).
