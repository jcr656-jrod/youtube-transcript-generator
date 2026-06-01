"""
YouTube Transcript Generator - Transcription Service
Method 1: youtube-transcript-api (native captions)
Method 2: yt-dlp audio + ffmpeg subtitle extraction
"""

import re
import asyncio
import subprocess
import os
import json
from pathlib import Path
from typing import Dict

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False


def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&
?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Invalid YouTube URL: {url}")


async def get_youtube_native_transcript(video_id: str) -> Dict:
    """Method 1: Native YouTube captions via youtube-transcript-api"""
    if not YOUTUBE_API_AVAILABLE:
        return {"success": False, "method": "youtube_native", "error": "youtube-transcript-api not installed"}

    try:
        print(f"  [Method 1] Trying YouTube native captions for {video_id}...")
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        try:
            transcript = transcript_list.find_transcript(['en'])
        except Exception:
            try:
                transcript = list(transcript_list)[0]
            except Exception:
                return {"success": False, "method": "youtube_native", "error": "No transcripts available"}

        entries = transcript.fetch()
        full_text = ' '.join([entry.get('text', '') for entry in entries])

        print(f"  [Method 1] SUCCESS ({len(full_text)} chars)")
        return {"success": True, "method": "youtube_native", "text": full_text, "cost": 0.0}

    except Exception as e:
        print(f"  [Method 1] FAILED: {str(e)[:100]}")
        return {"success": False, "method": "youtube_native", "error": str(e)}


async def get_ytdlp_subtitle_transcript(video_url: str, video_id: str) -> Dict:
    """Method 2: yt-dlp auto-subtitle extraction (no audio download needed)"""
    try:
        print(f"  [Method 2] Trying yt-dlp subtitle extraction...")
        out_dir = f"/tmp/{video_id}"
        os.makedirs(out_dir, exist_ok=True)

        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "en",
            "--sub-format", "json3",
            "--convert-subs", "srt",
            "-o", f"{out_dir}/%(id)s.%(ext)s",
            video_url
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=60, text=True)

        # Find downloaded subtitle file
        srt_files = list(Path(out_dir).glob("*.srt"))
        vtt_files = list(Path(out_dir).glob("*.vtt"))
        sub_files = srt_files + vtt_files

        if not sub_files:
            print(f"  [Method 2] No subtitle files found. stderr: {result.stderr[:200]}")
            return {"success": False, "method": "ytdlp_subs", "error": "No subtitle files downloaded"}

        sub_file = sub_files[0]
        raw = sub_file.read_text(encoding='utf-8', errors='ignore')

        # Parse SRT - strip timestamps and sequence numbers
        lines = raw.split('
')
        text_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.isdigit():
                continue
            if '-->' in line:
                continue
            # Strip HTML tags
            line = re.sub(r'<[^>]+>', '', line)
            if line:
                text_lines.append(line)

        full_text = ' '.join(text_lines)

        # Cleanup
        import shutil
        shutil.rmtree(out_dir, ignore_errors=True)

        if len(full_text) < 50:
            return {"success": False, "method": "ytdlp_subs", "error": "Subtitle content too short"}

        print(f"  [Method 2] SUCCESS ({len(full_text)} chars)")
        return {"success": True, "method": "ytdlp_subs", "text": full_text, "cost": 0.0}

    except subprocess.TimeoutExpired:
        return {"success": False, "method": "ytdlp_subs", "error": "Timeout"}
    except Exception as e:
        print(f"  [Method 2] FAILED: {str(e)[:100]}")
        return {"success": False, "method": "ytdlp_subs", "error": str(e)}


async def transcribe_video(video_url: str, timeout: int = 300) -> Dict:
    """Main transcription function - tries methods in order"""
    print(f"
[Transcribe] Starting: {video_url}")

    try:
        video_id = extract_video_id(video_url)
        print(f"[Transcribe] Video ID: {video_id}")
    except ValueError as e:
        return {"success": False, "error": str(e), "method": "none"}

    # Method 1: Native captions
    result = await get_youtube_native_transcript(video_id)
    if result["success"]:
        return result

    # Method 2: yt-dlp subtitles
    result = await get_ytdlp_subtitle_transcript(video_url, video_id)
    if result["success"]:
        return result

    return {
        "success": False,
        "error": "Could not transcribe video. The video may have no captions or subtitles available.",
        "method": "all_failed"
    }
