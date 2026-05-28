"""
Multi-provider AI fallback system for blog automation.
Providers (in fallback order):
  1. AIML API key 1  (auto)
  2. AIML API key 2  (muli)
  3. AIML API key 3  (harsi)
  4. OpenRouter key 1  ← FREE MODELS ONLY (enforced)
  5. OpenRouter key 2  ← FREE MODELS ONLY (enforced)
  6. OpenRouter key 3  ← FREE MODELS ONLY (enforced)
  7. Gemini key 1
  8. Gemini key 2

AIML API is fully OpenAI-compatible:
  Base URL : https://api.aimlapi.com/v1
  Auth     : Bearer <key>

OpenRouter free-model enforcement:
  - All model IDs are suffixed with :free
  - A curated FREE_OR_MODELS list is used for rotation
"""

import os
import time
import json
import random
import requests
import streamlit as st
from typing import Dict, List, Optional
from litellm import completion
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
    APIError,
)


# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------
AIML_DEFAULT_MODEL   = "google/gemini-2.0-flash"
GEMINI_DEFAULT_MODEL = "gemini/gemini-2.0-flash"

# Curated list of reliable FREE OpenRouter models (all end with :free)
FREE_OR_MODELS: List[str] = [
    "openrouter/google/gemma-3-27b-it:free",
    "openrouter/google/gemma-3-12b-it:free",
    "openrouter/google/gemma-3-4b-it:free",
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/meta-llama/llama-3.2-3b-instruct:free",
    "openrouter/mistralai/mistral-small-3.1-24b-instruct:free",
    "openrouter/qwen/qwen3-4b:free",
    "openrouter/qwen/qwen3-coder:free",
    "openrouter/nousresearch/hermes-3-llama-3.1-405b:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
]


def _enforce_free_or_model(model: Optional[str]) -> str:
    """
    Given any model string, return a guaranteed-free OpenRouter model.
    - If the model already ends with :free, keep it (add openrouter/ prefix if missing).
    - Otherwise, pick the first model from FREE_OR_MODELS.
    """
    if not model:
        return FREE_OR_MODELS[0]
    m = model.strip()
    # Already a free OR model
    if m.endswith(":free"):
        if not m.startswith("openrouter/"):
            m = f"openrouter/{m}"
        return m
    # Not free → use default free model
    return FREE_OR_MODELS[0]


class ProviderConfig:
    """Holds runtime state for one provider slot."""

    def __init__(self, name: str, api_key: str, base_url: Optional[str] = None):
        self.name          = name
        self.api_key       = api_key
        self.base_url      = base_url
        self.is_available  = bool(api_key)
        self.failure_count = 0
        self.last_error    = None
        self.last_error_time = None


class ProviderManager:
    """
    Manages multiple AI provider slots with intelligent fallback and rotation.
    Each key is an independent slot — rate-limiting one auto-rolls to the next.
    """

    def __init__(self, secrets_dict: Dict[str, str]):
        self.secrets = secrets_dict
        self.call_history: List[Dict] = []
        self.retry_backoff_base = 2   # wait = base^n seconds, capped at 10 s
        self.providers = self._build_providers()

    # ------------------------------------------------------------------
    # Provider initialisation
    # ------------------------------------------------------------------

    def _build_providers(self) -> List[ProviderConfig]:
        """Build ordered provider list from secrets."""
        providers: List[ProviderConfig] = []

        # ── AIML API (3 slots) ────────────────────────────────────────
        for slot, env_key in [
            ("aiml_1", "AIML_API_KEY_1"),
            ("aiml_2", "AIML_API_KEY_2"),
            ("aiml_3", "AIML_API_KEY_3"),
        ]:
            key = self.secrets.get(env_key, "")
            if key:
                providers.append(
                    ProviderConfig(slot, key, "https://api.aimlapi.com/v1")
                )

        # ── OpenRouter (3 slots, FREE MODELS ONLY) ───────────────────
        for slot, env_key in [
            ("openrouter_1", "OPENROUTER_API_KEY_1"),
            ("openrouter_2", "OPENROUTER_API_KEY_2"),
            ("openrouter_3", "OPENROUTER_API_KEY_3"),
        ]:
            key = self.secrets.get(env_key, "")
            if key:
                providers.append(
                    ProviderConfig(slot, key, "https://openrouter.ai/api/v1")
                )

        # ── Gemini (2 slots via litellm) ─────────────────────────────
        for slot, env_key in [
            ("gemini_1", "GOOGLE_API_KEY"),
            ("gemini_2", "GOOGLE_API_KEY_2"),
        ]:
            key = self.secrets.get(env_key, "")
            if key:
                os.environ[env_key] = key
                providers.append(ProviderConfig(slot, key))

        return providers

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_available_providers(self) -> List[str]:
        return [p.name for p in self.providers if p.is_available]

    def get_provider_status(self) -> Dict:
        return {
            p.name: {
                "available":       p.is_available,
                "failures":        p.failure_count,
                "last_error":      p.last_error,
                "last_error_time": p.last_error_time,
            }
            for p in self.providers
        }

    def get_call_history(self, limit: int = 20) -> List[Dict]:
        return self.call_history[-limit:]

    # ------------------------------------------------------------------
    # Core call
    # ------------------------------------------------------------------

    def ai_call(
        self,
        system_prompt: str,
        user_prompt: str,
        preferred_model: str = None,
        json_mode: bool = True,
    ) -> str:
        """Try each provider in order until one succeeds."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        failed: List[str] = []
        last_error = None

        for provider in self.providers:
            if not provider.is_available:
                continue

            try:
                content = self._call_provider(
                    provider, messages, preferred_model, json_mode
                )
                # ── success ──────────────────────────────────────────
                provider.failure_count = 0
                provider.last_error    = None
                self._log("success", provider.name,
                          self._model_for(provider, preferred_model))
                return content

            except Exception as e:
                last_error = e
                err_str    = str(e)
                status     = self._http_status(e)

                if status == 401:
                    provider.is_available = False

                provider.failure_count  += 1
                provider.last_error      = err_str[:200]
                provider.last_error_time = time.time()
                failed.append(provider.name)
                self._log("failed", provider.name,
                          self._model_for(provider, preferred_model), err_str)

                if provider is not self.providers[-1]:
                    wait = min(self.retry_backoff_base ** len(failed), 10)
                    time.sleep(wait)

        raise RuntimeError(
            f"All {len(failed)} provider slot(s) failed.\n"
            + "\n".join(
                f"  {p.name}: {p.last_error}"
                for p in self.providers
                if p.name in failed
            )
        )

    # ------------------------------------------------------------------
    # Per-provider dispatch
    # ------------------------------------------------------------------

    def _call_provider(
        self,
        provider: ProviderConfig,
        messages: List[Dict],
        preferred_model: Optional[str],
        json_mode: bool,
    ) -> str:
        model = self._model_for(provider, preferred_model)

        # ── AIML API ─────────────────────────────────────────────────
        if provider.name.startswith("aiml_"):
            return self._call_openai_compat(
                provider.api_key, provider.base_url,
                model, messages, json_mode
            )

        # ── OpenRouter (FREE MODELS ONLY) ────────────────────────────
        if provider.name.startswith("openrouter_"):
            free_model = _enforce_free_or_model(preferred_model)
            return self._call_openai_compat(
                provider.api_key, provider.base_url,
                free_model, messages, json_mode,
                extra_headers={
                    "HTTP-Referer": "https://finol-writer.streamlit.app",
                    "X-Title": "FINOL Blog Writer",
                }
            )

        # ── Gemini via litellm ────────────────────────────────────────
        if provider.name.startswith("gemini_"):
            os.environ["GOOGLE_API_KEY"] = provider.api_key
            resp = completion(
                model=model,
                messages=messages,
                response_format={"type": "json_object"} if json_mode else None,
                timeout=60,
            )
            return resp.choices[0].message.content or ""

        raise ValueError(f"Unknown provider slot: {provider.name}")

    # ------------------------------------------------------------------
    # Generic OpenAI-compatible call (AIML + OpenRouter)
    # ------------------------------------------------------------------

    def _call_openai_compat(
        self,
        api_key: str,
        base_url: str,
        model: str,
        messages: List[Dict],
        json_mode: bool,
        extra_headers: Optional[Dict] = None,
        timeout: int = 60,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        payload: Dict = {
            "model":    model,
            "messages": messages,
            "stream":   False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "") or ""
        return json.dumps(data)

    # ------------------------------------------------------------------
    # Model name helpers
    # ------------------------------------------------------------------

    def _model_for(self, provider: ProviderConfig, preferred: Optional[str]) -> str:
        if provider.name.startswith("aiml_"):
            return self._aiml_model(preferred)
        if provider.name.startswith("openrouter_"):
            return _enforce_free_or_model(preferred)
        if provider.name.startswith("gemini_"):
            return self._gemini_model(preferred)
        return preferred or "default"

    def _aiml_model(self, preferred: Optional[str]) -> str:
        if not preferred or preferred == "default":
            return AIML_DEFAULT_MODEL
        if preferred.startswith("google/"):
            return preferred
        if preferred.startswith("gemini/"):
            return preferred.replace("gemini/", "google/", 1)
        if preferred.startswith("openrouter/"):
            return AIML_DEFAULT_MODEL
        return preferred

    def _gemini_model(self, preferred: Optional[str]) -> str:
        if not preferred or preferred == "default":
            return GEMINI_DEFAULT_MODEL
        if preferred.startswith("google/"):
            return preferred.replace("google/", "gemini/", 1)
        if preferred.startswith("gemini/"):
            return preferred
        return GEMINI_DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _http_status(exc: Exception) -> int:
        resp = getattr(exc, "response", None)
        if resp is not None:
            return getattr(resp, "status_code", 0)
        return 0

    def _log(self, status: str, provider: str, model: str, error: str = "") -> None:
        entry = {
            "provider":  provider,
            "model":     model,
            "status":    status,
            "timestamp": time.time(),
        }
        if error:
            entry["error"] = error[:200]
        self.call_history.append(entry)

import os
import time
import json
import requests
import streamlit as st
from typing import Dict, List, Optional
from litellm import completion
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
    APIError,
)


# ---------------------------------------------------------------------------
# Default models per provider
# ---------------------------------------------------------------------------
AIML_DEFAULT_MODEL  = "google/gemini-2.0-flash"   # fast, reliable on AIML
GEMINI_DEFAULT_MODEL = "gemini/gemini-2.0-flash"   # litellm prefix
OPENROUTER_DEFAULT  = "openrouter/google/gemma-3-4b-it:free"


class ProviderConfig:
    """Holds runtime state for one provider slot."""

    def __init__(self, name: str, api_key: str, base_url: Optional[str] = None):
        self.name          = name
        self.api_key       = api_key
        self.base_url      = base_url
        self.is_available  = bool(api_key)
        self.failure_count = 0
        self.last_error    = None
        self.last_error_time = None


class ProviderManager:
    """
    Manages multiple AI provider slots with intelligent fallback and rotation.
    Each AIML key is treated as an independent provider slot so that when one
    key is rate-limited the next key is tried automatically.
    """

    def __init__(self, secrets_dict: Dict[str, str]):
        self.secrets = secrets_dict
        self.call_history: List[Dict] = []
        self.retry_backoff_base = 2   # seconds; wait = base^n, capped at 10 s
        self.providers = self._build_providers()

    # ------------------------------------------------------------------
    # Provider initialisation
    # ------------------------------------------------------------------

    def _build_providers(self) -> List[ProviderConfig]:
        """Build ordered provider list from secrets."""
        providers: List[ProviderConfig] = []

        # ── AIML API keys (3 independent slots) ──────────────────────
        for slot, env_key in [
            ("aiml_1", "AIML_API_KEY_1"),
            ("aiml_2", "AIML_API_KEY_2"),
            ("aiml_3", "AIML_API_KEY_3"),
        ]:
            key = self.secrets.get(env_key, "")
            if key:
                providers.append(
                    ProviderConfig(slot, key, "https://api.aimlapi.com/v1")
                )

        # ── Gemini keys (2 independent slots via litellm) ────────────
        for slot, env_key in [
            ("gemini_1", "GOOGLE_API_KEY"),
            ("gemini_2", "GOOGLE_API_KEY_2"),
        ]:
            key = self.secrets.get(env_key, "")
            if key:
                os.environ[env_key] = key          # litellm reads env vars
                providers.append(ProviderConfig(slot, key))

        # ── OpenRouter (optional) ─────────────────────────────────────
        or_key = self.secrets.get("OPENROUTER_API_KEY", "")
        if or_key:
            os.environ["OPENROUTER_API_KEY"] = or_key
            providers.append(
                ProviderConfig("openrouter", or_key, "https://openrouter.ai/api/v1")
            )

        return providers

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_available_providers(self) -> List[str]:
        return [p.name for p in self.providers if p.is_available]

    def get_provider_status(self) -> Dict:
        return {
            p.name: {
                "available":       p.is_available,
                "failures":        p.failure_count,
                "last_error":      p.last_error,
                "last_error_time": p.last_error_time,
            }
            for p in self.providers
        }

    def get_call_history(self, limit: int = 20) -> List[Dict]:
        return self.call_history[-limit:]

    # ------------------------------------------------------------------
    # Core call
    # ------------------------------------------------------------------

    def ai_call(
        self,
        system_prompt: str,
        user_prompt: str,
        preferred_model: str = None,
        json_mode: bool = True,
    ) -> str:
        """
        Try each provider in order until one succeeds.
        Returns the raw content string (caller handles JSON parsing).
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        failed: List[str] = []
        last_error = None

        for provider in self.providers:
            if not provider.is_available:
                continue

            try:
                content = self._call_provider(
                    provider, messages, preferred_model, json_mode
                )

                # ── success ──────────────────────────────────────────
                provider.failure_count = 0
                provider.last_error    = None
                self._log("success", provider.name,
                          self._model_for(provider, preferred_model))
                return content

            except Exception as e:
                last_error = e
                err_str    = str(e)
                status     = self._http_status(e)

                # Permanent auth failure → disable slot
                if status == 401:
                    provider.is_available = False

                provider.failure_count  += 1
                provider.last_error      = err_str[:200]
                provider.last_error_time = time.time()
                failed.append(provider.name)
                self._log("failed", provider.name,
                          self._model_for(provider, preferred_model), err_str)

                # Brief pause before next provider (skip on last)
                if provider is not self.providers[-1]:
                    wait = min(self.retry_backoff_base ** len(failed), 10)
                    time.sleep(wait)

        raise RuntimeError(
            f"All {len(failed)} provider(s) failed.\n"
            + "\n".join(f"  {n}: {self.providers[[p.name for p in self.providers].index(n)].last_error}"
                        for n in failed if n in [p.name for p in self.providers])
        )

    # ------------------------------------------------------------------
    # Per-provider dispatch
    # ------------------------------------------------------------------

    def _call_provider(
        self,
        provider: ProviderConfig,
        messages: List[Dict],
        preferred_model: Optional[str],
        json_mode: bool,
    ) -> str:
        model = self._model_for(provider, preferred_model)

        # ── AIML API (OpenAI-compatible, direct requests) ─────────────
        if provider.name.startswith("aiml_"):
            return self._call_aiml(provider, model, messages, json_mode)

        # ── Gemini via litellm ────────────────────────────────────────
        if provider.name.startswith("gemini_"):
            # Set the correct env var for litellm
            env_key = "GOOGLE_API_KEY" if provider.name == "gemini_1" else "GOOGLE_API_KEY_2"
            os.environ["GOOGLE_API_KEY"] = provider.api_key
            gemini_model = self._gemini_model(preferred_model)
            resp = completion(
                model=gemini_model,
                messages=messages,
                response_format={"type": "json_object"} if json_mode else None,
                timeout=60,
            )
            return resp.choices[0].message.content or ""

        # ── OpenRouter via litellm ────────────────────────────────────
        if provider.name == "openrouter":
            or_model = self._openrouter_model(preferred_model)
            resp = completion(
                model=or_model,
                messages=messages,
                response_format={"type": "json_object"} if json_mode else None,
                base_url=provider.base_url,
                timeout=60,
            )
            return resp.choices[0].message.content or ""

        raise ValueError(f"Unknown provider: {provider.name}")

    # ------------------------------------------------------------------
    # AIML API call
    # ------------------------------------------------------------------

    def _call_aiml(
        self,
        provider: ProviderConfig,
        model: str,
        messages: List[Dict],
        json_mode: bool,
        timeout: int = 60,
    ) -> str:
        """Call AIML API (OpenAI-compatible endpoint)."""
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type":  "application/json",
        }
        payload: Dict = {
            "model":    model,
            "messages": messages,
            "stream":   False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(
            f"{provider.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Standard OpenAI-compatible response
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "") or ""

        # Fallback: return raw JSON string
        return json.dumps(data)

    # ------------------------------------------------------------------
    # Model name helpers
    # ------------------------------------------------------------------

    def _model_for(self, provider: ProviderConfig, preferred: Optional[str]) -> str:
        """Return the best model name for a given provider slot."""
        if provider.name.startswith("aiml_"):
            return self._aiml_model(preferred)
        if provider.name.startswith("gemini_"):
            return self._gemini_model(preferred)
        if provider.name == "openrouter":
            return self._openrouter_model(preferred)
        return preferred or "default"

    def _aiml_model(self, preferred: Optional[str]) -> str:
        """Map the UI model selection to an AIML API model ID."""
        if not preferred or preferred == "default":
            return AIML_DEFAULT_MODEL
        # If user picked a google/gemini model, use it directly on AIML
        if preferred.startswith("google/"):
            return preferred
        # If user picked gemini/ (litellm prefix), strip prefix
        if preferred.startswith("gemini/"):
            return preferred.replace("gemini/", "google/", 1)
        # OpenRouter models → map to AIML equivalent
        if preferred.startswith("openrouter/"):
            return AIML_DEFAULT_MODEL
        return preferred

    def _gemini_model(self, preferred: Optional[str]) -> str:
        """Return a litellm-compatible Gemini model string."""
        if not preferred or preferred == "default":
            return GEMINI_DEFAULT_MODEL
        if preferred.startswith("google/"):
            return preferred.replace("google/", "gemini/", 1)
        if preferred.startswith("gemini/"):
            return preferred
        return GEMINI_DEFAULT_MODEL

    def _openrouter_model(self, preferred: Optional[str]) -> str:
        if not preferred or preferred == "default":
            return OPENROUTER_DEFAULT
        if preferred.startswith("openrouter/"):
            return preferred
        return OPENROUTER_DEFAULT

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _http_status(exc: Exception) -> int:
        """Extract HTTP status code from an exception if available."""
        resp = getattr(exc, "response", None)
        if resp is not None:
            return getattr(resp, "status_code", 0)
        return 0

    def _log(self, status: str, provider: str, model: str, error: str = "") -> None:
        entry = {
            "provider":  provider,
            "model":     model,
            "status":    status,
            "timestamp": time.time(),
        }
        if error:
            entry["error"] = error[:200]
        self.call_history.append(entry)
