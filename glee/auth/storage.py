"""Auth storage for Glee credentials.

Single file storage: ~/.glee/auth.yml

```yaml
- id: a1b2c3d4e5
  label: my-codex
  type: oauth
  sdk: openai
  vendor: openai
  refresh: "..."
  access: "..."
  expires: 1736956800000
  account_id: "org-abc123"

- id: f6g7h8i9j0
  label: work-claude
  type: api
  sdk: anthropic
  vendor: anthropic
  key: "sk-ant-..."

- id: k1l2m3n4o5
  label: openrouter
  type: api
  sdk: openai
  vendor: openrouter
  base_url: "https://openrouter.ai/api/v1"
  key: "sk-or-..."
```
"""

from __future__ import annotations

import os
import secrets
import string
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

# SDK types
SDK = Literal["openai", "anthropic", "google"]

# Common vendors with known base URLs (for OpenAI SDK)
VENDOR_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}


def _generate_id() -> str:
    """Generate a random alphanumeric ID."""
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(10))


@dataclass
class OAuthCredential:
    """OAuth credential (e.g., Codex, Gemini)."""

    id: str
    label: str
    sdk: SDK
    vendor: str
    refresh: str = ""
    access: str = ""
    expires: int = 0  # Unix timestamp (milliseconds)
    account_id: str | None = None
    type: Literal["oauth"] = field(default="oauth", repr=False)

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires == 0:
            return False
        return time.time() * 1000 > self.expires

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "type": "oauth",
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
    def from_dict(cls, data: dict[str, Any]) -> OAuthCredential:
        return cls(
            id=data.get("id", _generate_id()),
            label=data.get("label", ""),
            sdk=data.get("sdk", "openai"),
            vendor=data.get("vendor", ""),
            refresh=data.get("refresh", ""),
            access=data.get("access", ""),
            expires=data.get("expires", 0),
            account_id=data.get("account_id"),
        )


@dataclass
class APICredential:
    """API key credential (e.g., Claude, OpenRouter)."""

    id: str
    label: str
    sdk: SDK
    vendor: str
    key: str = ""
    base_url: str | None = None
    type: Literal["api"] = field(default="api", repr=False)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "type": "api",
            "sdk": self.sdk,
            "vendor": self.vendor,
            "key": self.key,
        }
        if self.base_url:
            d["base_url"] = self.base_url
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> APICredential:
        return cls(
            id=data.get("id", _generate_id()),
            label=data.get("label", ""),
            sdk=data.get("sdk", "openai"),
            vendor=data.get("vendor", ""),
            key=data.get("key", ""),
            base_url=data.get("base_url"),
        )


# Union type
Credential = OAuthCredential | APICredential


def _get_auth_path() -> Path:
    """Get path to auth.yml."""
    return Path.home() / ".glee" / "auth.yml"


def _read_auth() -> list[dict[str, Any]]:
    """Read all credentials from auth.yml."""
    path = _get_auth_path()
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, list) else []  # type: ignore[return-value]
    except Exception:
        return []


def _write_auth(data: list[dict[str, Any]]) -> None:
    """Write credentials to auth.yml."""
    path = _get_auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    os.chmod(path, 0o600)


def _parse_credential(data: dict[str, Any]) -> Credential | None:
    """Parse a credential dict into the appropriate type."""
    cred_type = data.get("type")
    if cred_type == "oauth":
        return OAuthCredential.from_dict(data)
    elif cred_type == "api":
        return APICredential.from_dict(data)
    return None


def all() -> list[Credential]:
    """Get all credentials."""
    data = _read_auth()
    result: list[Credential] = []
    for entry in data:
        cred = _parse_credential(entry)
        if cred:
            result.append(cred)
    return result


def get(id: str) -> Credential | None:
    """Get credential by ID."""
    for cred in all():
        if cred.id == id:
            return cred
    return None


def find(vendor: str, type: Literal["oauth", "api"] | None = None) -> list[Credential]:
    """Find credentials by vendor and optionally type."""
    result: list[Credential] = []
    for cred in all():
        if cred.vendor == vendor:
            if type is None or cred.type == type:
                result.append(cred)
    return result


def find_one(vendor: str, type: Literal["oauth", "api"] | None = None) -> Credential | None:
    """Find first credential matching vendor and optionally type."""
    matches = find(vendor, type)
    return matches[0] if matches else None


def add(credential: Credential) -> Credential:
    """Add a new credential. Generates ID if not set."""
    if not credential.id:
        credential.id = _generate_id()

    data = _read_auth()
    data.append(credential.to_dict())
    _write_auth(data)
    return credential


def remove(id: str) -> bool:
    """Remove credential by ID."""
    data = _read_auth()
    original_len = len(data)
    data = [d for d in data if d.get("id") != id]
    if len(data) < original_len:
        _write_auth(data)
        return True
    return False


def update(id: str, credential: Credential) -> bool:
    """Update credential by ID."""
    data = _read_auth()
    for i, entry in enumerate(data):
        if entry.get("id") == id:
            credential.id = id  # Preserve ID
            data[i] = credential.to_dict()
            _write_auth(data)
            return True
    return False
