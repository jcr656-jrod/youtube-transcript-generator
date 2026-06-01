"""
YouTube Transcript Generator - Transcription Service
Proxy rotation with concurrent async attempts to bypass YouTube IP blocks.
"""

import re
import asyncio
import os
import random
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from typing import Dict, List, Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

PROXY_FETCH_URL = (
    "https://api.proxyscrape.com/v3/free-proxy-list/get"
    "?request=displayproxies&protocol=http&timeout=3000"
    "&country=US,GB,DE,CA&ssl=all&anonymity=elite,anonymous&limit=50"
)
_proxy_cache: List[str] = []
PROXY_TIMEOUT = 8  # seconds per proxy attempt


def extract_video_id(url: str) -> str:
    for pattern in [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)",
    ]:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Invalid YouTube URL: {url}")


def _sync_fetch(video_id: str, proxy_url: Optional[str] = None) -> Optional[str]:
    """Synchronous transcript fetch - runs in thread pool."""
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
    """Run proxy attempts concurrently - return first success."""
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

    # Strategy 1: Direct (fast, no overhead)
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

    # Strategy 2: Webshare (premium, if configured)
    ws_user = os.getenv("WEBSHARE_PROXY_USERNAME")
    ws_pass = os.getenv("WEBSHARE_PROXY_PASSWORD")
    if ws_user and ws_pass:
        print(f"  [S2] Webshare proxy...")
        try:
            cfg = WebshareProxyConfig(proxy_username=ws_user, proxy_password=ws_pass, retries_when_blocked=2)
            api = YouTubeTranscriptApi(proxy_config=cfg)
            text = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: _sync_fetch(video_id, None) or None),
                timeout=15
            )
            # Actually call with webshare api
            def _ws_fetch():
                try:
                    t = api.fetch(video_id, languages=["en", "en-US"])
                except Exception:
                    t = api.fetch(video_id)
                snippets = t.snippets if hasattr(t, "snippets") else t
                return " ".join([(s.text if hasattr(s,"text") else s.get("text","")) for s in snippets]).strip()
            text = await asyncio.wait_for(loop.run_in_executor(None, _ws_fetch), timeout=20)
            if text and len(text) > 50:
                print(f"  [S2] SUCCESS via Webshare ({len(text)} chars)")
                return {"success": True, "method": "webshare", "text": text, "cost": 0.0}
        except Exception as e:
            print(f"  [S2] Webshare failed: {str(e)[:60]}")

    # Strategy 3: Concurrent free proxy race
    print(f"  [S3] Free proxy race...")
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
            print(f"  [S3] Race failed: {str(e)[:60]}")

    return {
        "success": False,
        "method": "all_failed",
        "error": (
            "Could not retrieve transcript after trying direct + proxy rotation. "
            "This video may have captions disabled, or add WEBSHARE_PROXY_USERNAME "
            "/ WEBSHARE_PROXY_PASSWORD to Railway env for premium proxies."
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
