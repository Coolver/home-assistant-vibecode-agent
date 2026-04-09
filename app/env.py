"""
Environment loading helpers.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv

_LOADED = False


def load_env() -> None:
    """Load .env once, supporting optional ENV_FILE override."""
    global _LOADED
    if _LOADED:
        return

    env_file = os.getenv("ENV_FILE")
    if env_file:
        load_dotenv(dotenv_path=env_file, override=False, interpolate=True)
    else:
        load_dotenv(override=False, interpolate=True)

    _LOADED = True


def get_mistral_config():
    """Get Mistral Vibe configuration from environment variables or add-on options."""
    # Check environment variables first
    api_url = os.getenv("MISTRAL_VIBE_API_URL", "").strip()
    api_key = os.getenv("MISTRAL_VIBE_API_KEY", "").strip()
    
    # Fall back to add-on configuration options
    if not api_url:
        api_url = os.getenv("mistral_vibe_api_url", "").strip()
    if not api_key:
        api_key = os.getenv("mistral_vibe_api_key", "").strip()
    
    default_model = os.getenv("MISTRAL_VIBE_DEFAULT_MODEL", "mistral-tiny").strip()
    if not default_model or default_model == "mistral-tiny":  # Fallback to add-on config
        default_model = os.getenv("mistral_vibe_default_model", "mistral-tiny").strip()
    
    # Get timeout - env var takes precedence
    timeout_env = os.getenv("MISTRAL_VIBE_TIMEOUT")
    if timeout_env:
        timeout = int(timeout_env)
    else:
        timeout = int(os.getenv("mistral_vibe_timeout", "30"))
    
    # Get max retries - env var takes precedence
    retries_env = os.getenv("MISTRAL_VIBE_MAX_RETRIES")
    if retries_env:
        max_retries = int(retries_env)
    else:
        max_retries = int(os.getenv("mistral_vibe_max_retries", "3"))
    
    return {
        "api_url": api_url,
        "api_key": api_key,
        "default_model": default_model,
        "timeout": timeout,
        "max_retries": max_retries,
        "enabled": bool(api_url and api_key)
    }


def validate_mistral_config(config: dict) -> bool:
    """Validate Mistral Vibe configuration."""
    if not config["enabled"]:
        return True  # Mistral Vibe is disabled, no validation needed
    
    if not config["api_url"]:
        raise ValueError("MISTRAL_VIBE_API_URL is required when Mistral Vibe is enabled")
    
    if not config["api_key"]:
        raise ValueError("MISTRAL_VIBE_API_KEY is required when Mistral Vibe is enabled")
    
    if config["timeout"] <= 0:
        raise ValueError("MISTRAL_VIBE_TIMEOUT must be positive")
    
    if config["max_retries"] < 0:
        raise ValueError("MISTRAL_VIBE_MAX_RETRIES must be non-negative")
    
    return True