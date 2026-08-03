# SKILL.md — FINOL Blog Automation

Guide for AI agents working in this repo. Read before editing.

## What this is

A Streamlit app that auto-generates SEO blog drafts via **OpenRouter free models**
(research backed by Tavily) and publishes them to **WordPress**. Single-provider,
OpenRouter-only architecture — no more Bytez/AIML/Google providers.

## Tech stack

- Python 3.11 (pinned in `runtime.txt` for Streamlit Cloud)
- `streamlit` UI (`app.py`)
- Plain `requests` to OpenRouter (NO litellm — do not reintroduce it)
- `tavily-python` for web research
- `markdown` for rendering drafts

## File map

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI: tabs Write Article / Provider Monitor / Debug, sidebar settings, model selector |
| `automation.py` | `FinolAutomation` — full writing pipeline (SEO → outline → sections), WordPress publishing, Tavily research |
| `provider_manager.py` | `ProviderManager` — OpenRouter calls, `FREE_OR_MODELS` fallback ladder, health tracking, backoff |
| `provider_dashboard.py` | Reusable Streamlit monitoring components (`show_provider_status`, `show_call_history`, `show_model_selector`, `show_provider_selector`, `show_fallback_info`, `show_debug_panel`) |
| `text_sanitizer.py` | Strips non-printable chars before publishing |
| `test_fallback.py` | Network-free unit tests + live integration tests |
| `.streamlit/secrets.toml` | Local secrets (gitignored). Template: `.streamlit/secrets.toml.example` + `SECRETS_TEMPLATE.toml` |
| `deploy.sh` | Deployment helper |

## Core workflow (writing pipeline)

1. Tavily research on topic + user-provided knowledge base URLs
2. SEO metadata call (`json_mode=True`)
3. Outline call (`json_mode=True`)
4. Section-by-section content generation
5. Draft assembled in Markdown, shown in the editor, then published to WordPress

Each step calls `provider_manager.ai_call(...)` which walks the fallback ladder.

## Key API facts

- Base URL: `https://openrouter.ai/api/v1`
- Endpoint: `POST /chat/completions` (OpenAI-compatible), `Authorization: Bearer <key>`
- JSON mode: pass `response_format={"type": "json_object"}` in the payload
- Model ladder (`FREE_OR_MODELS` in `provider_manager.py`), best first:
  `google/gemma-4-26b-a4b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` →
  `openai/gpt-oss-20b:free` → `inclusionai/ling-3.0-flash:free` →
  `nvidia/nemotron-nano-9b-v2:free` → `google/gemma-4-31b-it:free`
- **Only `:free`-suffixed model IDs are valid.** Legacy Bytez IDs must never be used.
- Backoff: `2^attempt` seconds, capped at 10s. Triggers on 429/5xx/404/timeouts/empty responses.

## Secrets / keys (CRITICAL)

Required in Streamlit Secrets **and** supported as env vars:

```toml
OPENROUTER_API_KEY = "sk-or-v1-..."   # required for all AI calls
TAVILY_API_KEY = "tvly-..."           # required for research
```

- Never commit a real API key. **GitHub push protection will block any push containing a real key.**
- Local `.streamlit/secrets.toml` is gitignored — the real key lives only there.
- Committed templates must contain the placeholder `sk-or-v1-your-openrouter-api-key`.
- On Streamlit Cloud the user adds keys via Settings → Secrets (I cannot do it — it's manual).
- `automation.py` reads keys from `st.secrets`, falling back to `os.environ`.

## Model selection in the UI

- The AI model dropdown lives on the **📊 Provider Monitor tab** (`show_model_selector`).
- Choice persists in `st.session_state["selected_model"]`, drives generation + publishing.
- The sidebar shows the selected model read-only. Keep this pattern — don't put a second selectbox with the same key in the sidebar.

## Verification workflow

- Syntax check after edits:
  ```bash
  python3 -m py_compile app.py automation.py provider_manager.py provider_dashboard.py text_sanitizer.py
  ```
- Run unit tests (network-free, do not need keys):
  ```bash
  python3 test_fallback.py
  ```
- Live integration tests in `test_fallback.py` DO hit OpenRouter and need `OPENROUTER_API_KEY` set — skip if no key.
- No streamlit/tavily installed locally; testing uses plain `python3` + `requests` + `markdown`.

## Gotchas

- `provider_dashboard.show_debug_panel` must keep existing, `app.py` imports it.
- `automation.py` interface (`FinolAutomation(model)`, `provider_manager`, `ai_call`) is depended on by `app.py` and `provider_dashboard.py` — don't break signatures.
- JSON parsing failures are auto-recovered (embedded JSON extraction) or fall back to safe defaults.
- If the app shows "No AI provider configured" → `OPENROUTER_API_KEY` is missing from secrets/env.
- Don't add comments to code unless asked.

## Common tasks

- **Add/edit free models**: update `FREE_OR_MODELS` in `provider_manager.py` (and `FREE_MODELS` in `provider_dashboard.py` to keep the UI list in sync). Verify the model exists via `GET /api/v1/models`.
- **Deploy**: push to GitHub → Streamlit Cloud redeploys → secrets must already be set.
