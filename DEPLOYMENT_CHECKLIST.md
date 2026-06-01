# YouTube Transcript Generator - Production Deployment Checklist

## Pre-Deployment ✅

- [x] Git repository initialized and committed
- [x] Docker configuration created (Dockerfile.prod)
- [x] Railway.app configuration files created (railway.toml, Procfile, railway.json)
- [x] Environment variables documented
- [x] Frontend and backend integrated
- [x] Health check endpoint configured
- [x] CORS properly configured
- [x] Backend imports verified

## Railway.app Deployment Steps

### 1. Create Railway Account
- [ ] Go to https://railway.app
- [ ] Sign up with GitHub
- [ ] Verify email

### 2. Connect GitHub Repository
- [ ] Push code to GitHub: 
  ```bash
  git remote add origin https://github.com/YOUR_USERNAME/youtube-transcript-generator.git
  git push -u origin main
  ```
- [ ] In Railway dashboard: New Project → Deploy from GitHub
- [ ] Select repository and authorize

### 3. Configure Environment Variables
In Railway Dashboard → Variables:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
ENVIRONMENT=production
DEBUG=false
```

### 4. Deploy
- [ ] Click "Deploy" 
- [ ] Monitor logs (3-5 minutes)
- [ ] Check for "Deployment: Success"

### 5. Test Endpoints

```bash
RAILWAY_URL=https://YOUR_RAILWAY_DOMAIN.railway.app

# Health check
curl $RAILWAY_URL/health

# API status  
curl $RAILWAY_URL/api/status

# Test transcription (optional)
curl -X POST $RAILWAY_URL/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{"url":"https://youtu.be/dQw4w9WgXcQ","analysis_type":"summary"}'
```

### 6. Frontend (Optional: Deploy to Vercel)

If you want separate frontend hosting:

```bash
cd frontend
npm install  # If using npm
vercel --prod
```

Then update API URL in frontend code to point to Railway backend.

### 7. Custom Domain (Optional)

1. Railway Dashboard → Settings → Domains
2. Add your domain (e.g., transcript-gen.yourdomain.com)
3. Add DNS CNAME record to Railway's provided value
4. Wait 5-30 minutes for DNS propagation
5. Verify with: `nslookup transcript-gen.yourdomain.com`

## Post-Deployment ✅

- [ ] Health endpoint responding
- [ ] API status endpoint working
- [ ] Frontend accessible from root URL
- [ ] Logs showing no errors
- [ ] Metrics showing healthy CPU/Memory
- [ ] Test with real YouTube URL

## Monitoring

**Regular checks:**
- Monitor logs for errors
- Check CPU/Memory usage in Railway dashboard
- Test health endpoint weekly: `curl YOUR_URL/health`
- Monitor API error rates in logs

**Alerts to set up (if available):**
- Deployment failure notifications
- Health check failures
- High CPU/Memory usage

## Rollback Procedure

If deployment has issues:

1. Go to Railway Deployments tab
2. Click on previous "Successful" deployment
3. Click "Redeploy"
4. Wait for rollback to complete

## Cost Management

- Free tier: $5/month credit + pay-as-you-go
- Monitor usage in Railway account dashboard
- API costs billed separately (OpenAI, Anthropic)

## Success Criteria

✅ All complete when:
1. `curl YOUR_URL/health` returns 200 OK
2. `curl YOUR_URL/api/status` shows "operational": true
3. Frontend loads at `YOUR_URL/`
4. No errors in Railway logs
5. Metrics show healthy system

---

**Live URL Format:** `https://[project-name]-[random].railway.app`

**Documentation:** See RAILWAY_DEPLOYMENT.md for detailed guide
