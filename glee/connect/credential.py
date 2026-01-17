"""Credential types for Glee connections.

Three credential types:
- AIProviderOAuthCredential: OAuth-based AI providers (Codex, Copilot)
- AIProviderAPICredential: API key-based AI providers (Anthropic, OpenRouter, etc.)
- ServiceCredential: Services like GitHub
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from glee.utils import generate_id

# SDK types (for AI providers only)
SDK = Literal["openai", "openrouter", "anthropic", "vertex", "bedrock"]

# Category types
Category = Literal["ai_provider", "service"]


@dataclass
class AIProviderOAuthCredential:
    """OAuth credential for AI providers (e.g., Codex, Copilot)."""

    id: str
    label: str
    sdk: SDK
    vendor: str
    refresh: str = ""
    access: str = ""
    expires: int = 0  # Unix timestamp (milliseconds)
    account_id: str | None = None
    type: Literal["ai_oauth"] = field(default="ai_oauth", repr=False)

    @property
    def category(self) -> Category:
        return "ai_provider"

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires == 0:
            return False
        return time.time() * 1000 > self.expires

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "type": "ai_oauth",
            "sdk": self.sdk,
            "vendor": self.vendor,
            "refresh": self.refresh,
            "access": self.access,
            "expires": self.expires,
        }
        if self.account_id:
            d["account_id"] = self.account_id
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AIProviderOAuthCredential:
        return cls(
            id=data.get("id", generate_id()),
            label=data.get("label", ""),
            sdk=data.get("sdk", "openai"),
            vendor=data.get("vendor", ""),
            refresh=data.get("refresh", ""),
            access=data.get("access", ""),
            expires=data.get("expires", 0),
            account_id=data.get("account_id"),
        )


@dataclass
class AIProviderAPICredential:
    """API key credential for AI providers (e.g., Anthropic, OpenRouter)."""

    id: str
    label: str
    sdk: SDK
    vendor: str
    key: str = ""
    base_url: str | None = None
    type: Literal["ai_api"] = field(default="ai_api", repr=False)

    @property
    def category(self) -> Category:
        return "ai_provider"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "type": "ai_api",
            "sdk": self.sdk,
            "vendor": self.vendor,
            "key": self.key,
        }
        if self.base_url:
            d["base_url"] = self.base_url
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AIProviderAPICredential:
        return cls(
            id=data.get("id", generate_id()),
            label=data.get("label", ""),
            sdk=data.get("sdk", "openai"),
            vendor=data.get("vendor", ""),
            key=data.get("key", ""),
            base_url=data.get("base_url"),
        )


@dataclass
class ServiceCredential:
    """Credential for services (e.g., GitHub)."""

    id: str
    label: str
    vendor: str
    key: str = ""
    base_url: str | None = None
    type: Literal["service"] = field(default="service", repr=False)

    @property
    def category(self) -> Category:
        return "service"

    @property
    def sdk(self) -> None:
        """Services don't have SDK."""
        return None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "type": "service",
            "vendor": self.vendor,
            "key": self.key,
        }
        if self.base_url:
            d["base_url"] = self.base_url
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServiceCredential:
        return cls(
            id=data.get("id", generate_id()),
            label=data.get("label", ""),
            vendor=data.get("vendor", ""),
            key=data.get("key", ""),
            base_url=data.get("base_url"),
        )


# Union types
AIProviderCredential = AIProviderOAuthCredential | AIProviderAPICredential
Credential = AIProviderOAuthCredential | AIProviderAPICredential | ServiceCredential

# Backwards compatibility aliases
OAuthCredential = AIProviderOAuthCredential
APICredential = AIProviderAPICredential
