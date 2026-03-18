# Architecture Overview - Multi-Provider Fallback System

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Streamlit UI (app.py)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Write Article│  │   Provider   │  │   Debug Panel        │  │
│  │     Tab      │  │  Monitor Tab │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FinolAutomation (automation.py)                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  run_writing_pipeline()                                   │  │
│  │    ├─ Research (Tavily)                                   │  │
│  │    ├─ SEO Analysis (AI)                                   │  │
│  │    ├─ Outline Generation (AI)                             │  │
│  │    └─ Section Writing (AI)                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ai_call(system_prompt, user_prompt, json_mode)          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              ProviderManager (provider_manager.py)               │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  ai_call() - Main Fallback Logic                          │ │
│  │                                                            │ │
│  │  1. Get preferred provider                                │ │
│  │  2. Try API call                                          │ │
│  │  3. On failure:                                           │ │
│  │     ├─ Log error                                          │ │
│  │     ├─ Update health status                               │ │
│  │     ├─ Exponential backoff (2s, 4s, 8s)                  │ │
│  │     └─ Try next provider                                  │ │
│  │  4. Return first success                                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   Provider   │  │   Provider   │  │      Provider        │ │
│  │    Config    │  │    Config    │  │       Config         │ │
│  │   (Gemini)   │  │ (OpenRouter) │  │      (Bytez)         │ │
│  │              │  │              │  │                      │ │
│  │ • API Key    │  │ • API Key    │  │ • API Key            │ │
│  │ • Base URL   │  │ • Base URL   │  │ • Base URL           │ │
│  │ • Available  │  │ • Available  │  │ • Available          │ │
│  │ • Failures   │  │ • Failures   │  │ • Failures           │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      External APIs                               │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │    Gemini    │  │  OpenRouter  │  │       Bytez          │ │
│  │     API      │  │     API      │  │        API           │ │
│  │              │  │              │  │                      │ │
│  │ ai.google.   │  │ openrouter.  │  │ api.bytez.com        │ │
│  │ dev          │  │ ai           │  │                      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Fallback Decision Flow

```
                    ┌─────────────────┐
                    │  User Request   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Get Preferred   │
                    │    Provider     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Try Provider   │
                    │   API Call      │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
            ┌──────────────┐   ┌──────────────┐
            │   Success?   │   │   Failure?   │
            └──────┬───────┘   └──────┬───────┘
                   │                  │
                   │                  ▼
                   │         ┌─────────────────┐
                   │         │  Log Error      │
                   │         │  Update Health  │
                   │         └────────┬────────┘
                   │                  │
                   │                  ▼
                   │         ┌─────────────────┐
                   │         │ More Providers? │
                   │         └────────┬────────┘
                   │                  │
                   │         ┌────────┴────────┐
                   │         │                 │
                   │         ▼                 ▼
                   │  ┌──────────────┐  ┌──────────────┐
                   │  │     Yes      │  │      No      │
                   │  └──────┬───────┘  └──────┬───────┘
                   │         │                 │
                   │         ▼                 ▼
                   │  ┌──────────────┐  ┌──────────────┐
                   │  │ Exponential  │  │ Raise Error  │
                   │  │   Backoff    │  │ "All Failed" │
                   │  └──────┬───────┘  └──────────────┘
                   │         │
                   │         ▼
                   │  ┌──────────────┐
                   │  │ Try Next     │
                   │  │  Provider    │
                   │  └──────┬───────┘
                   │         │
                   └─────────┴─────────────────┐
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │ Return Response │
                                      └─────────────────┘
```

## Provider Selection Logic

```
┌─────────────────────────────────────────────────────────────────┐
│                    Provider Selection                            │
│                                                                   │
│  Input: preferred_model = "google/gemini-2.5-pro"               │
│                                                                   │
│  Step 1: Identify Provider from Model Name                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ if "google/gemini-" in model:                              │ │
│  │     provider = "gemini"                                    │ │
│  │ elif "openrouter/" in model:                               │ │
│  │     provider = "openrouter"                                │ │
│  │ else:                                                      │ │
│  │     provider = "default"                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Step 2: Build Provider List                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ providers_to_try = []                                      │ │
│  │                                                            │ │
│  │ # Add preferred provider first                            │ │
│  │ if preferred_provider.is_available:                       │ │
│  │     providers_to_try.append(preferred_provider)           │ │
│  │                                                            │ │
│  │ # Add remaining available providers                       │ │
│  │ for provider in all_providers:                            │ │
│  │     if provider.is_available and provider not in list:    │ │
│  │         providers_to_try.append(provider)                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Step 3: Normalize Model for Each Provider                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Gemini:      "google/gemini-2.5-pro"                       │ │
│  │              → "gemini/gemini-2.5-pro"                     │ │
│  │                                                            │ │
│  │ OpenRouter:  "google/gemini-2.5-pro"                       │ │
│  │              → "openrouter/google/gemma-3-4b-it:free"      │ │
│  │                                                            │ │
│  │ Bytez:       "google/gemini-2.5-pro"                       │ │
│  │              → "google/gemini-2.5-flash"                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                      Error Types & Actions                       │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ APIConnectionError / RateLimitError                       │  │
│  │ ├─ Log error                                              │  │
│  │ ├─ Increment failure count                                │  │
│  │ ├─ Exponential backoff (2^n seconds, max 10s)            │  │
│  │ └─ Try next provider                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ AuthenticationError                                        │  │
│  │ ├─ Mark provider as unavailable                           │  │
│  │ ├─ Log authentication failure                             │  │
│  │ └─ Skip to next provider (no retry)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ BadRequestError                                            │  │
│  │ ├─ If JSON mode enabled:                                  │  │
│  │ │   ├─ Retry without JSON mode                            │  │
│  │ │   └─ If succeeds, return response                       │  │
│  │ ├─ Increment failure count                                │  │
│  │ └─ Try next provider                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Timeout (>60s)                                             │  │
│  │ ├─ Log timeout                                             │  │
│  │ ├─ Increment failure count                                │  │
│  │ └─ Try next provider                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Health Tracking System

```
┌─────────────────────────────────────────────────────────────────┐
│                    Provider Health Status                        │
│                                                                   │
│  Each Provider Tracks:                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ • is_available: bool                                       │ │
│  │ • failure_count: int                                       │ │
│  │ • last_error: str                                          │ │
│  │ • last_error_time: timestamp                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Call History Tracks:                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ • provider: str                                            │ │
│  │ • model: str                                               │ │
│  │ • status: "success" | "failed" | "auth_failed"            │ │
│  │ • error: str (if failed)                                   │ │
│  │ • timestamp: float                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Success Updates:                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ provider.failure_count = 0                                 │ │
│  │ provider.last_error = None                                 │ │
│  │ call_history.append({"status": "success", ...})            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Failure Updates:                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ provider.failure_count += 1                                │ │
│  │ provider.last_error = str(error)                           │ │
│  │ provider.last_error_time = time.time()                     │ │
│  │ call_history.append({"status": "failed", ...})             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Example

```
User: "Write a blog about AI"
    │
    ▼
FinolAutomation.run_writing_pipeline()
    │
    ├─ Research Phase
    │   └─ ai_call("SEO specialist", "Find keywords")
    │       └─ ProviderManager.ai_call()
    │           ├─ Try Gemini → ❌ Rate limit
    │           ├─ Wait 2s
    │           ├─ Try OpenRouter → ✅ Success
    │           └─ Return keywords
    │
    ├─ Outline Phase
    │   └─ ai_call("Outline planner", "Create structure")
    │       └─ ProviderManager.ai_call()
    │           ├─ Try Gemini → ✅ Success
    │           └─ Return outline
    │
    └─ Writing Phase (for each section)
        └─ ai_call("Section writer", "Write section 1")
            └─ ProviderManager.ai_call()
                ├─ Try Gemini → ❌ Timeout
                ├─ Wait 2s
                ├─ Try OpenRouter → ❌ Connection error
                ├─ Wait 4s
                ├─ Try Bytez → ✅ Success
                └─ Return section content
```

## Performance Characteristics

```
┌─────────────────────────────────────────────────────────────────┐
│                    Timing Analysis                               │
│                                                                   │
│  Best Case (First Provider Succeeds):                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ API Call: 1-3 seconds                                      │ │
│  │ Total: 1-3 seconds                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Fallback Case (Second Provider Succeeds):                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ First API Call: 1-3 seconds (fails)                        │ │
│  │ Backoff: 2 seconds                                         │ │
│  │ Second API Call: 1-3 seconds (succeeds)                    │ │
│  │ Total: 4-8 seconds                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Worst Case (Third Provider Succeeds):                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ First API Call: 1-3 seconds (fails)                        │ │
│  │ Backoff: 2 seconds                                         │ │
│  │ Second API Call: 1-3 seconds (fails)                       │ │
│  │ Backoff: 4 seconds                                         │ │
│  │ Third API Call: 1-3 seconds (succeeds)                     │ │
│  │ Total: 9-15 seconds                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Provider Independence
Each provider is isolated with its own configuration, allowing independent failure tracking and recovery.

### 2. Exponential Backoff
Prevents overwhelming failing providers while giving them time to recover from rate limits.

### 3. Model Normalization
Automatically adapts model names for each provider, ensuring compatibility without user intervention.

### 4. Health Tracking
Maintains provider health status for monitoring and debugging without affecting runtime behavior.

### 5. JSON Mode Fallback
Automatically retries without JSON mode if a model doesn't support it, maximizing compatibility.

### 6. No Circuit Breaking
Providers are never permanently disabled (except auth failures), allowing recovery from temporary issues.

## Extension Points

### Adding New Providers
```python
# In provider_manager.py
def _initialize_providers(self):
    return [
        ProviderConfig("gemini", "GOOGLE_API_KEY"),
        ProviderConfig("openrouter", "OPENROUTER_API_KEY", ...),
        ProviderConfig("bytez", "BYTEZ_API_KEY", ...),
        ProviderConfig("custom", "CUSTOM_API_KEY", "https://api.custom.com"),  # New
    ]

# Implement custom API call if needed
def _call_custom_api(self, model, messages, json_mode, timeout):
    # Custom implementation
    pass
```

### Custom Retry Logic
```python
# In provider_manager.py
self.retry_backoff_base = 3  # Change from 2 to 3
self.max_retries = 5  # Change from 3 to 5
```

### Provider Priority
```python
# Reorder providers in _initialize_providers()
return [
    ProviderConfig("bytez", ...),      # Try Bytez first
    ProviderConfig("gemini", ...),     # Then Gemini
    ProviderConfig("openrouter", ...),  # Then OpenRouter
]
```
