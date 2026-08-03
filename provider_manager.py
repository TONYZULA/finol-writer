"""
OpenRouter-only AI provider manager for blog automation.

Uses the user's OpenRouter API key (OPENROUTER_API_KEY) to call free
chat models with a fallback ladder. Plain `requests`, no litellm.

  Base URL : https://openrouter.ai/api/v1
  Auth     : Authorization: Bearer <key>
  Endpoint : POST /chat/completions (OpenAI-compatible)

Free-model enforcement: all ladder entries are :free-suffixed IDs that
are currently served by OpenRouter.
"""

import time
import json
import requests
from typing import Dict, List, Optional

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_CHAT_URL = f"{OPENROUTER_BASE_URL}/chat/completions"
OPENROUTER_MODELS_URL = f"{OPENROUTER_BASE_URL}/models"

# Model ladder, best first. All entries are :free models currently served.
FREE_OR_MODELS: List[str] = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-20b:free",
    "inclusionai/ling-3.0-flash:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-4-31b-it:free",
]


class ProviderConfig:
    """Holds runtime state for one provider slot."""

    def __init__(self, name: str, api_key: str, base_url: Optional[str] = None):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.is_available = bool(api_key)
        self.failure_count = 0
        self.last_error = None
        self.last_error_time = None


class ProviderManager:
    """
    Manages the OpenRouter provider slot with a free-model fallback ladder.
    """

    def __init__(self, secrets_dict: Dict[str, str]):
        self.secrets = secrets_dict
        self.call_history: List[Dict] = []
        self.retry_backoff_base = 2
        self.providers = self._build_providers()

    # ------------------------------------------------------------------
    # Provider initialisation
    # ------------------------------------------------------------------

    def _build_providers(self) -> List[ProviderConfig]:
        """Build ordered provider list from secrets."""
        providers: List[ProviderConfig] = []
        key = self.secrets.get("OPENROUTER_API_KEY", "")
        if key:
            providers.append(
                ProviderConfig("openrouter", key, OPENROUTER_BASE_URL)
            )
        return providers

    # ------------------------------------------------------------------
    # Introspection (used by automation.py + provider_dashboard.py)
    # ------------------------------------------------------------------

    def get_available_providers(self) -> List[str]:
        return [p.name for p in self.providers if p.is_available]

    def get_provider_status(self) -> Dict:
        status: Dict = {}
        for p in self.providers:
            status[p.name] = {
                "available": p.is_available,
                "failures": p.failure_count,
                "last_error": p.last_error,
                "last_error_time": p.last_error_time,
            }
        return status

    def get_call_history(self, limit: int = 50) -> List[Dict]:
        return self.call_history[-limit:]

    def _log(self, provider: str, status: str, model: str = None, error: str = None):
        self.call_history.append({
            "provider": provider,
            "status": status,
            "timestamp": time.time(),
            "model": model,
            "error": error,
        })

    def _record_failure(self, provider: ProviderConfig, error: Exception):
        provider.failure_count += 1
        provider.last_error = str(error)[:500]
        provider.last_error_time = time.time()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ai_call(
        self,
        system_prompt: str,
        user_prompt: str,
        preferred_model: Optional[str] = None,
        json_mode: bool = True,
    ) -> str:
        """
        Make an AI call through OpenRouter with a model fallback ladder.
        Returns the content string (JSON text when json_mode=True).
        """
        providers = [p for p in self.providers if p.is_available]
        if not providers:
            raise RuntimeError(
                "No AI provider configured. Add OPENROUTER_API_KEY to your "
                "Streamlit Secrets (Settings → Secrets) or set it as the "
                "OPENROUTER_API_KEY environment variable."
            )

        provider = providers[0]
        ladder = self._model_ladder(preferred_model)

        last_error: Optional[Exception] = None
        attempt = 1
        for model in ladder:
            try:
                content = self._call_openrouter(
                    provider, system_prompt, user_prompt, model, json_mode
                )
                provider.failure_count = 0
                self._log("openrouter", "success", model=model)
                return content
            except Exception as e:
                last_error = e
                self._record_failure(provider, e)
                self._log("openrouter", "failed", model=model, error=str(e)[:300])
                if attempt < len(ladder):
                    time.sleep(min(self.retry_backoff_base ** attempt, 10))
                attempt += 1

        raise RuntimeError(
            f"All OpenRouter models failed. Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _model_ladder(self, preferred: Optional[str]) -> List[str]:
        """Build a deduped model list with the preferred model first."""
        ladder: List[str] = []
        if preferred:
            m = preferred.strip()
            # Only honor a preferred model that is a valid OpenRouter ID
            # (free-suffixed or an explicit :free/auto id). Legacy Bytez
            # ids like "Qwen/Qwen3-4B" are skipped.
            if m.endswith(":free") or m == "openrouter/auto":
                ladder.append(m)
        ladder.extend(FREE_OR_MODELS)

        seen: set = set()
        out: List[str] = []
        for m in ladder:
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out

    def _call_openrouter(
        self,
        provider: ProviderConfig,
        system_prompt: str,
        user_prompt: str,
        model: str,
        json_mode: bool,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        resp = requests.post(
            OPENROUTER_CHAT_URL, headers=headers, json=payload, timeout=90
        )

        if resp.status_code != 200:
            try:
                err = resp.json().get("error", {}).get("message") or resp.text[:300]
            except Exception:
                err = resp.text[:300]
            raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {err}")

        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(
                f"Unexpected OpenRouter response: {json.dumps(data)[:300]}"
            )

        if content is None:
            raise RuntimeError(f"OpenRouter returned empty content for model {model}")

        return str(content).strip()
