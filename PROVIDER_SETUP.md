# Multi-Provider AI Fallback System Setup Guide

This guide explains how to configure the intelligent fallback mechanism for your WordPress blog automation system.

## Overview

The system automatically rotates between three AI providers:
- **Gemini** (Google) - Direct API
- **OpenRouter** - Aggregator with free tier models
- **Bytez** - Free tier API with extensive model library

When one provider fails (API error, timeout, rate limit), the system automatically switches to the next available provider without interrupting your workflow.

## Configuration

### 1. Streamlit Secrets Setup

Add the following to your `.streamlit/secrets.toml` file:

```toml
# Google Gemini API
GOOGLE_API_KEY = "your-google-api-key-here"

# OpenRouter API
OPENROUTER_API_KEY = "your-openrouter-api-key-here"
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OR_SITE_URL = "https://yoursite.com"  # Optional
OR_APP_NAME = "FINOL Blog Writer"      # Optional

# Bytez API (Free Tier)
BYTEZ_API_KEY = "444d1ac0a8b038cbe61ff956a8cdd700"

# Tavily Search API
TAVILY_API_KEY = "your-tavily-api-key-here"

# Templated.io for image generation
TEMPLATED_API_KEY = "your-templated-api-key-here"
```

### 2. Getting API Keys

#### Google Gemini
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikeys)
2. Create a new API key
3. Copy and paste into `GOOGLE_API_KEY`

#### OpenRouter
1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Sign up and go to Keys section
3. Create an API key
4. Copy and paste into `OPENROUTER_API_KEY`

#### Bytez (Free Tier)
- Pre-configured API key: `444d1ac0a8b038cbe61ff956a8cdd700`
- Or get your own at [Bytez.com](https://bytez.com/api)
- Supports 70+ free tier models including:
  - OpenAI models (GPT-4, GPT-3.5, etc.)
  - Anthropic Claude models
  - Google Gemini models
  - Open-source models (Llama, Mistral, Qwen, etc.)

#### Tavily Search
1. Go to [Tavily.com](https://tavily.com)
2. Sign up and get your API key
3. Copy and paste into `TAVILY_API_KEY`

#### Templated.io
1. Visit [Templated.io](https://templated.io)
2. Create account and get API key
3. Copy and paste into `TEMPLATED_API_KEY`

## How the Fallback System Works

### Provider Selection Strategy

1. **Preferred Provider First**: System tries your selected model's provider first
2. **Automatic Rotation**: If that fails, rotates to next available provider
3. **Intelligent Retry**: Uses exponential backoff (2s, 4s, 8s) between attempts
4. **Model Normalization**: Automatically adapts model names for each provider

### Error Handling

The system handles:
- **Connection Errors**: Automatic retry with backoff
- **Rate Limits**: Exponential backoff before retry
- **Authentication Failures**: Marks provider as unavailable
- **Bad Requests**: Retries without JSON mode if applicable
- **Timeouts**: Moves to next provider

### Example Flow

```
User selects: "google/gemini-2.5-pro"
    ↓
Try Gemini API with gemini-2.5-pro
    ↓ (fails - rate limit)
Wait 2 seconds, try OpenRouter with gemini-2.5-flash
    ↓ (fails - timeout)
Wait 4 seconds, try Bytez with google/gemini-2.5-flash
    ↓ (succeeds!)
Return response to user
```

## Monitoring Provider Health

### Check Provider Status

```python
from automation import FinolAutomation

agent = FinolAutomation("google/gemini-2.5-pro")

# Get provider status
status = agent.provider_manager.get_provider_status()
print(status)

# Output:
# {
#   'gemini': {'available': True, 'failures': 0, 'last_error': None},
#   'openrouter': {'available': True, 'failures': 1, 'last_error': 'Rate limit exceeded'},
#   'bytez': {'available': True, 'failures': 0, 'last_error': None}
# }
```

### View Call History

```python
# Get last 10 API calls
history = agent.provider_manager.get_call_history(limit=10)
for call in history:
    print(f"{call['provider']}: {call['status']} at {call['timestamp']}")
```

## Available Models by Provider

### Gemini (Direct API)
- `google/gemini-2.5-pro`
- `google/gemini-2.5-flash`
- `google/gemini-2.5-flash-lite`

### OpenRouter (Free Tier)
- `openrouter/google/gemma-3-4b-it:free`
- `openrouter/meta-llama/llama-3.2-3b-instruct:free`
- `openrouter/mistralai/mistral-small-3.1-24b-instruct:free`
- And 25+ more free models

### Bytez (Free Tier - 70+ Models)
- OpenAI: `openai/gpt-4o-mini`, `openai/gpt-3.5-turbo`, etc.
- Anthropic: `anthropic/claude-sonnet-4-5`, `anthropic/claude-haiku-4-5`, etc.
- Google: `google/gemini-2.5-flash`, `google/gemma-3-4b-it`, etc.
- Open-source: `Qwen/Qwen3-4B`, `meta-llama/Llama-2-7b-chat-hf`, etc.

See `provider_manager.py` for complete model list.

## Troubleshooting

### "All AI providers failed"
- Check that at least one API key is configured in secrets
- Verify API keys are correct and have quota remaining
- Check internet connection
- Review call history: `agent.provider_manager.get_call_history()`

### Provider marked as unavailable
- Check authentication error in status: `agent.provider_manager.get_provider_status()`
- Verify API key is correct
- Regenerate API key if needed

### Slow responses
- Check if rate limits are being hit: `agent.provider_manager.get_call_history()`
- Consider using smaller models (e.g., `gemini-2.5-flash` instead of `gemini-2.5-pro`)
- Bytez free tier may have usage limits

### JSON parsing errors
- System automatically retries without JSON mode
- If still failing, check model supports JSON responses
- Try different model from fallback provider

## Best Practices

1. **Configure Multiple Providers**: Set up at least 2 API keys for redundancy
2. **Monitor Health**: Regularly check provider status in production
3. **Use Appropriate Models**: Match model size to your needs
4. **Handle Errors Gracefully**: Wrap `ai_call()` in try-except for critical workflows
5. **Log Call History**: Keep logs for debugging and optimization

## Example: Custom Error Handling

```python
from automation import FinolAutomation

agent = FinolAutomation("google/gemini-2.5-pro")

try:
    response = agent.ai_call(
        system_prompt="You are a blog writer",
        user_prompt="Write about AI",
        json_mode=True
    )
except RuntimeError as e:
    # All providers failed
    print(f"Error: {e}")
    
    # Check which providers are still available
    available = agent.provider_manager.get_available_providers()
    print(f"Available providers: {available}")
    
    # Get detailed status
    status = agent.provider_manager.get_provider_status()
    for provider, info in status.items():
        print(f"{provider}: {info}")
```

## Performance Tips

1. **Bytez for Cost**: Free tier with 70+ models, no rate limits for free tier
2. **OpenRouter for Variety**: 30+ free models, good for testing
3. **Gemini for Quality**: Best quality responses, good rate limits
4. **Fallback Strategy**: Gemini → OpenRouter → Bytez (quality to cost)

## Support

For issues with specific providers:
- **Gemini**: [Google AI Support](https://support.google.com/ai)
- **OpenRouter**: [OpenRouter Docs](https://openrouter.ai/docs)
- **Bytez**: [Bytez Docs](https://docs.bytez.com)
