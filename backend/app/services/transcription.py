"""
YouTube Transcript Generator - Transcription Service
Strategy order:
  1. youtube-transcript-api direct
  2. Webshare premium proxy (if configured)
  3. yt-dlp subtitle extraction (bypasses IP blocks entirely)
  4. Free proxy race
"""

import re
import asyncio
import os
import random
import json
import subprocess
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

PROXY_FETCH_URL = (
    "https://api.proxyscrape.com/v3/free-proxy-list/get"
    "?request=displayproxies&protocol=http&timeout=3000"
    "&country=US,GB,DE,CA&ssl=all&anonymity=elite,anonymous&limit=50"
)
_proxy_cache: List[str] = []
PROXY_TIMEOUT = 8


def extract_video_id(url: str) -> str:
    for pattern in [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)",
    ]:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Invalid YouTube URL: {url}")


def _sync_fetch(video_id: str, proxy_url: Optional[str] = None) -> Optional[str]:
    try:
        if proxy_url:
            cfg = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
            api = YouTubeTranscriptApi(proxy_config=cfg)
        else:
            api = YouTubeTranscriptApi()

        try:
            t = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        except Exception:
            t = api.fetch(video_id)

        snippets = t.snippets if hasattr(t, "snippets") else t
        text = " ".join([
            (s.text if hasattr(s, "text") else s.get("text", ""))
            for s in snippets
        ]).strip()
        return text if len(text) > 50 else None
    except Exception:
        return None


def _ytdlp_fetch(video_id: str) -> Optional[str]:
    """
    Use yt-dlp to download auto-generated or manual subtitles.
    This bypasses youtube-transcript-api's IP restrictions entirely
    because yt-dlp uses different endpoints and supports cookies/user-agents.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            url = f"https://www.youtube.com/watch?v={video_id}"
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-auto-sub",
                "--write-sub",
                "--sub-lang", "en",
                "--sub-format", "json3",
                "--output", f"{tmpdir}/%(id)s",
                "--no-warnings",
                "--quiet",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Find the subtitle file
            import glob
            sub_files = glob.glob(f"{tmpdir}/*.json3")
            if not sub_files:
                # Try vtt format as fallback
                cmd[cmd.index("json3")] = "vtt"
                cmd[cmd.index("--sub-format")] = "--sub-format"
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                vtt_files = glob.glob(f"{tmpdir}/*.vtt")
                if vtt_files:
                    return _parse_vtt(vtt_files[0])
                return None

            # Parse json3 subtitle format
            with open(sub_files[0]) as f:
                data = json.load(f)

            texts = []
            for event in data.get("events", []):
                for seg in event.get("segs", []):
                    t = seg.get("utf8", "").strip()
                    if t and t != "\n":
                        texts.append(t)

            text = " ".join(texts).replace("\n", " ").strip()
            # Clean up yt-dlp artifacts
            text = re.sub(r'\s+', ' ', text).strip()
            return text if len(text) > 50 else None

    except subprocess.TimeoutExpired:
        print("  [S3-ytdlp] Timeout")
        return None
    except FileNotFoundError:
        print("  [S3-ytdlp] yt-dlp not installed")
        return None
    except Exception as e:
        print(f"  [S3-ytdlp] Error: {str(e)[:80]}")
        return None


def _parse_vtt(vtt_path: str) -> Optional[str]:
    """Parse WebVTT subtitle file to plain text."""
    try:
        with open(vtt_path) as f:
            content = f.read()
        # Remove VTT header and timestamps
        lines = content.split('\n')
        texts = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('WEBVTT') or '-->' in line or line.isdigit():
                continue
            # Remove HTML tags
            line = re.sub(r'<[^>]+>', '', line)
            if line:
                texts.append(line)
        text = ' '.join(texts)
        text = re.sub(r'\s+', ' ', text).strip()
        return text if len(text) > 50 else None
    except Exception:
        return None


def _fetch_free_proxies() -> List[str]:
    global _proxy_cache
    try:
        req = urllib.request.urlopen(PROXY_FETCH_URL, timeout=6)
        proxies = [p.strip() for p in req.read().decode().strip().split("\n") if p.strip()]
        random.shuffle(proxies)
        _proxy_cache = proxies
        print(f"  [Proxy] Fetched {len(proxies)} proxies")
        return proxies
    except Exception as e:
        print(f"  [Proxy] Fetch failed: {e} - using cache ({len(_proxy_cache)})")
        return _proxy_cache[:]


def _race_proxies(video_id: str, proxies: List[str], max_workers: int = 8, per_proxy_timeout: int = 8) -> Optional[str]:
    batch = proxies[:16]
    print(f"  [Race] Trying {len(batch)} proxies concurrently ({max_workers} workers)...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_sync_fetch, video_id, f"http://{p}"): p
            for p in batch
        }
        for future in as_completed(futures, timeout=per_proxy_timeout + 2):
            proxy = futures[future]
            try:
                result = future.result(timeout=per_proxy_timeout)
                if result:
                    print(f"  [Race] SUCCESS via {proxy}")
                    return result
            except Exception:
                pass
    return None


async def get_transcript_with_proxy_rotation(video_id: str) -> Dict:
    loop = asyncio.get_event_loop()

    # Strategy 1: Direct
    print(f"  [S1] Direct request...")
    try:
        text = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_fetch, video_id, None),
            timeout=10
        )
        if text:
            print(f"  [S1] SUCCESS direct ({len(text)} chars)")
            return {"success": True, "method": "direct", "text": text, "cost": 0.0}
    except Exception as e:
        print(f"  [S1] Direct failed: {str(e)[:60]}")

    # Strategy 2: Webshare premium proxy
    ws_user = os.getenv("WEBSHARE_PROXY_USERNAME")
    ws_pass = os.getenv("WEBSHARE_PROXY_PASSWORD")
    if ws_user and ws_pass:
        print(f"  [S2] Webshare proxy...")
        try:
            cfg = WebshareProxyConfig(proxy_username=ws_user, proxy_password=ws_pass, retries_when_blocked=2)
            api = YouTubeTranscriptApi(proxy_config=cfg)
            def _ws_fetch():
                try:
                    t = api.fetch(video_id, languages=["en", "en-US"])
                except Exception:
                    t = api.fetch(video_id)
                snippets = t.snippets if hasattr(t, "snippets") else t
                return " ".join([(s.text if hasattr(s, "text") else s.get("text", "")) for s in snippets]).strip()
            text = await asyncio.wait_for(loop.run_in_executor(None, _ws_fetch), timeout=20)
            if text and len(text) > 50:
                print(f"  [S2] SUCCESS via Webshare ({len(text)} chars)")
                return {"success": True, "method": "webshare", "text": text, "cost": 0.0}
        except Exception as e:
            print(f"  [S2] Webshare failed: {str(e)[:60]}")

    # Strategy 3: yt-dlp (best bypass for Railway IP blocks)
    print(f"  [S3] yt-dlp subtitle extraction...")
    try:
        text = await asyncio.wait_for(
            loop.run_in_executor(None, _ytdlp_fetch, video_id),
            timeout=45
        )
        if text:
            print(f"  [S3] SUCCESS via yt-dlp ({len(text)} chars)")
            return {"success": True, "method": "yt-dlp", "text": text, "cost": 0.0}
        else:
            print(f"  [S3] yt-dlp returned no text")
    except Exception as e:
        print(f"  [S3] yt-dlp failed: {str(e)[:60]}")

    # Strategy 4: Free proxy race
    print(f"  [S4] Free proxy race...")
    proxies = await loop.run_in_executor(None, _fetch_free_proxies)
    if proxies:
        try:
            text = await asyncio.wait_for(
                loop.run_in_executor(None, _race_proxies, video_id, proxies),
                timeout=25
            )
            if text:
                return {"success": True, "method": "free_proxy", "text": text, "cost": 0.0}
        except Exception as e:
            print(f"  [S4] Race failed: {str(e)[:60]}")

    return {
        "success": False,
        "method": "all_failed",
        "error": (
            "Could not retrieve transcript after trying direct, yt-dlp, and proxy rotation. "
            "This video may have captions fully disabled. "
            "Add WEBSHARE_PROXY_USERNAME / WEBSHARE_PROXY_PASSWORD to Railway env for premium proxies."
        ),
    }


async def transcribe_video(video_url: str, timeout: int = 300) -> Dict:
    print(f"\n[Transcribe] {video_url}")
    try:
        video_id = extract_video_id(video_url)
        print(f"[Transcribe] ID: {video_id}")
    except ValueError as e:
        return {"success": False, "error": str(e), "method": "none"}
    return await get_transcript_with_proxy_rotation(video_id)
