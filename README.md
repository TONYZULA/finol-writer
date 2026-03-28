# FINOL Blog Automation (Bytez-Only)

Reliable WordPress blog automation using Bytez models with built-in retries and provider health tracking.

## 🚀 Features

- **Bytez-Only AI**: Single-provider setup for stability
- **Smart Retries**: Exponential backoff on transient failures
- **Real-Time Monitoring**: Track provider health and call history
- **70+ Models Available**: OpenAI, Anthropic, Google, Meta, and open-source models via Bytez
- **WordPress Integration**: Direct publishing
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
BYTEZ_API_KEY = "your-bytez-key"  # Free tier available
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

### Bytez Call Flow

```
User Request
    ↓
Bytez API Call
    ↓ (transient failure)
Retry with exponential backoff
    ↓ (success)
Return Response
```

### What Triggers Retries?

- API connection errors
- Rate limit exceeded
- Request timeouts (>60s)
- Authentication failures
- Bad request errors

### Automatic Handling

- **Exponential Backoff**: 2s → 4s → 8s (capped at 10s)
- **JSON Mode Fallback**: Retries without JSON if a model doesn't support it
- **Health Tracking**: Monitors provider failures and availability

## ⚙️ Configuration

### API Keys

| Provider | Required | Get Key | Free Tier |
|----------|----------|---------|-----------|
| Bytez | Yes | [bytez.com/api](https://bytez.com/api) | ✅ 70+ models |
| Tavily | Yes | [tavily.com](https://tavily.com) | ✅ 1000 searches/month |

### Environment Variables

For non-Streamlit deployments:

```bash
export BYTEZ_API_KEY="..."
export TAVILY_API_KEY="..."
```

## 🤖 Available Models

### Bytez (70+ Free Models)
- **OpenAI**: `openai/gpt-4o-mini`, `openai/gpt-3.5-turbo`
- **Anthropic**: `anthropic/claude-sonnet-4-5`, `anthropic/claude-haiku-4-5`
- **Google**: `google/gemini-2.5-flash`, `google/gemma-3-4b-it`
- **Meta**: `meta-llama/Llama-2-7b-chat-hf`
- **Qwen**: `Qwen/Qwen3-4B`, `Qwen/Qwen2.5-3B-Instruct`
- **DeepSeek**: `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`
- **Mistral**: `mistralai/Mistral-7B-Instruct-v0.3`
- And 60+ more

See [Bytez Models Page](https://bytez.com/models?task=chat) for the complete list.

## 📊 Monitoring

### Provider Status Dashboard

The app includes a real-time monitoring dashboard:

1. **Provider Monitor Tab**: View Bytez status
2. **Call History**: See recent API calls and success rates
3. **Debug Panel**: Detailed error logs and statistics

### Programmatic Monitoring

```python
from automation import FinolAutomation

agent = FinolAutomation("google/gemini-2.5-flash")

# Check provider status
status = agent.provider_manager.get_provider_status()
print(status)
# {
#   'bytez': {'available': True, 'failures': 0, 'last_error': None}
# }

# View call history
history = agent.provider_manager.get_call_history(limit=10)
for call in history:
    print(f"{call['provider']}: {call['status']} at {call['timestamp']}")
```

## 🔧 Troubleshooting

### "All AI providers failed"
**Cause**: Bytez API key not configured or unavailable
**Solution**: Configure `BYTEZ_API_KEY` in `.streamlit/secrets.toml`

### "Missing TAVILY_API_KEY"
**Cause**: Tavily API key not set
**Solution**: Add `TAVILY_API_KEY` to secrets (required for research)

### Slow Responses
**Cause**: Rate limits or slow models
**Solution**:
- Check Provider Monitor for rate limits
- Use faster models (`google/gemini-2.5-flash`)

### Provider Shows "Unavailable"
**Cause**: Authentication failure
**Solution**:
- Verify API key is correct
- Check API key has quota remaining
- Regenerate API key if needed

### JSON Parsing Errors
**Cause**: Model doesn't support JSON mode
**Solution**: System automatically retries without JSON mode

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
├── Bytez orchestration
├── Retry logic
└── Health tracking

provider_dashboard.py
└── Monitoring UI components
```

### Provider Manager Flow

```python
ProviderManager
    ├── Initialize provider (Bytez)
    ├── Track health status
    ├── ai_call()
    │   ├── Try Bytez
    │   ├── On failure: exponential backoff
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
- Single provider stability
- Predictable configuration

## 🔐 Security

- API keys stored in Streamlit secrets (not in code)
- Environment variable support for production
- No API keys logged or exposed

## 🚀 Deployment

### Streamlit Cloud
1. Push to GitHub
2. Connect to Streamlit Cloud
3. Add secrets in dashboard
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
- **Throughput**: Limited by Bytez rate limits
- **Latency**: 1-5 seconds per API call

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Custom retry strategies
- Advanced monitoring features
- Performance optimizations

## 📄 License

MIT License - feel free to use in your projects

## 🙏 Acknowledgments

- **Bytez** for free tier API access
- **Tavily** for research capabilities

## 📞 Support

- **Issues**: Open a GitHub issue
- **Bytez Support**: [docs.bytez.com](https://docs.bytez.com)

---

**Built for reliable AI-powered content creation**
