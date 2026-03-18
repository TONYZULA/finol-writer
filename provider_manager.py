"""
Multi-provider AI fallback system for blog automation.
Intelligently rotates between Gemini, OpenRouter, and Bytez with automatic failover.
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
        """Set up environment variables for all providers."""
        os.environ["GOOGLE_API_KEY"] = self.secrets.get("GOOGLE_API_KEY", "")
        os.environ["OPENROUTER_API_KEY"] = self.secrets.get("OPENROUTER_API_KEY", "")
        os.environ["BYTEZ_API_KEY"] = self.secrets.get("BYTEZ_API_KEY", "")
        os.environ["OPENROUTER_API_BASE"] = self.secrets.get(
            "OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"
        )
        if self.secrets.get("OR_SITE_URL"):
            os.environ["OR_SITE_URL"] = self.secrets["OR_SITE_URL"]
        if self.secrets.get("OR_APP_NAME"):
            os.environ["OR_APP_NAME"] = self.secrets["OR_APP_NAME"]
    
    def _initialize_providers(self) -> List[ProviderConfig]:
        """Initialize all available providers."""
        return [
            ProviderConfig("gemini", "GOOGLE_API_KEY"),
            ProviderConfig("openrouter", "OPENROUTER_API_KEY", 
                          self.secrets.get("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")),
            ProviderConfig("bytez", "BYTEZ_API_KEY", "https://api.bytez.com/v1"),
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
        if provider == "gemini":
            if model.startswith("google/gemini-"):
                return "gemini/" + model.replace("google/", "", 1)
            elif model.startswith("gemini/"):
                return model
            else:
                return "gemini/gemini-2.5-flash"
        
        elif provider == "openrouter":
            if model.startswith("openrouter/"):
                return model
            else:
                return "openrouter/google/gemma-3-4b-it:free"
        
        elif provider == "bytez":
            # Map to Bytez model format
            if model.startswith("google/gemini-"):
                return "google/gemini-2.5-flash"
            elif model.startswith("openrouter/"):
                return "google/gemini-2.5-flash"
            else:
                return "google/gemini-2.5-flash"
        
        return model
    
    def _call_bytez_api(self, model: str, messages: List[Dict], 
                       json_mode: bool = True, timeout: int = 60) -> str:
        """
        Direct call to Bytez API (not through LiteLLM).
        
        Args:
            model: Bytez model identifier
            messages: Message list for the API
            json_mode: Whether to request JSON response
            timeout: Request timeout in seconds
            
        Returns:
            Response content string
        """
        api_key = self.secrets.get("BYTEZ_API_KEY", "")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        
        response = requests.post(
            "https://api.bytez.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def ai_call(self, system_prompt: str, user_prompt: str, 
                preferred_model: str = None, json_mode: bool = True) -> str:
        """
        Make AI call with automatic fallback between providers.
        
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
