"""
YouTube Transcript Generator - Analysis Service
Uses Claude AI to generate summaries, threads, show notes, and more
"""

import json
import os
from typing import Dict, Optional
from anthropic import Anthropic

client = Anthropic()


async def analyze_transcript(text: str, analysis_type: str = "full") -> Dict:
    """
    Use Claude to analyze transcript and generate outputs
    
    Types:
    - full: Summary + threads + show notes + seo
    - summary: Just executive summary
    - threads: Just Twitter threads
    - show_notes: Just show notes
    - seo: Just SEO metadata
    """
    
    print(f"  [Analysis] Running {analysis_type} analysis...")
    
    if analysis_type == "full":
        prompt = f"""Analyze this YouTube transcript and provide comprehensive output in JSON format.

TRANSCRIPT (first 4000 chars):
{text[:4000]}

Provide ONLY valid JSON (no other text) with this exact structure:
{{
    "summary": "2-3 sentence executive summary of the video content",
    "key_points": ["main point 1", "main point 2", "main point 3", "main point 4"],
    "twitter_threads": {{
        "thread_5": ["tweet 1", "tweet 2", "tweet 3", "tweet 4", "tweet 5"],
        "thread_10": ["tweet 1", "tweet 2", "tweet 3", "tweet 4", "tweet 5", "tweet 6", "tweet 7", "tweet 8", "tweet 9", "tweet 10"]
    }},
    "show_notes": "Structured outline with main sections and key quotes. Format as markdown with timestamps if available.",
    "seo_metadata": {{
        "title": "SEO-optimized title (60 chars max)",
        "description": "Meta description for search results (160 chars max)",
        "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
    }},
    "questions_answered": {{"question 1": "answer 1", "question 2": "answer 2"}}
}}

IMPORTANT: Return ONLY the JSON object, no other text."""
    
    elif analysis_type == "summary":
        prompt = f"""Summarize this YouTube transcript in 2-3 sentences:

{text[:2000]}

Return ONLY the summary text, nothing else."""
    
    elif analysis_type == "threads":
        prompt = f"""Create engaging Twitter threads from this transcript.

TRANSCRIPT:
{text[:3000]}

Return ONLY valid JSON (no other text):
{{
    "thread_5": ["tweet 1", "tweet 2", "tweet 3", "tweet 4", "tweet 5"],
    "thread_10": ["tweet 1", "tweet 2", "tweet 3", "tweet 4", "tweet 5", "tweet 6", "tweet 7", "tweet 8", "tweet 9", "tweet 10"]
}}"""
    
    elif analysis_type == "show_notes":
        prompt = f"""Create detailed show notes from this transcript.

TRANSCRIPT:
{text[:3000]}

Return ONLY the show notes as markdown text with sections and key points."""
    
    else:
        raise ValueError(f"Unknown analysis type: {analysis_type}")
    
    try:
        # Call Claude
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text
        
        # Try to parse as JSON for full/threads
        if analysis_type in ["full", "threads"]:
            try:
                result = json.loads(response_text)
                print(f"  ✅ {analysis_type} analysis complete")
                return {"success": True, "data": result}
            except json.JSONDecodeError:
                print(f"  ⚠️  Could not parse JSON, returning raw text")
                return {"success": True, "data": {"raw": response_text}}
        else:
            # For summary/show_notes, just return the text
            print(f"  ✅ {analysis_type} analysis complete")
            return {"success": True, "data": response_text}
    
    except Exception as e:
        print(f"  ❌ Analysis failed: {str(e)[:80]}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


async def get_summary(text: str) -> str:
    """Get just the summary"""
    result = await analyze_transcript(text, "summary")
    if result["success"]:
        return result["data"]
    return "Analysis failed"


async def get_threads(text: str) -> Dict:
    """Get just the Twitter threads"""
    result = await analyze_transcript(text, "threads")
    if result["success"]:
        return result["data"]
    return {"error": "Analysis failed"}


async def get_show_notes(text: str) -> str:
    """Get just the show notes"""
    result = await analyze_transcript(text, "show_notes")
    if result["success"]:
        return result["data"]
    return "Analysis failed"


if __name__ == "__main__":
    # Test
    import asyncio
    
    test_transcript = """
    In this video, I'm going to show you how to make money online in 2026.
    There are several methods that have worked really well for creators.
    The first method is white-labeling software like HighLevel.
    You can resell it to clients for much more than you pay.
    The second method is creating digital products.
    These have high profit margins and can be sold repeatedly.
    The third method is running an agency that provides services.
    This requires more time but has unlimited earning potential.
    """
    
    result = asyncio.run(analyze_transcript(test_transcript, "full"))
    
    if result["success"]:
        print("✅ Analysis successful")
        print(json.dumps(result["data"], indent=2))
    else:
        print(f"❌ Analysis failed: {result['error']}")
