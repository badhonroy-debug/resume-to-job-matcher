"""Configuration loading from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

DUMMY_KEY_VALUES = {"your-api-key-here", "sk-ant-xxx", ""}


class ConfigError(Exception):
    """Raised when configuration is invalid."""


def get_api_key() -> str:
    """Return the Anthropic API key, raising a friendly error if missing or dummy."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key in DUMMY_KEY_VALUES:
        raise ConfigError(
            "ANTHROPIC_API_KEY is not set or is still the placeholder value.\n"
            "Please set a valid API key in your .env file:\n"
            "  ANTHROPIC_API_KEY=sk-ant-..."
        )
    return key


def get_model() -> str:
    """Return the Claude model to use."""
    return os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")
