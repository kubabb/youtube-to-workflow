# Skill: youtube-to-workflow

## Trigger Conditions

Use when user:
- Provides YouTube URL/ID + asks to "extract", "convert", "summarize", "make workflow", "turn into steps"
- Says "extract instructions from", "create workflow from YouTube", "what does this video show"
- URL matches `youtube.com/watch?v=` or `youtu.be/`

## What This Skill Does

Converts YouTube video → structured agent-ready workflow markdown by:
1. Extracting video ID from URL
2. Fetching full transcript via `fetch_transcript.py`
3. LLM extracts: steps, tools, warnings, prerequisites
4. Writes `workflow_VIDEO_ID.md` to current working directory

## Prerequisites Check

Before starting verify:
- Python 3.8+: `python --version`
- Library installed: `pip install youtube-transcript-api`
- Video has captions (auto-generated OK)
- Running locally — YouTube blocks AWS/GCP/Azure IPs

## Execution Steps

### Step 1: Extract Video ID

```
youtube.com/watch?v=VIDEO_ID  →  VIDEO_ID
youtu.be/VIDEO_ID             →  VIDEO_ID
bare VIDEO_ID                 →  use as-is
```

### Step 2: Fetch Transcript

```bash
python "C:\Users\kubar\.claude\skills\youtube-to-workflow\fetch_transcript.py" VIDEO_ID
```

Outputs: `transcript_VIDEO_ID.json` in current dir.

Error handling:
- `TranscriptsDisabled` → inform user, cannot proceed
- `NoTranscriptFound` → add `--lang en` arg
- HTTP 429 / IP block → advise local run or `--proxy http://...`

### Step 3: Extract Structured Data

Read `transcript_VIDEO_ID.json`, send `full_text` field to LLM with this extraction prompt:

```
SYSTEM: You are a workflow extraction specialist. Extract ALL procedural information from
the transcript. Mark ambiguous items with [?]. Be exhaustive — miss nothing actionable.

TRANSCRIPT:
{full_text}

OUTPUT JSON:
{
  "title": "inferred video title/topic",
  "summary": "2-3 sentence summary of what the video teaches",
  "prerequisites": ["tools, accounts, knowledge needed before starting"],
  "tools_and_commands": ["exact CLI commands, tools, software mentioned"],
  "steps": [
    {
      "number": 1,
      "title": "short step title",
      "description": "what to do in detail",
      "command": "exact command or null",
      "expected_output": "what success looks like or null"
    }
  ],
  "warnings": ["gotchas, common mistakes, failure modes"],
  "tips": ["shortcuts, optimizations, best practices"]
}
```

### Step 4: Write Workflow File

Write extracted data as `workflow_VIDEO_ID.md` in current working directory using template:

```markdown
# Workflow: {title}

> **Source:** https://www.youtube.com/watch?v={video_id}
> **Generated:** {date}
> **Transcript:** {language} ({auto-generated or manual}) — {duration}
{if auto_generated}> **Warning:** Auto-generated transcript — verify technical terms manually.{endif}

---

## Summary

{summary}

---

## Prerequisites

{for each}
- [ ] {prerequisite}

---

## Tools & Commands Referenced

{for each}
- `{tool_or_command}`

---

## Step-by-Step Instructions

{for each step}
### Step {number}: {title}

{description}

{if command}
```bash
{command}
```
{endif}

{if expected_output}**Expected output:** {expected_output}{endif}

---

## Warnings & Gotchas

{for each}
> **Warning:** {warning}

## Tips & Optimizations

{for each}
- {tip}

---
*Auto-generated from YouTube transcript. Review all steps before running in production.*
```

### Step 5: Confirm Output

Report to user:
- File path: `{absolute_path}/workflow_VIDEO_ID.md`
- Steps extracted: N
- Warnings found: N
- Any sections with insufficient data → user should supplement manually

## Error Table

| Error | Action |
|---|---|
| No captions | Inform user, suggest enabling auto-captions |
| Video < 2 min | Warn: extracted steps may be sparse |
| Auto-generated, low quality | Add disclaimer in output header |
| Network / IP blocked | Run `fetch_transcript.py` locally with `--proxy` |
| Non-English transcript | Script auto-translates to English; fallback: inform user |
| Transcript > 50k tokens | Chunk `snippets` into thirds, extract per chunk, merge steps |

## Multi-Agent Compatibility

| Agent | Location |
|---|---|
| Claude Code | `~/.claude/skills/youtube-to-workflow/SKILL.md` (auto-loaded) |
| Cursor | `.cursor/rules/youtube-to-workflow.mdc` |
| Windsurf | `.windsurf/rules/youtube-to-workflow.md` |
| Codex CLI | `~/.codex/skills/youtube-to-workflow.md` |
| Gemini CLI | Embed in `GEMINI.md` |

Python script is agent-agnostic — all agents run `python fetch_transcript.py VIDEO_ID` as shell command.
