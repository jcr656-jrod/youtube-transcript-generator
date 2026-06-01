#!/bin/bash
# YouTube Transcript Generator - Startup Script

set -e

echo "🚀 YouTube Transcript Generator - Starting Services"
echo "=================================================="
echo ""

# Check if venv exists
if [ ! -d "backend/venv" ]; then
    echo "❌ Virtual environment not found"
    echo "Run: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate venv
echo "📦 Activating virtual environment..."
source backend/venv/bin/activate

# Check API keys
echo "🔑 Checking API keys..."
if [ -z "$OPENAI_API_KEY" ] && [ ! -f "backend/.env" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set. Update backend/.env with your keys."
fi

if [ -z "$ANTHROPIC_API_KEY" ] && [ ! -f "backend/.env" ]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY not set. Update backend/.env with your keys."
fi

# Start backend
echo ""
echo "🔧 Starting FastAPI backend on port 8000..."
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 2

# Start frontend
echo "🎨 Starting frontend server on port 5000..."
cd ../frontend
python3 -m http.server 5000 &
FRONTEND_PID=$!

echo ""
echo "✅ Services started!"
echo "📚 Frontend: http://localhost:5000"
echo "🔌 API: http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop services"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
