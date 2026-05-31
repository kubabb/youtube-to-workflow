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
