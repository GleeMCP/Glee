"""Connection storage for Glee.

Single file storage: ~/.config/glee/connections.yml

```yaml
- id: a1b2c3d4e5
  label: codex
  type: ai_oauth
  sdk: openai
  vendor: openai
  refresh: "..."
  access: "..."
  expires: 1736956800000
  account_id: "org-abc123"

- id: f6g7h8i9j0
  label: anthropic
  type: ai_api
  sdk: anthropic
  vendor: anthropic
  key: "sk-ant-..."

- id: k1l2m3n4o5
  label: github
  type: service
  vendor: github
  base_url: "https://api.github.com"
  key: "ghp_..."
```
"""

from __future__ import annotations

import os
import secrets
import string
from pathlib import Path
from typing import Any

import yaml

from glee.connect.credential import (
    SDK,
    AIProviderAPICredential,
    AIProviderCredential,
    AIProviderOAuthCredential,
    APICredential,
    Category,
    Credential,
    OAuthCredential,
    ServiceCredential,
)

# Re-export for backwards compatibility
__all__ = [
    "SDK",
    "Category",
    "AIProviderOAuthCredential",
    "AIProviderAPICredential",
    "ServiceCredential",
    "AIProviderCredential",
    "Credential",
    "OAuthCredential",
    "APICredential",
    "ConnectionStorage",
    "VENDOR_URLS",
    "generate_id",
]

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


def generate_id() -> str:
    """Generate a random alphanumeric ID."""
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(10))


# Storage path
CONNECTIONS_PATH = Path.home() / ".config" / "glee" / "connections.yml"


class ConnectionStorage:
    """Storage for Glee connections (~/.config/glee/connections.yml)."""

    path: Path = CONNECTIONS_PATH

    @classmethod
    def all(cls) -> list[Credential]:
        """Get all connections."""
        result: list[Credential] = []
        for entry in cls.read():
            cred = cls.parse(entry)
            if cred:
                result.append(cred)
        return result

    @classmethod
    def get(cls, id_or_label: str) -> Credential | None:
        """Get connection by ID or label (both are unique)."""
        for cred in cls.all():
            if cred.id == id_or_label or cred.label == id_or_label:
                return cred
        return None

    @classmethod
    def add(cls, credential: Credential) -> Credential:
        """Add a new connection. Generates ID if not set."""
        if not credential.id:
            credential.id = generate_id()

        data = cls.read()
        data.append(credential.to_dict())
        cls.write(data)
        return credential

    @classmethod
    def remove(cls, id_or_label: str) -> bool:
        """Remove connection by ID or label."""
        data = cls.read()
        original_len = len(data)
        data = [d for d in data if d.get("id") != id_or_label and d.get("label") != id_or_label]
        if len(data) < original_len:
            cls.write(data)
            return True
        return False

    @classmethod
    def update(cls, id: str, credential: Credential) -> bool:
        """Update connection by ID."""
        data = cls.read()
        for i, entry in enumerate(data):
            if entry.get("id") == id:
                credential.id = id  # Preserve ID
                data[i] = credential.to_dict()
                cls.write(data)
                return True
        return False

    @classmethod
    def read(cls) -> list[dict[str, Any]]:
        """Read all connections from file."""
        if not cls.path.exists():
            return []
        try:
            with open(cls.path) as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, list) else []  # type: ignore[return-value]
        except Exception:
            return []

    @classmethod
    def write(cls, data: list[dict[str, Any]]) -> None:
        """Write connections to file."""
        cls.path.parent.mkdir(parents=True, exist_ok=True)
        with open(cls.path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        os.chmod(cls.path, 0o600)

    @staticmethod
    def parse(data: dict[str, Any]) -> Credential | None:
        """Parse a dict into the appropriate credential type."""
        cred_type = data.get("type")
        # New types
        if cred_type == "ai_oauth":
            return AIProviderOAuthCredential.from_dict(data)
        elif cred_type == "ai_api":
            return AIProviderAPICredential.from_dict(data)
        elif cred_type == "service":
            return ServiceCredential.from_dict(data)
        # Legacy types (backwards compatibility)
        elif cred_type == "oauth":
            return AIProviderOAuthCredential.from_dict(data)
        elif cred_type == "api":
            # Check category to determine if it's AI provider or service
            if data.get("category") == "service":
                return ServiceCredential.from_dict(data)
            return AIProviderAPICredential.from_dict(data)
        return None
