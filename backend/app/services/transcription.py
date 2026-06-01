"""
YouTube Transcript Generator - Transcription Service
4-method fallback system for maximum reliability
"""

import re
import asyncio
import subprocess
import os
from pathlib import Path
from typing import Dict, Optional
import httpx

# Try imports, handle gracefully if not available
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Invalid YouTube URL: {url}")


async def get_youtube_native_transcript(video_id: str) -> Dict:
    """
    METHOD 1: Get native YouTube captions
    Speed: <2 seconds
    Cost: $0
    Success rate: ~30% of videos
    """
    if not YOUTUBE_API_AVAILABLE:
        return {
            "success": False,
            "method": "youtube_native",
            "error": "youtube-transcript-api not available"
        }
    
    try:
        print(f"  [Method 1] Trying YouTube native captions for {video_id}...")
        
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try English first
        try:
            transcript = transcript_list.find_transcript(['en'])
        except Exception:
            # Fall back to any available language
            transcript = transcript_list.find_manually_created_transcripts()[0]
        
        entries = transcript.fetch()
        
        # Combine all text
        full_text = ' '.join([entry['text'] for entry in entries])
        
        print(f"  ✅ YouTube native captions found ({len(full_text)} chars)")
        
        return {
            "success": True,
            "method": "youtube_native",
            "text": full_text,
            "entries": entries,
            "cost": 0.0,
            "speed": "fast"
        }
    except Exception as e:
        print(f"  ❌ YouTube native failed: {str(e)[:80]}")
        return {
            "success": False,
            "method": "youtube_native",
            "error": str(e),
            "text": None
        }


async def get_whisper_transcript(video_url: str) -> Dict:
    """
    METHOD 2: Extract audio + OpenAI Whisper transcription
    Speed: 2-10 minutes (depends on length)
    Cost: ~$0.006/min audio
    Success rate: ~95%
    """
    if not OPENAI_AVAILABLE:
        return {
            "success": False,
            "method": "whisper",
            "error": "openai not available"
        }
    
    try:
        print(f"  [Method 2] Trying OpenAI Whisper...")
        
        # Download audio with yt-dlp
        output_path = "/tmp/%(id)s.%(ext)s"
        cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "192",
            "-o", output_path,
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=300, text=True)
        
        if result.returncode != 0:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            return {
                "success": False,
                "method": "whisper",
                "error": f"yt-dlp failed: {error_msg}"
            }
        
        # Find the downloaded file
        audio_files = list(Path("/tmp").glob("*.mp3"))
        if not audio_files:
            return {
                "success": False,
                "method": "whisper",
                "error": "No audio file downloaded"
            }
        
        audio_file = audio_files[-1]  # Get most recent
        print(f"  Audio downloaded: {audio_file.name} ({audio_file.stat().st_size / 1024 / 1024:.1f} MB)")
        
        # Transcribe with Whisper
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        with open(audio_file, 'rb') as f:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=f,
                language="en"
            )
        
        full_text = transcript['text']
        
        # Cleanup
        audio_file.unlink()
        
        # Estimate cost (~$0.006 per minute)
        # Whisper costs: $0.006 per minute of audio
        duration_seconds = len(full_text.split()) * 0.5  # Rough estimate
        duration_minutes = duration_seconds / 60
        cost = max(0.05, duration_minutes * 0.006)  # Min $0.05
        
        print(f"  ✅ Whisper transcription complete ({len(full_text)} chars, ~${cost:.3f})")
        
        return {
            "success": True,
            "method": "whisper",
            "text": full_text,
            "cost": round(cost, 3),
            "speed": "medium"
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "method": "whisper",
            "error": "Audio download timeout (video too long)"
        }
    except Exception as e:
        print(f"  ❌ Whisper failed: {str(e)[:80]}")
        return {
            "success": False,
            "method": "whisper",
            "error": str(e)
        }


async def transcribe_video(video_url: str, timeout: int = 300) -> Dict:
    """
    Main transcription function
    Try methods in order until one succeeds
    """
    print(f"\n🔄 Starting transcription for: {video_url}")
    
    try:
        video_id = extract_video_id(video_url)
        print(f"✅ Video ID: {video_id}")
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "method": "none"
        }
    
    # Method 1: YouTube native
    result = await get_youtube_native_transcript(video_id)
    if result["success"]:
        return result
    
    # Method 2: Whisper
    result = await get_whisper_transcript(video_url)
    if result["success"]:
        return result
    
    # All methods failed
    return {
        "success": False,
        "error": "Could not transcribe video with available methods",
        "method": "all_failed"
    }


if __name__ == "__main__":
    # Test
    import asyncio
    
    test_url = "https://youtu.be/vB08-7RzgOs"
    
    result = asyncio.run(transcribe_video(test_url))
    
    if result["success"]:
        print(f"\n✅ SUCCESS")
        print(f"Method: {result['method']}")
        print(f"Text length: {len(result['text'])} characters")
        print(f"Cost: ${result.get('cost', 0)}")
    else:
        print(f"\n❌ FAILED: {result['error']}")
