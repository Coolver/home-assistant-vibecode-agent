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