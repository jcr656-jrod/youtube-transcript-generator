# Railway.app Deployment Guide

## Step 1: Create Railway.app Account

1. Visit https://railway.app
2. Sign up with GitHub/email
3. Connect your GitHub account

## Step 2: Create Project + Add GitHub Repository

**Option A: Deploy from GitHub (Recommended)**

1. Click "New Project" in Railway dashboard
2. Click "Deploy from GitHub"
3. Select your GitHub repository containing this code
4. Authorize Railway to access your repos

**Option B: Manual GitHub Connection**

```bash
# Push code to GitHub first
git remote add origin https://github.com/YOUR_USERNAME/youtube-transcript-generator.git
git branch -M main
git push -u origin main
```

## Step 3: Configure Environment Variables in Railway

In your Railway project dashboard, go to **Variables** and add:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
ENVIRONMENT=production
DEBUG=false
```

**Getting API Keys:**

- **OpenAI API Key**: https://platform.openai.com/account/api-keys
- **Anthropic API Key**: https://console.anthropic.com/

## Step 4: Configure Railway Deployment Settings

1. **Build Command**: Leave default (auto-detects)
2. **Start Command**: Set to `cd backend && python -m uvicorn app:app --host 0.0.0.0 --port $PORT`
3. **Root Directory**: Leave empty (detects Dockerfile.prod automatically)

Railway will use Dockerfile.prod automatically.

## Step 5: Deploy

1. Click "Deploy" button
2. Wait for build to complete (3-5 minutes)
3. Check logs for errors

## Step 6: Verify Deployment

Once Railway shows "Deployment: Success", test the endpoints:

```bash
# Get your Railway URL from dashboard (e.g., https://youtube-transcript-xxxxx.railway.app)

# Health check
curl https://youtube-transcript-xxxxx.railway.app/health

# API status
curl https://youtube-transcript-xxxxx.railway.app/api/status

# Test transcription (requires valid YouTube URL)
curl -X POST https://youtube-transcript-xxxxx.railway.app/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{"url":"https://youtu.be/dQw4w9WgXcQ","analysis_type":"summary"}'
```

## Step 7: Set Custom Domain (Optional)

1. In Railway Project → Settings → Domains
2. Click "Add Domain"
3. Enter your custom domain (e.g., transcript-generator.yourdomain.com)
4. Railway provides a DNS entry to add to your DNS provider
5. Wait for DNS propagation (5-30 minutes)

## Step 8: Monitor Deployment

- **Logs**: View in "Deployments" tab
- **Metrics**: CPU, memory, requests in "Monitoring"
- **Health**: Green status indicator = healthy

## Environment Variables Reference

| Variable | Value | Required |
|----------|-------|----------|
| OPENAI_API_KEY | Your OpenAI API key | Yes |
| ANTHROPIC_API_KEY | Your Anthropic API key | Yes |
| ENVIRONMENT | production/development | No |
| DEBUG | true/false | No |
| ALLOWED_ORIGINS | Comma-separated list | No |
| DATABASE_URL | PostgreSQL URL (optional) | No |

## Troubleshooting

### "Module not found" errors
- Make sure requirements.txt is in /backend/requirements.txt
- Check all Python dependencies are listed

### "Port already in use"
- Railway auto-assigns $PORT environment variable
- Start command must use: `--port $PORT`

### API Keys not working
- Double-check values in Railway Variables dashboard
- Make sure no extra spaces in API keys
- Test keys directly with curl

### Slow deployments
- First deploy takes longer (building Docker image)
- Subsequent deploys are faster (cached layers)

## Redeploy After Changes

```bash
git add -A
git commit -m "Feature: Add new capability"
git push origin main
```

Railway will automatically redeploy when it detects new commits.

## Cost Estimation

- **Railway Free Tier**: $5 credit/month + pay-as-you-go
- **Typical Monthly Cost**: $5-20 depending on usage
- **API Costs**: Separate (OpenAI + Anthropic charges apply)

## Support

- Railway Docs: https://docs.railway.app
- Status: https://status.railway.app
- Discord: https://discord.gg/railway
