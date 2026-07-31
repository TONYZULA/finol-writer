# FINOL Blog Automation (OpenRouter)

Reliable WordPress blog automation using OpenRouter free models with built-in retries and provider health tracking.

## 🚀 Features

- **OpenRouter AI**: Single-provider setup using verified free models
- **Smart Retries**: Exponential backoff on transient failures
- **Model Fallback Ladder**: Automatically rolls to the next free model on 429/5xx/unavailability
- **Real-Time Monitoring**: Track provider health and call history
- **WordPress Integration**: Direct publishing
- **Custom Cover Uploads**: Choose a featured image per post before publishing
- **Hidden Character Cleanup**: Removes non-printable copy/paste artifacts before publishing
- **Research-Powered Content**: Uses Tavily for real-time web research

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Available Models](#available-models)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)

## ⚡ Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy the example secrets file:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with your API keys:

```toml
# Minimum configuration
OPENROUTER_API_KEY = "sk-or-v1-..."  # https://openrouter.ai/keys
TAVILY_API_KEY = "your-tavily-key"
```

### 3. Test the System

```bash
python test_fallback.py
```

### 4. Run the Application

```bash
streamlit run app.py
```

Visit `http://localhost:8501` and start creating content.

## 🔄 How It Works

### OpenRouter Call Flow

```
User Request
    ↓
OpenRouter API Call (best free model first)
    ↓ (429 / 5xx / unavailable)
Fall to next free model in ladder (exponential backoff)
    ↓ (success)
Return Response
```

### What Triggers a Model Switch?

- API connection errors
- Free-tier rate limiting (HTTP 429)
- Model removed or unavailable in the free catalog (HTTP 404)
- Request timeouts
- Empty responses

### Automatic Handling

- **Exponential Backoff**: 2s → 4s → 8s (capped at 10s)
- **Model Fallback Ladder**: tries up to 6 verified free models
- **JSON Mode**: enabled via `response_format` for SEO/outline phases
- **Health Tracking**: Monitors provider failures and availability

## ⚙️ Configuration

### API Keys

| Provider | Required | Get Key | Free Tier |
|----------|----------|---------|-----------|
| OpenRouter | Yes | [openrouter.ai/keys](https://openrouter.ai/keys) | ✅ free models |
| Tavily | Yes | [tavily.com](https://tavily.com) | ✅ 1000 searches/month |

### Environment Variables

For non-Streamlit deployments:

```bash
export OPENROUTER_API_KEY="..."
export TAVILY_API_KEY="..."
```

## 🤖 Available Models

### OpenRouter Free Models (verified working)
- **Primary**: `google/gemma-4-26b-a4b-it:free`
- **Fallbacks**: `nvidia/nemotron-3-super-120b-a12b:free`, `openai/gpt-oss-20b:free`, `inclusionai/ling-3.0-flash:free`, `nvidia/nemotron-nano-9b-v2:free`, `google/gemma-4-31b-it:free`

The complete ladder is maintained in `provider_manager.py` (`FREE_OR_MODELS`). Only `:free`-suffixed models are used. See [OpenRouter Models](https://openrouter.ai/models) for the current catalog.

## 📊 Monitoring

### Provider Status Dashboard

The app includes a real-time monitoring dashboard:

1. **Provider Monitor Tab**: View OpenRouter status and model ladder
2. **Call History**: See recent API calls and success rates
3. **Debug Panel**: Detailed error logs and statistics

### Programmatic Monitoring

```python
from automation import FinolAutomation

agent = FinolAutomation("google/gemma-4-26b-a4b-it:free")

# Check provider status
status = agent.provider_manager.get_provider_status()
print(status)
# {
#   'openrouter': {'available': True, 'failures': 0, 'last_error': None}
# }

# View call history
history = agent.provider_manager.get_call_history(limit=10)
for call in history:
    print(f"{call['provider']}: {call['status']} at {call['timestamp']} ({call.get('model')})")
```

## 🔧 Troubleshooting

### "All OpenRouter models failed"
**Cause**: `OPENROUTER_API_KEY` not configured, or all free models rate-limited
**Solution**: Configure `OPENROUTER_API_KEY` in `.streamlit/secrets.toml`; wait for free-tier limits to reset

### "Missing TAVILY_API_KEY"
**Cause**: Tavily API key not set
**Solution**: Add `TAVILY_API_KEY` to secrets (required for research)

### Slow Responses
**Cause**: Free-tier rate limits or slow models
**Solution**:
- Check Provider Monitor for 429s
- The fallback ladder automatically switches models

### Provider Shows "Unavailable"
**Cause**: Authentication failure
**Solution**:
- Verify API key is correct
- Check key at https://openrouter.ai/keys
- Regenerate API key if needed

### JSON Parsing Errors
**Cause**: Model didn't return valid JSON
**Solution**: `automation.py` auto-recovers embedded JSON or falls back to safe defaults

## 🏗️ Architecture

### Core Components

```
app.py
├── Streamlit UI
└── Monitoring dashboard

automation.py
├── Blog writing pipeline
├── WordPress integration
└── Uses ProviderManager

provider_manager.py
├── OpenRouter orchestration
├── Model fallback ladder
└── Health tracking

provider_dashboard.py
└── Monitoring UI components
```

### Provider Manager Flow

```python
ProviderManager
    ├── Initialize provider (OpenRouter)
    ├── Track health status
    ├── ai_call()
    │   ├── Try preferred model
    │   ├── On failure: next model in FREE_OR_MODELS ladder
    │   └── Return on success
    └── Log call history
```

## 📚 Documentation

- [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
- [PROVIDER_SETUP.md](PROVIDER_SETUP.md) - Detailed configuration guide
- [test_fallback.py](test_fallback.py) - Test suite for verification

## 🎯 Use Cases

### Content Creation
- Blog posts with research
- SEO-optimized articles
- Multi-section content

### WordPress Automation
- Direct publishing
- Metadata optimization

### Reliable AI Access
- Free-tier stability via model ladder
- Predictable configuration

## 🔐 Security

- API keys stored in Streamlit secrets (not in code)
- Environment variable support for production
- No API keys logged or exposed

## 🚀 Deployment

### Streamlit Cloud
1. Push to GitHub
2. Connect to Streamlit Cloud
3. Add secrets in dashboard (`OPENROUTER_API_KEY`, `TAVILY_API_KEY`)
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

### Local Production
```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## 📈 Performance

- **Retry Time**: 2-10 seconds depending on failures
- **Throughput**: Limited by OpenRouter free-tier rate limits
- **Latency**: 1-10 seconds per API call

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Custom retry strategies
- Advanced monitoring features
- Performance optimizations

## 📄 License

MIT License - feel free to use in your projects

## 🙏 Acknowledgments

- **OpenRouter** for free model access
- **Tavily** for research capabilities

## 📞 Support

- **Issues**: Open a GitHub issue
- **OpenRouter Support**: [openrouter.ai/docs](https://openrouter.ai/docs)

---

**Built for reliable AI-powered content creation**
