# Quick Reference Card - Multi-Provider Fallback System

## 🚀 Quick Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Test the system
python3 test_fallback.py

# Run the application
streamlit run app.py
```

## 🔑 Minimum Configuration

```toml
# .streamlit/secrets.toml
BYTEZ_API_KEY = "444d1ac0a8b038cbe61ff956a8cdd700"
TAVILY_API_KEY = "your-tavily-key-here"
TEMPLATED_API_KEY = "your-templated-key-here"
```

## 🔄 How Fallback Works

```
Request → Gemini → Fails → Wait 2s → OpenRouter → Fails → Wait 4s → Bytez → Success!
```

## 📊 Provider Comparison

| Provider | Models | Free Tier | Quality | Speed |
|----------|--------|-----------|---------|-------|
| **Gemini** | 3 | ✅ Generous | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **OpenRouter** | 30+ | ✅ Yes | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Bytez** | 70+ | ✅ Unlimited | ⭐⭐⭐ | ⭐⭐⭐ |

## 🎯 Recommended Models

### Best Quality
```python
"google/gemini-2.5-pro"  # Gemini (premium)
```

### Best Balance
```python
"google/gemini-2.5-flash"  # Gemini (fast + quality)
```

### Best Free
```python
"openrouter/mistralai/mistral-small-3.1-24b-instruct:free"  # OpenRouter
```

### Always Available
```python
"google/gemini-2.5-flash"  # Via Bytez fallback
```

## 🔧 Common Tasks

### Check Provider Status
```python
from automation import FinolAutomation

agent = FinolAutomation("google/gemini-2.5-flash")
status = agent.provider_manager.get_provider_status()
print(status)
```

### View Call History
```python
history = agent.provider_manager.get_call_history(limit=10)
for call in history:
    print(f"{call['provider']}: {call['status']}")
```

### Get Available Providers
```python
available = agent.provider_manager.get_available_providers()
print(f"Available: {available}")
```

## 🐛 Troubleshooting Quick Fixes

| Error | Quick Fix |
|-------|-----------|
| "All providers failed" | Add at least one API key to secrets.toml |
| "Missing TAVILY_API_KEY" | Add Tavily key (required) |
| Slow responses | Use smaller model (e.g., gemini-2.5-flash) |
| Provider unavailable | Check API key in secrets.toml |
| JSON parsing error | System auto-retries without JSON mode |

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit UI |
| `automation.py` | Blog automation pipeline |
| `provider_manager.py` | Fallback system core |
| `provider_dashboard.py` | Monitoring UI |
| `test_fallback.py` | Test suite |
| `.streamlit/secrets.toml` | API keys (create from .example) |

## 🎯 Error Types & Actions

| Error Type | System Action |
|------------|---------------|
| Connection Error | Retry with backoff → Next provider |
| Rate Limit | Exponential backoff → Next provider |
| Auth Failure | Mark unavailable → Skip provider |
| Timeout | Immediate failover → Next provider |
| Bad Request | Retry without JSON → Next provider |

## 📈 Monitoring Locations

### In UI
1. **Provider Monitor Tab** - Real-time status
2. **Debug Panel** - Detailed errors
3. **Call History** - Recent API calls

### In Code
```python
# Status
agent.provider_manager.get_provider_status()

# History
agent.provider_manager.get_call_history()

# Available
agent.provider_manager.get_available_providers()
```

## 🔐 API Key Sources

| Provider | Get Key From |
|----------|--------------|
| Bytez | [bytez.com/api](https://bytez.com/api) (pre-configured) |
| Tavily | [tavily.com](https://tavily.com) |
| Templated | [templated.io](https://templated.io) |
| Gemini | [aistudio.google.com](https://aistudio.google.com/app/apikeys) |
| OpenRouter | [openrouter.ai](https://openrouter.ai) |

## ⏱️ Timing Expectations

| Scenario | Time |
|----------|------|
| First provider succeeds | 1-3 seconds |
| Second provider succeeds | 4-8 seconds |
| Third provider succeeds | 9-15 seconds |

## 🎨 Status Indicators

| Icon | Meaning |
|------|---------|
| ✅ | Success / Available |
| ❌ | Failed / Unavailable |
| ⚠️ | Warning / Skipped |
| 🔄 | In Progress |

## 📚 Documentation Map

| Document | When to Read |
|----------|--------------|
| **README.md** | Overview and features |
| **QUICKSTART.md** | First-time setup (5 min) |
| **PROVIDER_SETUP.md** | Detailed configuration |
| **ARCHITECTURE.md** | System design |
| **IMPLEMENTATION_SUMMARY.md** | What was built |
| **QUICK_REFERENCE.md** | This file (quick lookup) |

## 🚀 Deployment Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Copy secrets template: `cp .streamlit/secrets.toml.example .streamlit/secrets.toml`
- [ ] Add API keys to `.streamlit/secrets.toml`
- [ ] Test system: `python3 test_fallback.py`
- [ ] Run app: `streamlit run app.py`
- [ ] Generate test article
- [ ] Check Provider Monitor tab
- [ ] Verify fallback works (try with only Bytez key)

## 💡 Pro Tips

1. **Start with Bytez only** - Works out of the box with pre-configured key
2. **Add Gemini for quality** - Best results with Google's API
3. **Add OpenRouter for variety** - 30+ free models to choose from
4. **Monitor the dashboard** - Watch provider health in real-time
5. **Use smaller models** - Faster responses, lower rate limits
6. **Check call history** - Debug issues by reviewing past calls

## 🎯 Success Indicators

✅ Test suite passes (6/6 tests)  
✅ At least one provider available  
✅ Article generation completes  
✅ Provider Monitor shows status  
✅ No "All providers failed" errors  

## 📞 Quick Help

**Can't start?** → Check QUICKSTART.md  
**Configuration issues?** → Check PROVIDER_SETUP.md  
**Understanding system?** → Check ARCHITECTURE.md  
**Need examples?** → Check README.md  
**Troubleshooting?** → Check Debug Panel in UI  

---

**Keep this card handy for quick reference!** 📌
