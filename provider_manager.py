"""
AI provider manager for blog automation.
Bytez-only implementation with health tracking and retry logic.
"""

import os
import json
import time
import requests
import streamlit as st
from typing import Dict, List, Optional, Tuple
from litellm import completion
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
    APIError,
)
from requests.exceptions import HTTPError as RequestsHTTPError, RequestException


class ProviderConfig:
    """Configuration for each AI provider."""
    
    def __init__(self, name: str, api_key_env: str, base_url: Optional[str] = None):
        self.name = name
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.api_key = os.environ.get(api_key_env, "")
        self.is_available = bool(self.api_key)
        self.failure_count = 0
        self.last_error = None
        self.last_error_time = None


class ProviderManager:
    """
    Manages multiple AI providers with intelligent fallback and rotation.
    Tracks provider health and automatically switches on failures.
    """
    
    def __init__(self, secrets_dict: Dict[str, str]):
        """
        Initialize provider manager with API keys from secrets.
        
        Args:
            secrets_dict: Dictionary containing API keys and configuration
        """
        self.secrets = secrets_dict
        self._setup_environment()
        self.providers = self._initialize_providers()
        self.provider_rotation_index = 0
        self.call_history = []
        self.max_retries = 3
        self.retry_backoff_base = 2  # exponential backoff: 2^n seconds
        
    def _setup_environment(self):
        """Set up environment variables for Bytez."""
        os.environ["BYTEZ_API_KEY"] = self.secrets.get("BYTEZ_API_KEY", "")
    
    def _initialize_providers(self) -> List[ProviderConfig]:
        """Initialize only the Bytez provider as requested."""
        return [
            ProviderConfig("bytez", "BYTEZ_API_KEY", "https://api.bytez.com/models/v2/openai/v1"),
        ]
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return [p.name for p in self.providers if p.is_available]
    
    def get_provider_status(self) -> Dict:
        """Get health status of all providers."""
        return {
            p.name: {
                "available": p.is_available,
                "failures": p.failure_count,
                "last_error": p.last_error,
                "last_error_time": p.last_error_time,
            }
            for p in self.providers
        }
    
    def _get_next_provider(self, exclude_providers: List[str] = None) -> Optional[ProviderConfig]:
        """
        Get next available provider in rotation, excluding failed ones.
        
        Args:
            exclude_providers: List of provider names to skip
            
        Returns:
            Next available ProviderConfig or None if all failed
        """
        exclude_providers = exclude_providers or []
        available = [
            p for p in self.providers 
            if p.is_available and p.name not in exclude_providers
        ]
        
        if not available:
            return None
        
        # Rotate through available providers
        self.provider_rotation_index = (self.provider_rotation_index + 1) % len(available)
        return available[self.provider_rotation_index]
    
    def _normalize_model_for_provider(self, model: str, provider: str) -> str:
        """
        Normalize model name for specific provider.
        
        Args:
            model: Original model identifier
            provider: Target provider name
            
        Returns:
            Normalized model name for the provider
        """
        if provider == "bytez":
            # Bytez accepts direct model identifiers; keep as-is when provided.
            # Fallback to a safe default if the model is missing.
            if not model or model == "default":
                return "google/gemini-2.5-flash"
            return model
        
        return model
    
    # Fallback model ladder tried in order when the primary model 500s
    BYTEZ_FALLBACK_MODELS = [
        "google/gemini-2.5-flash",
        "google/gemini-2.0-flash",
        "meta-llama/Llama-3.1-8B-Instruct",
    ]

    def _call_bytez_api(self, model: str, messages: List[Dict],
                        json_mode: bool = True, timeout: int = 60) -> str:
        """
        Direct call to Bytez API with per-model retry and fallback ladder.

        On 5xx errors the method retries up to 2 times with exponential
        back-off, then moves to the next model in BYTEZ_FALLBACK_MODELS.
        4xx errors are re-raised immediately (caller handles auth/rate).

        Args:
            model: Bytez model identifier
            messages: Message list for the API
            json_mode: Whether to request JSON response
            timeout: Request timeout in seconds

        Returns:
            Response content string
        """
        from requests.exceptions import HTTPError as RequestsHTTPError

        api_key = self.secrets.get("BYTEZ_API_KEY", "")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Build model ladder: requested model first, then fallbacks (deduped)
        seen = set()
        ladder = []
        for m in [model] + self.BYTEZ_FALLBACK_MODELS:
            if m and m not in seen:
                seen.add(m)
                ladder.append(m)

        last_exc = None
        for attempt_model in ladder:
            payload = {
                "model": attempt_model,
                "messages": messages,
                "stream": False,
            }
            for attempt in range(3):  # up to 3 tries per model
                try:
                    response = requests.post(
                        "https://api.bytez.com/models/v2/openai/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=timeout,
                    )
                    response.raise_for_status()
                    return response.json()["choices"][0]["message"]["content"]
                except RequestsHTTPError as e:
                    status = e.response.status_code if e.response is not None else 0
                    if status < 500:
                        # 4xx — no point retrying; propagate immediately
                        raise
                    # 5xx — wait and retry (or move to next model)
                    last_exc = e
                    if attempt < 2:
                        time.sleep(2 ** attempt)  # 1s, 2s
                    else:
                        break  # exhausted retries for this model
                except Exception as e:
                    last_exc = e
                    raise  # non-HTTP errors propagate immediately

        # All models and retries exhausted
        raise last_exc
    
    def ai_call(self, system_prompt: str, user_prompt: str, 
                preferred_model: str = None, json_mode: bool = True) -> str:
        """
        Make AI call with Bytez provider and retry logic.
        
        Args:
            system_prompt: System message for the AI
            user_prompt: User message for the AI
            preferred_model: Preferred model to try first
            json_mode: Whether to request JSON response
            
        Returns:
            Response content string
            
        Raises:
            RuntimeError: If all providers fail
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        failed_providers = []
        last_error = None
        
        # Try providers in order: preferred first, then rotation
        providers_to_try = []
        if preferred_model:
            for p in self.providers:
                if p.is_available and p.name in preferred_model.lower():
                    providers_to_try.append(p)
        
        # Add remaining available providers
        for p in self.providers:
            if p.is_available and p not in providers_to_try:
                providers_to_try.append(p)
        
        for provider in providers_to_try:
            try:
                normalized_model = self._normalize_model_for_provider(
                    preferred_model or "default", provider.name
                )
                
                if provider.name == "bytez":
                    content = self._call_bytez_api(
                        normalized_model, messages, json_mode
                    )
                else:
                    response = completion(
                        model=normalized_model,
                        messages=messages,
                        response_format={"type": "json_object"} if json_mode else None,
                        base_url=provider.base_url,
                        timeout=60,
                    )
                    content = response.choices[0].message.content or ""
                
                # Success: reset failure count
                provider.failure_count = 0
                provider.last_error = None
                
                # Log successful call
                self.call_history.append({
                    "provider": provider.name,
                    "model": normalized_model,
                    "status": "success",
                    "timestamp": time.time(),
                })
                
                return content
            
            except (APIConnectionError, RateLimitError, APIError) as e:
                provider.failure_count += 1
                provider.last_error = str(e)
                provider.last_error_time = time.time()
                failed_providers.append(provider.name)
                last_error = e
                
                # Log failed attempt
                self.call_history.append({
                    "provider": provider.name,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": time.time(),
                })
                
                # Exponential backoff before next attempt
                if provider != providers_to_try[-1]:
                    wait_time = self.retry_backoff_base ** len(failed_providers)
                    time.sleep(min(wait_time, 10))  # Cap at 10 seconds
                
                continue
            
            except RequestsHTTPError as e:
                # Raised by response.raise_for_status() in _call_bytez_api
                status_code = e.response.status_code if e.response is not None else 0
                error_msg = f"HTTP {status_code}: {str(e)}"
                
                if status_code in (401, 403):
                    # Auth failure — disable provider
                    provider.is_available = False
                    provider.last_error = f"Auth failed: {error_msg}"
                    provider.last_error_time = time.time()
                    self.call_history.append({
                        "provider": provider.name,
                        "status": "auth_failed",
                        "error": error_msg,
                        "timestamp": time.time(),
                    })
                else:
                    # Rate limit or server error — retry with backoff
                    provider.failure_count += 1
                    provider.last_error = error_msg
                    provider.last_error_time = time.time()
                    failed_providers.append(provider.name)
                    last_error = e
                    self.call_history.append({
                        "provider": provider.name,
                        "status": "failed",
                        "error": error_msg,
                        "timestamp": time.time(),
                    })
                    if provider != providers_to_try[-1]:
                        wait_time = self.retry_backoff_base ** len(failed_providers)
                        time.sleep(min(wait_time, 10))
                
                continue
            
            except RequestException as e:
                # Network-level errors (timeout, connection refused, etc.)
                provider.failure_count += 1
                provider.last_error = f"Network error: {str(e)}"
                provider.last_error_time = time.time()
                failed_providers.append(provider.name)
                last_error = e
                self.call_history.append({
                    "provider": provider.name,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": time.time(),
                })
                if provider != providers_to_try[-1]:
                    wait_time = self.retry_backoff_base ** len(failed_providers)
                    time.sleep(min(wait_time, 10))
                continue
            
            except AuthenticationError as e:
                provider.is_available = False
                provider.last_error = f"Auth failed: {str(e)}"
                provider.last_error_time = time.time()
                
                self.call_history.append({
                    "provider": provider.name,
                    "status": "auth_failed",
                    "error": str(e),
                    "timestamp": time.time(),
                })
                
                continue
            
            except BadRequestError as e:
                # Retry without JSON mode if that's the issue
                if json_mode:
                    try:
                        if provider.name == "bytez":
                            content = self._call_bytez_api(
                                normalized_model, messages, False
                            )
                        else:
                            response = completion(
                                model=normalized_model,
                                messages=messages,
                                base_url=provider.base_url,
                                timeout=60,
                            )
                            content = response.choices[0].message.content or ""
                        
                        provider.failure_count = 0
                        return content
                    except Exception:
                        pass
                
                provider.failure_count += 1
                provider.last_error = str(e)
                failed_providers.append(provider.name)
                continue
        
        # All providers failed
        error_summary = "\n".join([
            f"  {p}: {self.providers[[x.name for x in self.providers].index(p)].last_error}"
            for p in failed_providers
        ])
        raise RuntimeError(
            f"All AI providers failed after {len(failed_providers)} attempts:\n{error_summary}"
        )
    
    def get_call_history(self, limit: int = 10) -> List[Dict]:
        """Get recent call history for debugging."""
        return self.call_history[-limit:]
