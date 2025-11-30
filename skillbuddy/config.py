"""Configuration helpers for SkillBuddy."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Ensure environment variables load once.
load_dotenv(ENV_PATH)

SERPAPI_MONTHLY_QUOTA = 250

_google_key_override: Optional[str] = None
_serpapi_key_override: Optional[str] = None


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


def set_google_api_key(value: Optional[str]) -> None:
    """Override the Google API key for the current process."""
    global _google_key_override
    normalized = value.strip() if value else None
    _google_key_override = normalized
    if normalized:
        os.environ["GOOGLE_API_KEY"] = normalized
    else:
        os.environ.pop("GOOGLE_API_KEY", None)
    google_api_key.cache_clear()


def set_serpapi_key(value: Optional[str]) -> None:
    """Override the SerpAPI key for the current process."""
    global _serpapi_key_override
    normalized = value.strip() if value else None
    _serpapi_key_override = normalized
    if normalized:
        os.environ["SERPAPI_KEY"] = normalized
    else:
        os.environ.pop("SERPAPI_KEY", None)
    serpapi_key.cache_clear()


@lru_cache(maxsize=1)
def google_api_key() -> str:
    if _google_key_override:
        return _google_key_override

    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ConfigError("GOOGLE_API_KEY missing. Define it in .env or set it in the UI")
    return key


@lru_cache(maxsize=1)
def serpapi_key() -> str:
    if _serpapi_key_override:
        return _serpapi_key_override

    key = os.getenv("SERPAPI_KEY")
    if not key:
        raise ConfigError("SERPAPI_KEY missing. Define it in .env or set it in the UI")
    return key
