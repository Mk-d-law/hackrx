# HackRx API - Deployment Guide

## 🚀 Deployment Options

### Option 1: Updated Requirements (Recommended)
Use the updated `requirements.txt` with exact versions that work locally:

```bash
# Push to GitHub with updated requirements.txt
git add requirements.txt Dockerfile .dockerignore
git commit -m "Fix deployment dependencies - match local working versions"
git push origin main
```

### Option 2: Simplified Requirements
If Option 1 fails, use the simplified approach:

```bash
# Rename files for deployment
mv Dockerfile Dockerfile.original
mv Dockerfile.simple Dockerfile
mv requirements.txt requirements_original.txt
mv requirements_deploy.txt requirements.txt

# Deploy with simplified dependencies
git add .
git commit -m "Use simplified dependencies for deployment"
git push origin main
```

### Option 3: Environment Variables Fix
Add these environment variables in Render dashboard:

```
HF_HUB_DISABLE_SYMLINKS_WARNING=1
TRANSFORMERS_CACHE=/tmp/transformers_cache
HF_HOME=/tmp/hf_home
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

## 🔧 Key Changes Made

### 1. **Updated Dependencies**
- `sentence-transformers==5.1.0` (matches local)
- `huggingface-hub==0.34.3` (matches local)
- `transformers==4.55.0` (matches local)
- `torch==2.8.0` (matches local)

### 2. **Docker Optimizations**
- Python 3.11 (better compatibility)
- CPU-only torch installation
- Environment variables for HuggingFace warnings
- Proper cache directory permissions

### 3. **Build Optimizations**
- `.dockerignore` to reduce build context
- Increased pip timeout
- Proper cache handling

## 🎯 Deployment Steps

1. **Choose deployment approach** (Option 1 recommended)
2. **Set environment variables** in Render:
   - `API_KEY` (your auth token)
   - `GOOGLE_API_KEY` (your Gemini API key)
   - `PINECONE_API_KEY` (your Pinecone key)
   - `PINECONE_HOST` (your Pinecone host URL)
   - `PINECONE_INDEX_NAME` (your index name)

3. **Deploy to Render**:
   - Connect GitHub repository
   - Select Docker deployment
   - Auto-deploy on push

## 🔍 Troubleshooting

If deployment still fails:
1. Check Render logs for specific error
2. Try Option 2 (simplified requirements)
3. Verify all environment variables are set
4. Consider using Render's native Python runtime instead of Docker

## ✅ Expected Result
- API accessible at: `https://your-app.onrender.com`
- Health check: `https://your-app.onrender.com/health`
- Main endpoint: `https://your-app.onrender.com/hackrx/run`