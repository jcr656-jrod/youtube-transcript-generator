"""
YouTube Transcript Generator - FastAPI Application Package
Main application initialization
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="YouTube Transcript Generator",
    description="Convert any YouTube video into summaries, Twitter threads, and more",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5000",
        "https://yourdomain.com",
        "*"  # For testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class TranscribeRequest(BaseModel):
    url: str
    analysis_type: str = "full"


class TranscribeResponse(BaseModel):
    success: bool
    transcript: str = None
    analysis: dict = None
    cost: float = 0.0
    processing_time: float = 0.0
    method: str = None
    error: str = None


# Import services
try:
    from .services.transcription import transcribe_video, extract_video_id
    from .services.analysis import analyze_transcript
except ImportError as e:
    print(f"⚠️  Warning: Could not import services - {e}")
    print("This is normal if running in test mode without full backend setup")


# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "YouTube Transcript Generator",
        "version": "0.1.0"
    }


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_endpoint(request: TranscribeRequest):
    """
    Main endpoint: Transcribe + Analyze
    """
    
    start_time = time.time()
    
    print(f"\n{'='*70}")
    print(f"📝 New transcription request")
    print(f"URL: {request.url}")
    print(f"Analysis type: {request.analysis_type}")
    print(f"{'='*70}")
    
    try:
        # Validate URL
        try:
            video_id = extract_video_id(request.url)
            print(f"✅ Valid YouTube URL: {video_id}")
        except ValueError as e:
            print(f"❌ Invalid URL: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid YouTube URL: {str(e)}"
            )
        
        # Transcribe
        print(f"\n📥 Transcription phase...")
        transcript_result = await transcribe_video(request.url)
        
        if not transcript_result["success"]:
            print(f"❌ Transcription failed: {transcript_result.get('error')}")
            raise HTTPException(
                status_code=400,
                detail=f"Transcription failed: {transcript_result.get('error')}"
            )
        
        transcript_text = transcript_result["text"]
        transcription_cost = transcript_result.get("cost", 0.0)
        transcription_method = transcript_result.get("method", "unknown")
        
        print(f"✅ Transcription complete")
        print(f"   Method: {transcription_method}")
        print(f"   Text length: {len(transcript_text)} chars")
        print(f"   Cost: ${transcription_cost:.4f}")
        
        # Analyze
        print(f"\n🤖 Analysis phase...")
        analysis_result = await analyze_transcript(
            transcript_text,
            request.analysis_type
        )
        
        if not analysis_result["success"]:
            print(f"❌ Analysis failed: {analysis_result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail="Analysis failed"
            )
        
        processing_time = time.time() - start_time
        total_cost = transcription_cost + 0.01
        
        print(f"✅ Analysis complete")
        print(f"   Analysis type: {request.analysis_type}")
        print(f"   Total cost: ${total_cost:.4f}")
        print(f"   Total time: {processing_time:.1f}s")
        print(f"{'='*70}\n")
        
        return TranscribeResponse(
            success=True,
            transcript=transcript_text,
            analysis=analysis_result["data"],
            cost=round(total_cost, 4),
            processing_time=round(processing_time, 2),
            method=transcription_method
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )


@app.get("/api/status")
async def get_status():
    """Check API status and capabilities"""
    return {
        "status": "operational",
        "openai_available": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic_available": bool(os.getenv("ANTHROPIC_API_KEY")),
        "features": [
            "youtube_native_captions",
            "whisper_transcription",
            "claude_analysis",
            "twitter_threads",
            "show_notes",
            "seo_metadata"
        ]
    }


@app.get("/")
async def root():
    """Root endpoint - serve frontend"""
    frontend_path = Path(__file__).parent.parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {
        "name": "YouTube Transcript Generator",
        "version": "0.1.0",
        "endpoints": {
            "health": "GET /health",
            "transcribe": "POST /api/transcribe",
            "status": "GET /api/status",
            "docs": "GET /docs"
        }
    }


# Mount static files (frontend assets)
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

__all__ = ['app']
