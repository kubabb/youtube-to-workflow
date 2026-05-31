#!/usr/bin/env python3
"""
fetch_transcript.py
Usage: python fetch_transcript.py <video_id_or_url> [--lang en de] [--proxy http://...] [--output-dir .]
Output: transcript_<video_id>.json in output dir, JSON also printed to stdout
"""

import sys
import json
import re
import os
import argparse
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

_VIDEO_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')
_YOUTUBE_NETLOC = frozenset({
    'youtube.com', 'www.youtube.com', 'm.youtube.com',
    'youtu.be', 'www.youtu.be',
})
_PROXY_RE = re.compile(r'^https?://\S+$')


def extract_video_id(input_str: str) -> str:
    input_str = input_str.strip()

    # Bare 11-char video ID
    if _VIDEO_ID_RE.match(input_str):
        return input_str

    # URL: parse and validate domain before extracting ID
    try:
        parsed = urlparse(input_str if '://' in input_str else 'https://' + input_str)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("URL must use http or https")
        netloc = parsed.netloc.lower()
        if netloc not in _YOUTUBE_NETLOC:
            raise ValueError(f"Not a YouTube URL (domain: {netloc!r})")
        if 'youtu.be' in netloc:
            vid = parsed.path.lstrip('/').split('/')[0]
        else:
            vids = parse_qs(parsed.query).get('v', [])
            if not vids:
                raise ValueError("Missing ?v= parameter in YouTube URL")
            vid = vids[0]
        if not _VIDEO_ID_RE.match(vid):
            raise ValueError(f"Invalid video ID format: {vid!r}")
        return vid
    except ValueError:
        raise
    except Exception:
        pass

    raise ValueError(f"Cannot extract video ID from: {input_str!r}")


def fetch_transcript(video_id: str, languages: list = None, http_proxy: str = None) -> dict:
    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            TranscriptsDisabled,
            NoTranscriptFound,
        )
    except ImportError:
        print("ERROR: Run: pip install youtube-transcript-api", file=sys.stderr)
        sys.exit(1)

    if languages is None:
        languages = ["en", "en-US", "en-GB"]

    kwargs = {}
    if http_proxy:
        if not _PROXY_RE.match(http_proxy):
            print("ERROR: Invalid proxy URL. Expected http://... or https://...", file=sys.stderr)
            sys.exit(1)
        try:
            from youtube_transcript_api import GenericProxyConfig
            kwargs["proxies"] = GenericProxyConfig(
                http_proxy=http_proxy, https_proxy=http_proxy
            )
        except ImportError:
            print("WARNING: proxy support unavailable in this version of youtube-transcript-api. --proxy ignored.", file=sys.stderr)

    ytt_api = YouTubeTranscriptApi(**kwargs)

    try:
        transcript_list = ytt_api.list(video_id)
    except TranscriptsDisabled:
        print(f"ERROR: Transcripts disabled for {video_id}", file=sys.stderr)
        sys.exit(2)
    except Exception:
        print(f"ERROR: Failed to list transcripts for {video_id}. Check video ID and network.", file=sys.stderr)
        sys.exit(3)

    transcript_obj = None
    try:
        transcript_obj = transcript_list.find_transcript(languages)
    except NoTranscriptFound:
        pass

    if transcript_obj is None:
        available = list(transcript_list)
        if not available:
            print(f"ERROR: No transcripts for {video_id}", file=sys.stderr)
            sys.exit(4)
        transcript_obj = available[0]
        print(f"WARNING: Using fallback language: {transcript_obj.language} ({transcript_obj.language_code})", file=sys.stderr)

    # Auto-translate non-English to English
    if transcript_obj.language_code not in ("en", "en-US", "en-GB", "en-CA", "en-AU"):
        if transcript_obj.is_translatable:
            print(f"INFO: Translating {transcript_obj.language_code} → en", file=sys.stderr)
            try:
                transcript_obj = transcript_obj.translate("en")
            except Exception as e:
                print(f"WARNING: Translation failed ({e}), using original", file=sys.stderr)

    is_generated = transcript_obj.is_generated
    actual_language = transcript_obj.language
    actual_language_code = transcript_obj.language_code

    try:
        fetched = transcript_obj.fetch()
    except Exception as e:
        print(f"ERROR fetching content: {e}", file=sys.stderr)
        sys.exit(5)

    snippets = []
    full_text_parts = []
    for snippet in fetched:
        # v1.x: FetchedTranscriptSnippet object (not dict)
        text = snippet.text if hasattr(snippet, "text") else snippet["text"]
        start = snippet.start if hasattr(snippet, "start") else snippet["start"]
        duration = snippet.duration if hasattr(snippet, "duration") else snippet["duration"]
        snippets.append({"text": text, "start": round(start, 2), "duration": round(duration, 2)})
        full_text_parts.append(text)

    full_text = " ".join(full_text_parts)
    # Strip ASR noise markers
    full_text = re.sub(r"\[Music\]", "", full_text, flags=re.IGNORECASE)
    full_text = re.sub(r"\[Applause\]", "", full_text, flags=re.IGNORECASE)
    full_text = re.sub(r"\[.*?\]", "", full_text)
    full_text = re.sub(r"\s+", " ", full_text).strip()

    total_seconds = 0
    if snippets:
        last = snippets[-1]
        total_seconds = int(last["start"] + last["duration"])
    minutes, seconds = divmod(total_seconds, 60)

    return {
        "video_id": video_id,
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "language": actual_language,
        "language_code": actual_language_code,
        "is_auto_generated": is_generated,
        "duration_seconds": total_seconds,
        "duration_human": f"{minutes}m {seconds}s",
        "snippet_count": len(snippets),
        "full_text": full_text,
        "snippets": snippets,
    }


def save_transcript(data: dict, output_dir: str = ".") -> str:
    """Save transcript dict to JSON file. Creates output_dir if missing."""
    video_id = data.get("video_id", "")
    if not _VIDEO_ID_RE.match(video_id):
        raise ValueError(f"Invalid video ID: {video_id!r}")

    abs_dir = os.path.abspath(output_dir)
    os.makedirs(abs_dir, exist_ok=True)

    output_path = os.path.join(abs_dir, f"transcript_{video_id}.json")
    abs_output = os.path.abspath(output_path)
    if not abs_output.startswith(abs_dir + os.sep):
        raise ValueError("Output path escapes output_dir")

    try:
        with open(abs_output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        print("Error: Could not write transcript file. Check permissions and disk space.", file=sys.stderr)
        sys.exit(1)
    return abs_output


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube transcript to JSON")
    parser.add_argument("video", help="YouTube video ID or URL")
    parser.add_argument("--lang", nargs="+", default=None, help="Language codes (priority order)")
    parser.add_argument("--proxy", default=None, help="HTTP proxy URL")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.video)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"INFO: Fetching transcript for: {video_id}", file=sys.stderr)

    data = fetch_transcript(video_id, languages=args.lang, http_proxy=args.proxy)

    output_path = save_transcript(data, args.output_dir)

    print(f"INFO: Written → {os.path.abspath(output_path)}", file=sys.stderr)
    print(f"INFO: {data['snippet_count']} snippets | {data['duration_human']} | lang: {data['language']} | auto: {data['is_auto_generated']}", file=sys.stderr)

    # stdout for piping
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
