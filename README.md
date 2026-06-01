# 🎬 YouTube Transcript Generator

Convert any YouTube video into summaries, Twitter threads, show notes, and SEO metadata in seconds.

## 🚀 Features

- ✅ **4-Method Transcription Engine** - YouTube captions → Whisper AI → Browser scraping → Human fallback
- ✅ **Claude AI Analysis** - Smart summaries, key points, and insights
- ✅ **Twitter Threads** - 5-tweet and 10-tweet ready-to-post threads
- ✅ **Show Notes** - Structured outlines with timestamps
- ✅ **SEO Metadata** - Titles, descriptions, keywords for content creators
- ✅ **Fast** - 60 seconds from paste to download
- ✅ **Affordable** - Free tier + $29-$99/month paid plans

## 🛠️ Tech Stack

**Backend:**
- FastAPI (Python)
- OpenAI Whisper API
- Anthropic Claude API
- youtube-transcript-api

**Frontend:**
- HTML/CSS/JavaScript (plain, no frameworks)
- RESTful API integration

## 📋 Quick Start

### Prerequisites
- Python 3.8+
- OPENAI_API_KEY (from https://platform.openai.com)
- ANTHROPIC_API_KEY (from https://console.anthropic.com)

### Setup

```bash
# 1. Clone/navigate to project
cd youtube-transcript-generator

# 2. Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your API keys:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# 4. Start backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 5. Start frontend (new terminal)
cd ../frontend
python3 -m http.server 5000

# 6. Open browser
# http://localhost:5000
```

### Using the Startup Script

```bash
cd youtube-transcript-generator
./start.sh
```

This will start both backend (port 8000) and frontend (port 5000).

## 📖 API Documentation

### Endpoint: POST /api/transcribe

**Request:**
```json
{
  "url": "https://youtu.be/vB08-7RzgOs",
  "analysis_type": "full"
}
```

**Analysis Types:**
- `full` - Summary + threads + show notes + SEO
- `summary` - Just executive summary
- `threads` - Just Twitter threads
- `show_notes` - Just show notes

**Response:**
```json
{
  "success": true,
  "transcript": "Full video transcript text...",
  "analysis": {
    "summary": "2-3 sentence overview",
    "key_points": ["point1", "point2"],
    "twitter_threads": {
      "thread_5": ["tweet1", "tweet2", ...],
      "thread_10": [...]
    },
    "seo_metadata": {
      "title": "SEO title",
      "description": "Meta description",
      "keywords": ["keyword1", "keyword2"]
    }
  },
  "cost": 0.15,
  "processing_time": 45.3,
  "method": "whisper"
}
```

### Testing with curl

```bash
curl -X POST http://localhost:8000/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtu.be/vB08-7RzgOs",
    "analysis_type": "full"
  }'
```

## 💰 Monetization

### 3-Tier Freemium Model

| Tier | Price | Videos/Month | Features |
|------|-------|--------------|----------|
| Free | $0 | 3 | Summary only |
| Starter | $29 | 50 | Threads + show notes + email |
| Pro | $99 | 500 | All + API + priority |

### Expected Revenue

- Month 1: 80-120 customers, $2.3K-3.5K MRR
- Month 3: 200-350 customers, $5.8K-10K MRR
- Year 1: $250K-550K revenue

## 🎯 Marketing Channels

1. **ProductHunt** - Launch for upvotes + credibility
2. **Twitter** - Build in public + share results
3. **Reddit** - Content communities (r/Youtubers, r/podcasting)
4. **Direct Outreach** - Email creators you watch
5. **Influencer Partners** - Give free access to 10 creators
6. **SEO** - Rank for "YouTube transcript generator"

## 📊 Unit Economics

- **CAC:** $0-50 (mostly organic)
- **LTV:** $1,050-1,900
- **Gross Margin:** 85%
- **LTV:CAC:** 21-38x ✅

## 🔄 How It Works

1. User pastes YouTube URL
2. System extracts video ID
3. Try 4 transcription methods in order:
   - YouTube native captions (fast, free)
   - OpenAI Whisper (reliable, cheap)
   - Browser scraping (fallback)
   - Human transcription (premium)
4. Claude AI analyzes transcript
5. Generate summaries, threads, metadata
6. User downloads + shares

## 📁 Project Structure

```
youtube-transcript-generator/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── transcription.py  # 4-method engine
│   │   │   └── analysis.py       # Claude AI
│   │   ├── routes/
│   │   ├── models/
│   │   └── utils/
│   ├── app.py                    # FastAPI app
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html                # Simple vanilla JS UI
│   ├── src/
│   │   ├── pages/index.jsx
│   │   └── styles/
│   └── package.json
├── start.sh                       # Startup script
└── README.md
```

## 🚀 Deployment

### Option 1: Railway.app (Recommended)

```bash
# 1. Push to GitHub
git push origin main

# 2. Connect to Railway
# 3. Set environment variables
# 4. Deploy!
```

### Option 2: Vercel (Frontend) + Fly.io (Backend)

```bash
# Frontend
cd frontend && vercel --prod

# Backend
fly launch
fly deploy
```

### Option 3: Docker

```bash
docker build -t transcript-generator .
docker run -p 8000:8000 -e OPENAI_API_KEY=... transcript-generator
```

## 🐛 Troubleshooting

**"youtube-transcript-api not found"**
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt`

**"OPENAI_API_KEY not set"**
- Create `backend/.env` with your keys
- Or set environment variable: `export OPENAI_API_KEY=sk-...`

**"Transcription failed for video"**
- Video may not have captions and audio can't be extracted
- Try another video first to test

**"Port 8000 already in use"**
- Run on different port: `python -m uvicorn app:app --port 8001`

## 📈 Next Steps

1. **Week 1:** Launch beta to 10 creators
2. **Week 2:** Get feedback, iterate features
3. **Week 3:** Add Stripe payments
4. **Week 4:** Launch ProductHunt + Twitter
5. **Month 2:** Target $1K MRR
6. **Month 3:** Hit $5K MRR
7. **Month 6:** $15K+ MRR

## 📄 License

MIT

## 👥 Support

Questions? File an issue or reach out directly.

---

**Built with ❤️ by [Your Name]**

**Ready to go live?** Check out `/TRANSCRIPT_GENERATOR_BLUEPRINT.md` for complete marketing + monetization strategy.
