# Bytez Provider Setup Guide

This guide explains how to configure the Bytez-only setup for your WordPress blog automation system.

## Overview

The system uses **Bytez** as the single AI provider. If a request fails due to a transient error, it retries with exponential backoff.

## Configuration

### 1. Streamlit Secrets Setup

Add the following to your `.streamlit/secrets.toml` file:

```toml
# Bytez API (Free Tier)
BYTEZ_API_KEY = "your-bytez-api-key-here"

# Tavily Search API (required for research)
TAVILY_API_KEY = "your-tavily-api-key-here"
```

### 2. Getting API Keys

#### Bytez (Free Tier)
- Get a key at [Bytez.com](https://bytez.com/api)
- Supports 70+ free tier models including:
  - OpenAI models
  - Anthropic Claude models
  - Google Gemini models
  - Open-source models (Llama, Mistral, Qwen, etc.)

#### Tavily Search
1. Go to [Tavily.com](https://tavily.com)
2. Sign up and get your API key
3. Copy and paste into `TAVILY_API_KEY`

## How the Retry System Works

### Retry Strategy

1. **Bytez API Call**
2. **On failure**: exponential backoff (2s → 4s → 8s)
3. **JSON fallback**: retries without JSON mode if needed

### Error Handling

The system handles:
- **Connection Errors**: Automatic retry with backoff
- **Rate Limits**: Exponential backoff before retry
- **Authentication Failures**: Marks provider as unavailable
- **Bad Requests**: Retries without JSON mode if applicable
- **Timeouts**: Retries based on backoff

## Monitoring Provider Health

### Check Provider Status

```python
from automation import FinolAutomation

agent = FinolAutomation("google/gemini-2.5-flash")

# Get provider status
status = agent.provider_manager.get_provider_status()
print(status)

# Output:
# {
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

## Available Models (Bytez)

- OpenAI: `openai/gpt-4o-mini`, `openai/gpt-3.5-turbo`, etc.
- Anthropic: `anthropic/claude-sonnet-4-5`, `anthropic/claude-haiku-4-5`, etc.
- Google: `google/gemini-2.5-flash`, `google/gemma-3-4b-it`, etc.
- Open-source: `Qwen/Qwen3-4B`, `meta-llama/Llama-2-7b-chat-hf`, etc.

See `provider_manager.py` for the default model list.

## Troubleshooting

### "All AI providers failed"
- Check that `BYTEZ_API_KEY` is configured in secrets
- Verify API key is correct and has quota remaining
- Check internet connection
- Review call history: `agent.provider_manager.get_call_history()`

### Provider marked as unavailable
- Check authentication error in status: `agent.provider_manager.get_provider_status()`
- Verify API key is correct
- Regenerate API key if needed

### Slow responses
- Check if rate limits are being hit: `agent.provider_manager.get_call_history()`
- Consider using smaller/faster models (e.g., `google/gemini-2.5-flash`)

### JSON parsing errors
- System automatically retries without JSON mode
- If still failing, check model supports JSON responses
- Try a different Bytez model

## Best Practices

1. **Keep Bytez Key Healthy**: Monitor quota and regenerate if needed
2. **Use Appropriate Models**: Match model size to your needs
3. **Monitor Health**: Regularly check provider status in production
4. **Log Call History**: Keep logs for debugging and optimization

## Support

- **Bytez Docs**: [docs.bytez.com](https://docs.bytez.com)
