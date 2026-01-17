"""Tests for connection storage module."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from glee.connect import storage
from glee.connect.credential import (
    AIProviderAPICredential,
    AIProviderOAuthCredential,
    ServiceCredential,
)
from glee.utils import generate_id

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def temp_auth_file() -> Generator[Path, None, None]:
    """Create a temporary auth file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        temp_path = Path(f.name)

    # Patch the auth path to use temp file
    with patch.object(storage.ConnectionStorage, "path", temp_path):
        yield temp_path

    # Cleanup
    if temp_path.exists():
        os.unlink(temp_path)


class TestAIProviderAPICredential:
    """Tests for AIProviderAPICredential dataclass."""

    def test_create_api_credential(self) -> None:
        cred = AIProviderAPICredential(
            id="test123",
            label="my-openrouter",
            sdk="openai",
            vendor="openrouter",
            key="sk-or-xxx",
            base_url="https://openrouter.ai/api/v1",
        )
        assert cred.id == "test123"
        assert cred.label == "my-openrouter"
        assert cred.sdk == "openai"
        assert cred.vendor == "openrouter"
        assert cred.key == "sk-or-xxx"
        assert cred.base_url == "https://openrouter.ai/api/v1"
        assert cred.type == "ai_api"
        assert cred.category == "ai_provider"

    def test_to_dict(self) -> None:
        cred = AIProviderAPICredential(
            id="test123",
            label="anthropic",
            sdk="anthropic",
            vendor="anthropic",
            key="sk-ant-xxx",
        )
        d = cred.to_dict()
        assert d["id"] == "test123"
        assert d["label"] == "anthropic"
        assert d["type"] == "ai_api"
        assert d["sdk"] == "anthropic"
        assert d["vendor"] == "anthropic"
        assert d["key"] == "sk-ant-xxx"
        assert "base_url" not in d  # None values not included

    def test_from_dict(self) -> None:
        data = {
            "id": "abc123",
            "label": "groq",
            "type": "ai_api",
            "sdk": "openai",
            "vendor": "groq",
            "key": "gsk-xxx",
            "base_url": "https://api.groq.com/openai/v1",
        }
        cred = AIProviderAPICredential.from_dict(data)
        assert cred.id == "abc123"
        assert cred.label == "groq"
        assert cred.vendor == "groq"
        assert cred.key == "gsk-xxx"
        assert cred.base_url == "https://api.groq.com/openai/v1"


class TestAIProviderOAuthCredential:
    """Tests for AIProviderOAuthCredential dataclass."""

    def test_create_oauth_credential(self) -> None:
        cred = AIProviderOAuthCredential(
            id="oauth123",
            label="codex",
            sdk="openai",
            vendor="openai",
            refresh="refresh-token",
            access="access-token",
            expires=1736956800000,
            account_id="org-abc",
        )
        assert cred.id == "oauth123"
        assert cred.label == "codex"
        assert cred.sdk == "openai"
        assert cred.vendor == "openai"
        assert cred.refresh == "refresh-token"
        assert cred.access == "access-token"
        assert cred.expires == 1736956800000
        assert cred.account_id == "org-abc"
        assert cred.type == "ai_oauth"
        assert cred.category == "ai_provider"

    def test_is_expired_not_expired(self) -> None:
        import time

        future_time = int((time.time() + 3600) * 1000)  # 1 hour from now
        cred = AIProviderOAuthCredential(
            id="test",
            label="codex",
            sdk="openai",
            vendor="openai",
            expires=future_time,
        )
        assert not cred.is_expired()

    def test_is_expired_expired(self) -> None:
        past_time = 1000  # Way in the past
        cred = AIProviderOAuthCredential(
            id="test",
            label="codex",
            sdk="openai",
            vendor="openai",
            expires=past_time,
        )
        assert cred.is_expired()

    def test_is_expired_zero_never_expires(self) -> None:
        cred = AIProviderOAuthCredential(
            id="test",
            label="copilot",
            sdk="openai",
            vendor="github",
            expires=0,
        )
        assert not cred.is_expired()

    def test_to_dict(self) -> None:
        cred = AIProviderOAuthCredential(
            id="oauth123",
            label="codex",
            sdk="openai",
            vendor="openai",
            refresh="refresh-token",
            access="access-token",
            expires=1736956800000,
            account_id="org-abc",
        )
        d = cred.to_dict()
        assert d["id"] == "oauth123"
        assert d["type"] == "ai_oauth"
        assert d["refresh"] == "refresh-token"
        assert d["account_id"] == "org-abc"

    def test_from_dict(self) -> None:
        data = {
            "id": "oauth456",
            "label": "copilot",
            "type": "ai_oauth",
            "sdk": "openai",
            "vendor": "github",
            "refresh": "token",
            "access": "token",
            "expires": 0,
        }
        cred = AIProviderOAuthCredential.from_dict(data)
        assert cred.id == "oauth456"
        assert cred.label == "copilot"
        assert cred.vendor == "github"


class TestServiceCredential:
    """Tests for ServiceCredential dataclass."""

    def test_create_service_credential(self) -> None:
        cred = ServiceCredential(
            id="svc123",
            label="github",
            vendor="github",
            key="ghp_xxx",
            base_url="https://api.github.com",
        )
        assert cred.id == "svc123"
        assert cred.label == "github"
        assert cred.vendor == "github"
        assert cred.key == "ghp_xxx"
        assert cred.base_url == "https://api.github.com"
        assert cred.type == "service"
        assert cred.category == "service"
        assert cred.sdk is None

    def test_to_dict(self) -> None:
        cred = ServiceCredential(
            id="svc123",
            label="github",
            vendor="github",
            key="ghp_xxx",
            base_url="https://api.github.com",
        )
        d = cred.to_dict()
        assert d["id"] == "svc123"
        assert d["type"] == "service"
        assert d["vendor"] == "github"
        assert d["key"] == "ghp_xxx"
        assert d["base_url"] == "https://api.github.com"
        assert "sdk" not in d  # Services don't have SDK

    def test_from_dict(self) -> None:
        data = {
            "id": "svc456",
            "label": "github",
            "type": "service",
            "vendor": "github",
            "key": "ghp_xxx",
            "base_url": "https://api.github.com",
        }
        cred = ServiceCredential.from_dict(data)
        assert cred.id == "svc456"
        assert cred.label == "github"
        assert cred.vendor == "github"
        assert cred.sdk is None


class TestStorageFunctions:
    """Tests for storage CRUD functions."""

    def test_add_and_get(self, temp_auth_file: Path) -> None:
        cred = AIProviderAPICredential(
            id="",
            label="test-api",
            sdk="openai",
            vendor="openrouter",
            key="test-key",
        )
        added = storage.ConnectionStorage.add(cred)
        assert added.id  # ID should be generated

        retrieved = storage.ConnectionStorage.get(added.id)
        assert retrieved is not None
        assert retrieved.label == "test-api"
        assert isinstance(retrieved, AIProviderAPICredential)
        assert retrieved.key == "test-key"

    def test_all_empty(self, temp_auth_file: Path) -> None:
        creds = storage.ConnectionStorage.all()
        assert creds == []

    def test_all_multiple(self, temp_auth_file: Path) -> None:
        storage.ConnectionStorage.add(AIProviderAPICredential(
            id="", label="cred1", sdk="openai", vendor="openrouter", key="key1"
        ))
        storage.ConnectionStorage.add(AIProviderAPICredential(
            id="", label="cred2", sdk="anthropic", vendor="anthropic", key="key2"
        ))
        storage.ConnectionStorage.add(AIProviderOAuthCredential(
            id="", label="cred3", sdk="openai", vendor="openai"
        ))

        creds = storage.ConnectionStorage.all()
        assert len(creds) == 3

    def test_find_by_vendor(self, temp_auth_file: Path) -> None:
        storage.ConnectionStorage.add(AIProviderAPICredential(
            id="", label="or1", sdk="openai", vendor="openrouter", key="key1"
        ))
        storage.ConnectionStorage.add(AIProviderAPICredential(
            id="", label="or2", sdk="openai", vendor="openrouter", key="key2"
        ))
        storage.ConnectionStorage.add(AIProviderAPICredential(
            id="", label="ant", sdk="anthropic", vendor="anthropic", key="key3"
        ))

        openrouter_creds = storage.ConnectionStorage.find(vendor="openrouter")
        assert len(openrouter_creds) == 2

        anthropic_creds = storage.ConnectionStorage.find(vendor="anthropic")
        assert len(anthropic_creds) == 1

    def test_find_by_vendor_and_category(self, temp_auth_file: Path) -> None:
        storage.ConnectionStorage.add(AIProviderAPICredential(
            id="", label="api", sdk="openai", vendor="openai", key="key1"
        ))
        storage.ConnectionStorage.add(ServiceCredential(
            id="", label="github", vendor="github", key="ghp_xxx"
        ))

        ai_creds = storage.ConnectionStorage.find(vendor="openai", category="ai_provider")
        assert len(ai_creds) == 1
        assert ai_creds[0].label == "api"

        service_creds = storage.ConnectionStorage.find(vendor="github", category="service")
        assert len(service_creds) == 1
        assert service_creds[0].label == "github"

    def test_find_one(self, temp_auth_file: Path) -> None:
        storage.ConnectionStorage.add(AIProviderAPICredential(
            id="", label="test", sdk="openai", vendor="groq", key="key1"
        ))

        cred = storage.ConnectionStorage.find_one(vendor="groq")
        assert cred is not None
        assert cred.label == "test"

        no_cred = storage.ConnectionStorage.find_one(vendor="nonexistent")
        assert no_cred is None

    def test_remove(self, temp_auth_file: Path) -> None:
        added = storage.ConnectionStorage.add(AIProviderAPICredential(
            id="", label="to-remove", sdk="openai", vendor="test", key="key"
        ))

        assert storage.ConnectionStorage.get(added.id) is not None
        assert storage.ConnectionStorage.remove(added.id) is True
        assert storage.ConnectionStorage.get(added.id) is None

    def test_remove_nonexistent(self, temp_auth_file: Path) -> None:
        assert storage.ConnectionStorage.remove("nonexistent-id") is False

    def test_update(self, temp_auth_file: Path) -> None:
        added = storage.ConnectionStorage.add(AIProviderAPICredential(
            id="", label="original", sdk="openai", vendor="test", key="old-key"
        ))

        updated_cred = AIProviderAPICredential(
            id=added.id,
            label="updated",
            sdk="openai",
            vendor="test",
            key="new-key",
        )
        assert storage.ConnectionStorage.update(added.id, updated_cred) is True

        retrieved = storage.ConnectionStorage.get(added.id)
        assert retrieved is not None
        assert retrieved.label == "updated"
        assert isinstance(retrieved, AIProviderAPICredential)
        assert retrieved.key == "new-key"

    def test_update_nonexistent(self, temp_auth_file: Path) -> None:
        cred = AIProviderAPICredential(
            id="fake", label="test", sdk="openai", vendor="test", key="key"
        )
        assert storage.ConnectionStorage.update("nonexistent", cred) is False


class TestGenerateId:
    """Tests for ID generation."""

    def test_generate_id_length(self) -> None:
        id1 = generate_id()
        assert len(id1) == 10

    def test_generate_id_alphanumeric(self) -> None:
        id1 = generate_id()
        assert id1.isalnum()
        assert id1.islower() or id1.replace("0123456789", "").islower()

    def test_generate_id_unique(self) -> None:
        ids = [generate_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique


class TestVendorUrls:
    """Tests for vendor URL constants."""

    def test_known_vendors(self) -> None:
        assert "openai" in storage.VENDOR_URLS
        assert "openrouter" in storage.VENDOR_URLS
        assert "groq" in storage.VENDOR_URLS
        assert "anthropic" not in storage.VENDOR_URLS  # Anthropic uses its own SDK

    def test_vendor_urls_format(self) -> None:
        for vendor, url in storage.VENDOR_URLS.items():
            assert url.startswith("http")
            assert "/v1" in url or vendor in ("ollama", "lmstudio")


class TestLegacyParsing:
    """Tests for backwards compatibility with legacy credential formats."""

    def test_parse_legacy_oauth(self) -> None:
        # Legacy oauth format should parse to AIProviderOAuthCredential
        data = {
            "id": "legacy1",
            "label": "codex",
            "type": "oauth",
            "sdk": "openai",
            "vendor": "openai",
            "category": "ai_provider",
        }
        cred = storage.ConnectionStorage.parse(data)
        assert cred is not None
        assert isinstance(cred, AIProviderOAuthCredential)
        assert cred.label == "codex"

    def test_parse_legacy_api_ai_provider(self) -> None:
        # Legacy api format with ai_provider category
        data = {
            "id": "legacy2",
            "label": "anthropic",
            "type": "api",
            "sdk": "anthropic",
            "vendor": "anthropic",
            "category": "ai_provider",
            "key": "sk-ant-xxx",
        }
        cred = storage.ConnectionStorage.parse(data)
        assert cred is not None
        assert isinstance(cred, AIProviderAPICredential)
        assert cred.label == "anthropic"

    def test_parse_legacy_api_service(self) -> None:
        # Legacy api format with service category
        data = {
            "id": "legacy3",
            "label": "github",
            "type": "api",
            "sdk": "github",
            "vendor": "github",
            "category": "service",
            "key": "ghp_xxx",
        }
        cred = storage.ConnectionStorage.parse(data)
        assert cred is not None
        assert isinstance(cred, ServiceCredential)
        assert cred.label == "github"
        assert cred.sdk is None  # Services don't have SDK
