# Troubleshooting Guide

## Common Issues and Solutions

### 1. KeyError: 'section_markdown' ✅ FIXED

**Error:**
```
KeyError: 'section_markdown'
```

**Cause:** AI returned plain text instead of JSON format

**Solution:** Already fixed in latest code! The system now:
- Handles both JSON and plain text responses
- Provides fallback structures when parsing fails
- Supports multiple response field names
- Continues generation even if one section fails

**Action:** Reboot your app on Streamlit Cloud to get the fix.

---

### 2. Python 3.14 Installation Errors ✅ FIXED

**Error:**
```
ERROR: Failed building wheel for pillow
RequiredDependencyException: zlib
```

**Cause:** Python 3.14 is too new for some dependencies

**Solution:** Already fixed! The code now uses Python 3.11 via `runtime.txt`

**Action:** Reboot your app on Streamlit Cloud.

---

### 3. Missing API Keys

**Error:**
```
Missing TAVILY_API_KEY in Streamlit Secrets!
```

**Solution:**
1. Go to Streamlit Cloud
2. Settings → Secrets
3. Add the missing API key:
```toml
TAVILY_API_KEY = "your-key-here"
```

**Required Keys:**
- `TAVILY_API_KEY` - For research
- `TEMPLATED_API_KEY` - For cover images
- At least one AI provider key (BYTEZ_API_KEY is pre-configured)

---

### 4. "All AI providers failed"

**Error:**
```
RuntimeError: All AI providers failed
```

**Possible Causes:**
1. No AI provider keys configured
2. All provider keys are invalid
3. All providers are rate limited

**Solution:**
1. Check Provider Monitor tab for status
2. Verify at least one key is configured:
   - `BYTEZ_API_KEY` (should be pre-configured)
   - `GOOGLE_API_KEY`
   - `OPENROUTER_API_KEY`
3. Check Debug Panel for specific errors
4. Wait a few minutes if rate limited

---

### 5. Slow Article Generation

**Symptom:** Takes 30+ seconds to generate

**Causes:**
- Using large models (gemini-2.5-pro)
- Bytez free tier (slower but unlimited)
- Multiple provider fallbacks

**Solutions:**
1. Use smaller models:
   - `google/gemini-2.5-flash` (fast)
   - `openrouter/google/gemma-3-4b-it:free` (fast)
2. Add more provider keys for better fallback
3. Reduce word target

---

### 6. WordPress Publishing Fails

**Error:**
```
Error uploading to WordPress
```

**Solutions:**
1. Verify WordPress URL is correct (include https://)
2. Check username is correct
3. Ensure you're using Application Password (not regular password)
4. Verify WordPress REST API is enabled
5. Check WordPress user has publishing permissions

**Get Application Password:**
1. WordPress Admin → Users → Profile
2. Scroll to "Application Passwords"
3. Create new password
4. Copy and use in app

---

### 7. Cover Image Generation Fails

**Error:**
```
Error generating cover image
```

**Solutions:**
1. Verify `TEMPLATED_API_KEY` is configured
2. Check Templated.io account has quota
3. Verify template ID is correct
4. Try regenerating

---

### 8. Provider Shows "Unavailable"

**Symptom:** Provider Monitor shows provider as unavailable

**Causes:**
1. Invalid API key
2. API key has no quota
3. Authentication failed

**Solutions:**
1. Check API key in Secrets
2. Verify key is correct (no extra spaces)
3. Check provider account has quota
4. Regenerate API key if needed
5. Remove and re-add key in Secrets

---

### 9. JSON Parsing Errors

**Error:**
```
JSONDecodeError: Expecting value
```

**Solution:** Already handled in latest code! System now:
- Tries multiple JSON parsing strategies
- Falls back to plain text if JSON fails
- Provides default structures
- Continues generation

**Action:** Reboot app to get the fix.

---

### 10. App Won't Start

**Symptom:** App shows error on startup

**Checklist:**
- [ ] Python version is 3.11 (check Advanced Settings)
- [ ] All required secrets are configured
- [ ] No syntax errors in code
- [ ] Dependencies install successfully

**Solutions:**
1. Check Streamlit Cloud logs for specific error
2. Verify secrets are valid TOML format
3. Clear cache and reboot
4. Check GitHub code is up to date

---

## Debugging Steps

### Step 1: Check Provider Status
1. Open your app
2. Go to **Provider Monitor** tab
3. Check which providers are available
4. Look for error messages

### Step 2: Review Call History
1. In Provider Monitor tab
2. Scroll to **Call History**
3. Check recent API calls
4. Look for patterns in failures

### Step 3: Check Debug Panel
1. Go to **Debug** tab
2. Review error logs
3. Check provider statistics
4. Look for specific error messages

### Step 4: Check Streamlit Logs
1. Go to Streamlit Cloud
2. Click on your app
3. Click **Manage app**
4. View logs for detailed errors

---

## Getting Help

### Check Documentation
- **QUICKSTART.md** - Setup guide
- **PROVIDER_SETUP.md** - Configuration
- **QUICK_REFERENCE.md** - Quick commands
- **DEPLOYMENT_CHECKLIST.md** - Deployment steps

### Check Provider Status
- **Bytez**: [status.bytez.com](https://status.bytez.com)
- **OpenRouter**: [status.openrouter.ai](https://status.openrouter.ai)
- **Google**: [status.cloud.google.com](https://status.cloud.google.com)

### Test Locally
```bash
# Run test suite
python3 test_fallback.py

# Run app locally
streamlit run app.py
```

### Contact Support
- **Streamlit**: [discuss.streamlit.io](https://discuss.streamlit.io)
- **Bytez**: [docs.bytez.com](https://docs.bytez.com)
- **OpenRouter**: [openrouter.ai/docs](https://openrouter.ai/docs)

---

## Prevention Tips

### 1. Configure Multiple Providers
Don't rely on just one provider. Add keys for:
- Bytez (free, 70+ models)
- Google Gemini (best quality)
- OpenRouter (variety)

### 2. Monitor Regularly
- Check Provider Monitor tab weekly
- Review call history for errors
- Monitor API usage and quotas

### 3. Use Appropriate Models
- Development: Small models (gemini-2.5-flash)
- Production: Balance quality and speed
- Testing: Free tier models

### 4. Keep Keys Updated
- Rotate keys periodically
- Check quota regularly
- Update expired keys promptly

### 5. Test Before Publishing
- Generate test articles
- Check all features work
- Verify WordPress integration
- Test fallback mechanism

---

## Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| KeyError | Reboot app (fix already deployed) |
| Python 3.14 error | Reboot app (fix already deployed) |
| Missing key | Add to Streamlit Secrets |
| Slow generation | Use smaller model |
| Provider unavailable | Check API key |
| WordPress fails | Use Application Password |
| All providers fail | Check at least one key configured |

---

**Most issues are already fixed in the latest code. Just reboot your app!** 🎉
