# Streamlit Cloud Deployment Guide

## 🚀 Deploy to Streamlit Cloud (share.streamlit.io)

### Step 1: Push Code to GitHub

```bash
# Add all new files
git add .

# Commit changes
git commit -m "Add multi-provider AI fallback system with Bytez integration"

# Push to GitHub
git push origin main
```

### Step 2: Configure Secrets on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click on your app (finol-writer)
3. Click **Settings** (⚙️) → **Secrets**
4. Add the following secrets:

```toml
# Required - Bytez API (Free tier included)
BYTEZ_API_KEY = "444d1ac0a8b038cbe61ff956a8cdd700"

# Required - Research & Images
TAVILY_API_KEY = "your-tavily-api-key-here"
TEMPLATED_API_KEY = "your-templated-api-key-here"

# Optional - Better quality and redundancy
GOOGLE_API_KEY = "your-google-api-key-here"
OPENROUTER_API_KEY = "your-openrouter-api-key-here"
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
```

### Step 3: Deploy

1. Click **Deploy** or wait for auto-deploy
2. App will be available at: `https://finol-writer.streamlit.app`

### Step 4: Verify Deployment

1. Open your app URL
2. Check Provider Monitor tab
3. Generate a test article
4. Verify fallback works

## 🔑 Getting API Keys

### Bytez (Pre-configured)
- Already included: `444d1ac0a8b038cbe61ff956a8cdd700`
- Or get your own: [bytez.com/api](https://bytez.com/api)

### Tavily (Required)
- Sign up: [tavily.com](https://tavily.com)
- Free tier: 1000 searches/month

### Templated (Required)
- Sign up: [templated.io](https://templated.io)
- Get API key from dashboard

### Google Gemini (Optional)
- Get key: [aistudio.google.com/app/apikeys](https://aistudio.google.com/app/apikeys)
- Free tier available

### OpenRouter (Optional)
- Sign up: [openrouter.ai](https://openrouter.ai)
- 30+ free models available

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Secrets configured on Streamlit Cloud
- [ ] At least BYTEZ_API_KEY, TAVILY_API_KEY, TEMPLATED_API_KEY added
- [ ] App deployed successfully
- [ ] Test article generation works
- [ ] Provider Monitor shows status

## 🐛 Troubleshooting

### "Missing API Key" errors
→ Add the required key to Streamlit Cloud Secrets

### "All providers failed"
→ Check at least one AI provider key is configured

### App won't start
→ Check requirements.txt is in repository
→ Verify no syntax errors in Python files

### Slow performance
→ Use smaller models (gemini-2.5-flash)
→ Bytez free tier may be slower

## 📊 Monitoring on Streamlit Cloud

- Use Provider Monitor tab to check health
- View call history for debugging
- Check Debug Panel for errors
- Monitor Streamlit Cloud logs

---

**Your app will be live at**: `https://finol-writer.streamlit.app` 🚀
