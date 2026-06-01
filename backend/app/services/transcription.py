"""
YouTube Transcript Generator - Transcription Service
Proxy rotation to bypass YouTube IP blocks on cloud servers.

Priority:
  1. Direct request (sometimes works)
  2. Webshare proxies (if WEBSHARE_PROXY_USERNAME + WEBSHARE_PROXY_PASSWORD set)
  3. Free rotating proxies from proxyscrape API
"""

import re
import asyncio
import os
import random
import urllib.request
from typing import Dict, List, Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig


PROXY_FETCH_URL = (
    "https://api.proxyscrape.com/v3/free-proxy-list/get"
    "?request=displayproxies&protocol=http&timeout=5000"
    "&country=all&ssl=all&anonymity=elite,anonymous&limit=30"
)

_proxy_cache: List[str] = []


def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Invalid YouTube URL: {url}")


def fetch_free_proxies() -> List[str]:
    global _proxy_cache
    try:
        req = urllib.request.urlopen(PROXY_FETCH_URL, timeout=8)
        proxies = [p.strip() for p in req.read().decode().strip().split("\n") if p.strip()]
        random.shuffle(proxies)
        _proxy_cache = proxies
        print(f"  [Proxy] Fetched {len(proxies)} free proxies")
        return proxies
    except Exception as e:
        print(f"  [Proxy] Could not fetch proxy list: {e}")
        return _proxy_cache  # return cached if available


def _fetch_transcript(video_id: str, api: YouTubeTranscriptApi) -> Optional[str]:
    """Attempt to fetch transcript with given api instance."""
    try:
        t = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        snippets = t.snippets if hasattr(t, "snippets") else t
        text = " ".join([
            (s.text if hasattr(s, "text") else s.get("text", ""))
            for s in snippets
        ])
        return text if len(text) > 50 else None
    except Exception:
        # Try without language filter
        try:
            t = api.fetch(video_id)
            snippets = t.snippets if hasattr(t, "snippets") else t
            text = " ".join([
                (s.text if hasattr(s, "text") else s.get("text", ""))
                for s in snippets
            ])
            return text if len(text) > 50 else None
        except Exception:
            return None


async def get_transcript_with_proxy_rotation(video_id: str) -> Dict:
    """
    Try transcript fetching with multiple strategies:
    1. Direct (no proxy)
    2. Webshare (if credentials set)
    3. Free rotating proxies (up to 10 attempts)
    """

    # --- Strategy 1: Direct ---
    print(f"  [Method 1] Direct request for {video_id}...")
    try:
        api = YouTubeTranscriptApi()
        text = _fetch_transcript(video_id, api)
        if text:
            print(f"  [Method 1] SUCCESS ({len(text)} chars)")
            return {"success": True, "method": "direct", "text": text, "cost": 0.0}
        print("  [Method 1] No text returned")
    except Exception as e:
        print(f"  [Method 1] FAILED: {str(e)[:80]}")

    # --- Strategy 2: Webshare (premium, if configured) ---
    ws_user = os.getenv("WEBSHARE_PROXY_USERNAME")
    ws_pass = os.getenv("WEBSHARE_PROXY_PASSWORD")
    if ws_user and ws_pass:
        print(f"  [Method 2] Webshare proxy...")
        try:
            cfg = WebshareProxyConfig(
                proxy_username=ws_user,
                proxy_password=ws_pass,
                retries_when_blocked=3,
            )
            api = YouTubeTranscriptApi(proxy_config=cfg)
            text = _fetch_transcript(video_id, api)
            if text:
                print(f"  [Method 2] SUCCESS via Webshare ({len(text)} chars)")
                return {"success": True, "method": "webshare", "text": text, "cost": 0.0}
        except Exception as e:
            print(f"  [Method 2] Webshare FAILED: {str(e)[:80]}")
    else:
        print("  [Method 2] Webshare not configured - skipping")

    # --- Strategy 3: Free rotating proxies ---
    print(f"  [Method 3] Free rotating proxies...")
    proxies = fetch_free_proxies()
    if not proxies:
        return {
            "success": False,
            "method": "all_failed",
            "error": "No proxies available and direct request blocked",
        }

    attempted = 0
    for proxy in proxies[:12]:
        attempted += 1
        try:
            cfg = GenericProxyConfig(
                http_url=f"http://{proxy}",
                https_url=f"http://{proxy}",
            )
            api = YouTubeTranscriptApi(proxy_config=cfg)
            text = _fetch_transcript(video_id, api)
            if text:
                print(f"  [Method 3] SUCCESS via {proxy} ({len(text)} chars)")
                return {
                    "success": True,
                    "method": f"proxy:{proxy}",
                    "text": text,
                    "cost": 0.0,
                }
        except Exception as e:
            err = str(e)[:60]
            print(f"  [Method 3] {proxy} failed: {err}")
            continue

    return {
        "success": False,
        "method": "all_failed",
        "error": (
            "Could not retrieve transcript. Video may have no captions, "
            "or all proxy attempts were blocked. "
            "Try adding WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD "
            "to your Railway environment variables for more reliable results."
        ),
    }


async def transcribe_video(video_url: str, timeout: int = 300) -> Dict:
    print(f"\n[Transcribe] Starting: {video_url}")
    try:
        video_id = extract_video_id(video_url)
        print(f"[Transcribe] Video ID: {video_id}")
    except ValueError as e:
        return {"success": False, "error": str(e), "method": "none"}

    return await get_transcript_with_proxy_rotation(video_id)
