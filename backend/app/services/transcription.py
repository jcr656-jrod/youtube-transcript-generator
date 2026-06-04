"""
YouTube Transcript Generator - Transcription Service
Strategy order:
  1. youtube-transcript.io API (hosted, bypasses Railway IP blocks, 100 free/mo)
  2. youtube-transcript-api direct (works locally, blocked on Railway)
  3. Webshare premium proxy (if configured)
  4. yt-dlp subtitle extraction
  5. Free proxy race
"""

import re
import asyncio
import os
import random
import json
import subprocess
import tempfile
import glob
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

PROXY_FETCH_URL = (
    "https://api.proxyscrape.com/v3/free-proxy-list/get"
    "?request=displayproxies&protocol=http&timeout=3000"
    "&country=US,GB,DE,CA&ssl=all&anonymity=elite,anonymous&limit=50"
)
_proxy_cache: List[str] = []


def extract_video_id(url: str) -> str:
    for pattern in [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)",
    ]:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Invalid YouTube URL: {url}")


# ── Strategy 1: youtube-transcript.io (hosted API, no IP issues) ─────────────
async def _fetch_via_transcript_io(video_id: str) -> Optional[str]:
    """
    Uses youtube-transcript.io — a hosted service that fetches transcripts
    without Railway IP restrictions. Free tier: 100 requests/month.
    Docs: https://www.youtube-transcript.io/
    """
    api_key = os.getenv("YOUTUBE_TRANSCRIPT_IO_KEY", "")
    try:
        url = f"https://www.youtube-transcript.io/api/transcripts"
        params = {"ids[]": video_id}
        headers = {}
        if api_key:
            headers["Authorization"] = f"Basic {api_key}"

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                print(f"  [S1-io] HTTP {resp.status_code}")
                return None
            data = resp.json()
            # Response: [{ "videoId": "...", "transcripts": [{"text": "...", ...}] }]
            if not data or not isinstance(data, list):
                return None
            item = data[0]
            transcripts = item.get("transcripts", [])
            if not transcripts:
                return None
            text = " ".join(t.get("text", "") for t in transcripts).strip()
            return text if len(text) > 50 else None
    except Exception as e:
        print(f"  [S1-io] Error: {str(e)[:80]}")
        return None


# ── Strategy 2: youtube-transcript-api direct ────────────────────────────────
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


# ── Strategy 4: yt-dlp ───────────────────────────────────────────────────────
def _ytdlp_fetch(video_id: str) -> Optional[str]:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            url = f"https://www.youtube.com/watch?v={video_id}"
            cmd = [
                "yt-dlp", "--skip-download",
                "--write-auto-sub", "--write-sub",
                "--sub-lang", "en",
                "--sub-format", "json3",
                "--output", f"{tmpdir}/%(id)s",
                "--no-warnings", "--quiet",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                url
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            sub_files = glob.glob(f"{tmpdir}/*.json3")
            if not sub_files:
                cmd[cmd.index("json3")] = "vtt"
                subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                vtt_files = glob.glob(f"{tmpdir}/*.vtt")
                if vtt_files:
                    return _parse_vtt(vtt_files[0])
                return None
            with open(sub_files[0]) as f:
                data = json.load(f)
            texts = []
            for event in data.get("events", []):
                for seg in event.get("segs", []):
                    t = seg.get("utf8", "").strip()
                    if t and t != "\n":
                        texts.append(t)
            text = re.sub(r'\s+', ' ', " ".join(texts)).strip()
            return text if len(text) > 50 else None
    except subprocess.TimeoutExpired:
        print("  [S4-ytdlp] Timeout")
        return None
    except FileNotFoundError:
        print("  [S4-ytdlp] yt-dlp not installed")
        return None
    except Exception as e:
        print(f"  [S4-ytdlp] Error: {str(e)[:80]}")
        return None


def _parse_vtt(vtt_path: str) -> Optional[str]:
    try:
        with open(vtt_path) as f:
            content = f.read()
        lines = content.split('\n')
        texts = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('WEBVTT') or '-->' in line or line.isdigit():
                continue
            line = re.sub(r'<[^>]+>', '', line)
            if line:
                texts.append(line)
        text = re.sub(r'\s+', ' ', ' '.join(texts)).strip()
        return text if len(text) > 50 else None
    except Exception:
        return None


# ── Strategy 5: Free proxy race ──────────────────────────────────────────────
def _fetch_free_proxies() -> List[str]:
    global _proxy_cache
    try:
        req = urllib.request.urlopen(PROXY_FETCH_URL, timeout=6)
        proxies = [p.strip() for p in req.read().decode().strip().split("\n") if p.strip()]
        random.shuffle(proxies)
        _proxy_cache = proxies
        return proxies
    except Exception as e:
        print(f"  [Proxy] Fetch failed: {e}")
        return _proxy_cache[:]


def _race_proxies(video_id: str, proxies: List[str]) -> Optional[str]:
    batch = proxies[:16]
    print(f"  [S5-race] Trying {len(batch)} proxies...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_sync_fetch, video_id, f"http://{p}"): p for p in batch}
        for future in as_completed(futures, timeout=10):
            try:
                result = future.result(timeout=8)
                if result:
                    return result
            except Exception:
                pass
    return None


# ── Main orchestrator ─────────────────────────────────────────────────────────
async def get_transcript_with_proxy_rotation(video_id: str) -> Dict:
    loop = asyncio.get_event_loop()

    # S1: youtube-transcript.io (best for Railway)
    print(f"  [S1] youtube-transcript.io...")
    text = await _fetch_via_transcript_io(video_id)
    if text:
        print(f"  [S1] SUCCESS ({len(text)} chars)")
        return {"success": True, "method": "transcript-io", "text": text, "cost": 0.0}
    print(f"  [S1] Failed")

    # S2: Direct (works locally, usually blocked on Railway)
    print(f"  [S2] Direct youtube-transcript-api...")
    try:
        text = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_fetch, video_id, None), timeout=10
        )
        if text:
            print(f"  [S2] SUCCESS ({len(text)} chars)")
            return {"success": True, "method": "direct", "text": text, "cost": 0.0}
    except Exception as e:
        print(f"  [S2] Failed: {str(e)[:60]}")

    # S3: Webshare premium proxy
    ws_user = os.getenv("WEBSHARE_PROXY_USERNAME")
    ws_pass = os.getenv("WEBSHARE_PROXY_PASSWORD")
    if ws_user and ws_pass:
        print(f"  [S3] Webshare proxy...")
        try:
            cfg = WebshareProxyConfig(proxy_username=ws_user, proxy_password=ws_pass, retries_when_blocked=2)
            api = YouTubeTranscriptApi(proxy_config=cfg)
            def _ws_fetch():
                try:
                    t = api.fetch(video_id, languages=["en", "en-US"])
                except Exception:
                    t = api.fetch(video_id)
                snippets = t.snippets if hasattr(t, "snippets") else t
                return " ".join([(s.text if hasattr(s,"text") else s.get("text","")) for s in snippets]).strip()
            text = await asyncio.wait_for(loop.run_in_executor(None, _ws_fetch), timeout=20)
            if text and len(text) > 50:
                print(f"  [S3] SUCCESS via Webshare ({len(text)} chars)")
                return {"success": True, "method": "webshare", "text": text, "cost": 0.0}
        except Exception as e:
            print(f"  [S3] Webshare failed: {str(e)[:60]}")

    # S4: yt-dlp
    print(f"  [S4] yt-dlp...")
    try:
        text = await asyncio.wait_for(
            loop.run_in_executor(None, _ytdlp_fetch, video_id), timeout=45
        )
        if text:
            print(f"  [S4] SUCCESS via yt-dlp ({len(text)} chars)")
            return {"success": True, "method": "yt-dlp", "text": text, "cost": 0.0}
    except Exception as e:
        print(f"  [S4] yt-dlp failed: {str(e)[:60]}")

    # S5: Free proxy race
    print(f"  [S5] Free proxy race...")
    proxies = await loop.run_in_executor(None, _fetch_free_proxies)
    if proxies:
        try:
            text = await asyncio.wait_for(
                loop.run_in_executor(None, _race_proxies, video_id, proxies), timeout=25
            )
            if text:
                return {"success": True, "method": "free_proxy", "text": text, "cost": 0.0}
        except Exception as e:
            print(f"  [S5] Race failed: {str(e)[:60]}")

    return {
        "success": False,
        "method": "all_failed",
        "error": (
            "Could not retrieve transcript. The video may have captions disabled. "
            "Sign up free at youtube-transcript.io and set YOUTUBE_TRANSCRIPT_IO_KEY "
            "in your environment for reliable extraction."
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
