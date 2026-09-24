"""Runtime configuration.

Everything tunable lives here so no module reads os.environ directly.
Python 3.9 compatible: no PEP 604 unions anywhere in this project.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


@dataclass
class Settings:
    # "openai" | "anthropic" | "mock"
    provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "mock").lower())

    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o-mini"))

    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    anthropic_model: str = field(
        default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    )

    github_token: str = field(default_factory=lambda: _env("GITHUB_TOKEN"))

    max_retries: int = 3
    request_timeout: int = 90

    # Scoring weights. Must sum to 100.
    weight_must_have: float = 70.0
    weight_nice_to_have: float = 10.0
    weight_experience: float = 15.0
    weight_external: float = 5.0

    def model_name(self) -> str:
        if self.provider == "openai":
            return self.openai_model
        if self.provider == "anthropic":
            return self.anthropic_model
        return "mock-heuristic"

    def is_configured(self) -> bool:
        if self.provider == "openai":
            return bool(self.openai_api_key)
        if self.provider == "anthropic":
            return bool(self.anthropic_api_key)
        return True  # mock always works

    def describe(self) -> Dict[str, str]:
        return {
            "provider": self.provider,
            "model": self.model_name(),
            "configured": "yes" if self.is_configured() else "no",
        }


_settings: Optional[Settings] = None


def get_settings(refresh: bool = False) -> Settings:
    global _settings
    if _settings is None or refresh:
        _settings = Settings()
    return _settings


def override(provider: Optional[str] = None, model: Optional[str] = None) -> Settings:
    """Used by the Streamlit sidebar to switch provider without a restart."""
    s = get_settings()
    if provider:
        s.provider = provider.lower()
    if model:
        if s.provider == "openai":
            s.openai_model = model
        elif s.provider == "anthropic":
            s.anthropic_model = model
    return s
