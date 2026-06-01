#!/bin/bash

# YouTube Transcript Generator - Railway.app Deployment Script
# This script automates the deployment process to Railway.app

set -e

echo "🚀 YouTube Transcript Generator - Railway.app Deployment"
echo "=========================================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v git &> /dev/null; then
    echo "❌ Git not installed. Please install git first."
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "❌ curl not installed. Please install curl first."
    exit 1
fi

echo "✅ Git and curl available"
echo ""

# Check git status
echo "📝 Checking git repository..."
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not a git repository. Please run this from project root."
    exit 1
fi

if [[ -z $(git config user.email) ]]; then
    echo "⚠️  Git user.email not configured"
    read -p "Enter git user email: " email
    git config user.email "$email"
fi

echo "✅ Git repository ready"
echo ""

# Verify project structure
echo "🏗️  Checking project structure..."

if [ ! -f "backend/app.py" ]; then
    echo "❌ backend/app.py not found"
    exit 1
fi

if [ ! -f "backend/requirements.txt" ]; then
    echo "❌ backend/requirements.txt not found"
    exit 1
fi

if [ ! -f "Dockerfile.prod" ]; then
    echo "❌ Dockerfile.prod not found"
    exit 1
fi

if [ ! -f "Procfile" ]; then
    echo "❌ Procfile not found"
    exit 1
fi

echo "✅ Project structure verified"
echo ""

# Commit changes
echo "📦 Committing changes..."
git add -A
if git diff --cached --quiet; then
    echo "✅ No changes to commit"
else
    git commit -m "Deploy: Production build with Railway.app configuration"
    echo "✅ Changes committed"
fi

echo ""

# Display next steps
echo "=========================================================="
echo "✅ Repository ready for Railway.app deployment!"
echo "=========================================================="
echo ""
echo "📌 Next steps:"
echo ""
echo "1. Push to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/youtube-transcript-generator.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "2. Create Railway.app account and project:"
echo "   https://railway.app"
echo ""
echo "3. Connect GitHub repository in Railway dashboard"
echo ""
echo "4. Add environment variables in Railway:"
echo "   OPENAI_API_KEY=sk-..."
echo "   ANTHROPIC_API_KEY=sk-ant-..."
echo ""
echo "5. Deploy and monitor!"
echo ""
echo "📚 Documentation: See RAILWAY_DEPLOYMENT.md"
echo "📋 Checklist: See DEPLOYMENT_CHECKLIST.md"
echo ""
