"""
AI provider abstraction — provider-agnostic LLM interface.

Supports:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Nvidia NIMs (OpenAI-compatible endpoint)
    - Ollama (local, OpenAI-compatible endpoint)
    - Any OpenAI-compatible API

API keys are read at RUNTIME ONLY from environment variables (Rule #21).
Provider endpoint URLs are hardcoded, NOT sourced from config files (Rule #28).

This module is OPTIONAL — CRAPQuants works fully without it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NVIDIA_NIMS = "nvidia_nims"
    OLLAMA = "ollama"
    CUSTOM = "custom"


# Hardcoded provider endpoints (Rule #28: never from project config)
_PROVIDER_ENDPOINTS = {
    ProviderType.OPENAI: "https://api.openai.com/v1/chat/completions",
    ProviderType.ANTHROPIC: "https://api.anthropic.com/v1/messages",
    ProviderType.NVIDIA_NIMS: "https://integrate.api.nvidia.com/v1/chat/completions",
    ProviderType.OLLAMA: "http://localhost:11434/v1/chat/completions",
}

_DEFAULT_MODELS = {
    ProviderType.OPENAI: "gpt-4o-mini",
    ProviderType.ANTHROPIC: "claude-sonnet-4-20250514",
    ProviderType.NVIDIA_NIMS: "meta/llama-3.1-8b-instruct",
    ProviderType.OLLAMA: "qwen3.5:latest",
}

_API_KEY_ENV_VARS = {
    ProviderType.OPENAI: "CRAPQUANTS_OPENAI_API_KEY",
    ProviderType.ANTHROPIC: "CRAPQUANTS_ANTHROPIC_API_KEY",
    ProviderType.NVIDIA_NIMS: "CRAPQUANTS_NVIDIA_API_KEY",
    ProviderType.OLLAMA: None,  # No key needed for local Ollama
    ProviderType.CUSTOM: "CRAPQUANTS_AI_API_KEY",
}


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""

    provider: ProviderType
    model: str | None = None
    endpoint: str | None = None  # Only for CUSTOM provider
    max_tokens: int = 1024
    temperature: float = 0.3

    @property
    def resolved_model(self) -> str:
        return self.model or _DEFAULT_MODELS.get(self.provider, "gpt-4o-mini")

    @property
    def resolved_endpoint(self) -> str:
        if self.endpoint:
            return self.endpoint
        return _PROVIDER_ENDPOINTS.get(self.provider, _PROVIDER_ENDPOINTS[ProviderType.OPENAI])

    @property
    def api_key(self) -> str | None:
        """Read API key from environment at runtime (Rule #21)."""
        env_var = _API_KEY_ENV_VARS.get(self.provider)
        if env_var is None:
            return None  # Ollama doesn't need a key
        key = os.environ.get(env_var)
        if not key:
            # Fallback to generic env var
            key = os.environ.get("CRAPQUANTS_AI_API_KEY")
        return key


def validate_provider(config: ProviderConfig) -> tuple[bool, str]:
    """
    Validate that a provider is configured and accessible.

    Returns:
        (is_valid, message) tuple.
    """
    if config.provider != ProviderType.OLLAMA:
        if not config.api_key:
            env_var = _API_KEY_ENV_VARS.get(config.provider, "CRAPQUANTS_AI_API_KEY")
            return False, (
                f"API key not found. Set environment variable: {env_var}\n"
                f"Keys are read at runtime only — never store in config files (Rule #21)."
            )

    return True, "Provider configured."


def call_llm(
    config: ProviderConfig,
    system_prompt: str,
    user_prompt: str,
) -> str | None:
    """
    Call the configured LLM provider.

    Uses httpx for HTTP calls to avoid heavy SDK dependencies.
    Falls back gracefully on any error.

    Args:
        config: Provider configuration.
        system_prompt: System message.
        user_prompt: User message.

    Returns:
        LLM response text, or None on failure.
    """
    try:
        import httpx
    except ImportError:
        logger.warning("httpx_not_installed",
                       message="Install httpx for AI explain: pip install httpx")
        return None

    is_valid, msg = validate_provider(config)
    if not is_valid:
        logger.warning("provider_invalid", message=msg)
        return None

    if config.provider == ProviderType.ANTHROPIC:
        return _call_anthropic(config, system_prompt, user_prompt)
    else:
        return _call_openai_compatible(config, system_prompt, user_prompt)


def _call_openai_compatible(
    config: ProviderConfig,
    system_prompt: str,
    user_prompt: str,
) -> str | None:
    """Call OpenAI-compatible API (OpenAI, NIMs, Ollama, Custom)."""
    import httpx

    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    payload = {
        "model": config.resolved_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(config.resolved_endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        logger.error("llm_timeout", provider=config.provider.value)
    except httpx.HTTPStatusError as e:
        logger.error("llm_http_error", status=e.response.status_code, provider=config.provider.value)
    except (KeyError, IndexError):
        logger.error("llm_response_parse_error", provider=config.provider.value)
    except Exception as e:
        logger.error("llm_error", error=str(e)[:200], provider=config.provider.value)

    return None


def _call_anthropic(
    config: ProviderConfig,
    system_prompt: str,
    user_prompt: str,
) -> str | None:
    """Call Anthropic API (different format from OpenAI)."""
    import httpx

    headers = {
        "Content-Type": "application/json",
        "x-api-key": config.api_key or "",
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": config.resolved_model,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(config.resolved_endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]
    except httpx.TimeoutException:
        logger.error("llm_timeout", provider="anthropic")
    except httpx.HTTPStatusError as e:
        logger.error("llm_http_error", status=e.response.status_code, provider="anthropic")
    except (KeyError, IndexError):
        logger.error("llm_response_parse_error", provider="anthropic")
    except Exception as e:
        logger.error("llm_error", error=str(e)[:200], provider="anthropic")

    return None
