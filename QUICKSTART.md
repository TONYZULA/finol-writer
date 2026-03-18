# Quick Start Guide - Multi-Provider Fallback System

Get your WordPress blog automation running with intelligent AI provider fallback in 5 minutes.

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure API Keys

Create `.streamlit/secrets.toml` in your project root:

```toml
# Minimum configuration (Bytez free tier only)
BYTEZ_API_KEY = "444d1ac0a8b038cbe61ff956a8cdd700"
TAVILY_API_KEY = "your-tavily-key-here"
TEMPLATED_API_KEY = "your-templated-key-here"

# Optional: Add more providers for better fallback
GOOGLE_API_KEY = "your-google-api-key"
OPENROUTER_API_KEY = "your-openrouter-key"
```

### Get API Keys:
- **Bytez** (Free): Already included above, or get your own at [bytez.com/api](https://bytez.com/api)
- **Tavily** (Required): [tavily.com](https://tavily.com) - for research
- **Templated** (Required): [templated.io](https://templated.io) - for cover images
- **Google Gemini** (Optional): [aistudio.google.com](https://aistudio.google.com/app/apikeys)
- **OpenRouter** (Optional): [openrouter.ai](https://openrouter.ai)

## Step 3: Test Your Setup

```bash
# Set environment variables (or use .streamlit/secrets.toml)
export BYTEZ_API_KEY="444d1ac0a8b038cbe61ff956a8cdd700"
export GOOGLE_API_KEY="your-key-here"  # optional
export OPENROUTER_API_KEY="your-key-here"  # optional

# Run test suite
python test_fallback.py
```

Expected output:
```
✅ Configuration: PASSED
✅ Simple Call: PASSED
✅ Fallback Mechanism: PASSED
✅ Bytez Direct: PASSED
✅ JSON Mode: PASSED
✅ Health Tracking: PASSED

🎉 All tests passed! Your fallback system is working correctly.
```

## Step 4: Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Step 5: Generate Your First Article

1. **Select a model** from the sidebar (e.g., `google/gemini-2.5-flash`)
2. **Enter WordPress credentials** (optional, for publishing)
3. **Fill in article details**:
   - Topic: "Benefits of AI in Healthcare"
   - Audience: "Healthcare professionals"
   - Goal: "Educate about AI applications"
   - Word Target: 1000
4. **Click "Generate Draft"**
5. **Monitor the fallback system** in the "Provider Monitor" tab

## How Fallback Works

When you click "Generate Draft", the system:

1. **Tries your selected model first** (e.g., Gemini)
2. **If it fails** (timeout, rate limit, error):
   - Waits 2 seconds
   - Tries OpenRouter with similar model
3. **If that fails**:
   - Waits 4 seconds
   - Tries Bytez with fallback model
4. **Returns result** from whichever provider succeeds

You'll see this in the **Provider Monitor** tab with real-time status.

## Example Scenarios

### Scenario 1: Gemini Rate Limited
```
User selects: google/gemini-2.5-pro
  ↓
Try Gemini API → ❌ Rate limit exceeded
  ↓ (wait 2s)
Try OpenRouter → ❌ Connection timeout
  ↓ (wait 4s)
Try Bytez → ✅ Success!
  ↓
Article generated using Bytez
```

### Scenario 2: All Providers Available
```
User selects: google/gemini-2.5-flash
  ↓
Try Gemini API → ✅ Success!
  ↓
Article generated using Gemini
(No fallback needed)
```

### Scenario 3: Only Bytez Configured
```
User selects: google/gemini-2.5-pro
  ↓
Try Gemini API → ❌ No API key
  ↓ (skip)
Try OpenRouter → ❌ No API key
  ↓ (skip)
Try Bytez → ✅ Success!
  ↓
Article generated using Bytez
```

## Monitoring Provider Health

### In the UI
1. Go to **Provider Monitor** tab
2. See real-time status of all providers
3. View call history and success rates

### Programmatically
```python
from automation import FinolAutomation

agent = FinolAutomation("google/gemini-2.5-flash")

# Check provider status
status = agent.provider_manager.get_provider_status()
print(status)

# View call history
history = agent.provider_manager.get_call_history(limit=10)
for call in history:
    print(f"{call['provider']}: {call['status']}")
```

## Troubleshooting

### "All AI providers failed"
**Solution**: Configure at least one API key in secrets.toml

### "Missing TAVILY_API_KEY"
**Solution**: Add Tavily API key to secrets.toml (required for research)

### Slow responses
**Solution**: 
- Check Provider Monitor for rate limits
- Use smaller models (e.g., `gemini-2.5-flash` instead of `gemini-2.5-pro`)
- Bytez free tier is unlimited but may be slower

### Provider shows "Unavailable"
**Solution**:
- Check API key is correct in secrets.toml
- Verify API key has quota remaining
- Check Debug panel for specific error

## Advanced Configuration

### Custom Fallback Order
Edit `provider_manager.py` line 120 to change provider order:

```python
def _initialize_providers(self) -> List[ProviderConfig]:
    return [
        ProviderConfig("bytez", "BYTEZ_API_KEY", "https://api.bytez.com/v1"),  # Try Bytez first
        ProviderConfig("gemini", "GOOGLE_API_KEY"),
        ProviderConfig("openrouter", "OPENROUTER_API_KEY", ...),
    ]
```

### Adjust Retry Timing
Edit `provider_manager.py` line 58:

```python
self.retry_backoff_base = 3  # Change from 2 to 3 (3s, 9s, 27s)
```

### Add Custom Provider
```python
# In provider_manager.py, add to _initialize_providers():
ProviderConfig("custom", "CUSTOM_API_KEY", "https://api.custom.com/v1")

# Then implement in _call_custom_api() method
```

## Next Steps

- Read [PROVIDER_SETUP.md](PROVIDER_SETUP.md) for detailed configuration
- Check [provider_manager.py](provider_manager.py) for implementation details
- Customize models in [app.py](app.py) dropdown
- Add more providers as needed

## Support

- **Bytez**: [docs.bytez.com](https://docs.bytez.com)
- **OpenRouter**: [openrouter.ai/docs](https://openrouter.ai/docs)
- **Gemini**: [ai.google.dev/docs](https://ai.google.dev/docs)

## Production Deployment

### Streamlit Cloud
1. Push code to GitHub
2. Connect to Streamlit Cloud
3. Add secrets in dashboard (Settings → Secrets)
4. Deploy

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py"]
```

### Environment Variables
For non-Streamlit deployments, use environment variables instead of secrets.toml:
```bash
export GOOGLE_API_KEY="..."
export OPENROUTER_API_KEY="..."
export BYTEZ_API_KEY="..."
export TAVILY_API_KEY="..."
export TEMPLATED_API_KEY="..."
```

---

**You're all set!** Your blog automation now has intelligent multi-provider fallback. 🎉
