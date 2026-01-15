"""Shared helper functions for Glee."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_time(value: str | datetime | None) -> datetime | None:
    """Parse a timestamp value (string or datetime)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_metadata(value: Any) -> dict[str, Any]:
    """Parse metadata from dict or JSON string."""
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


def git_head(path: Path) -> str | None:
    """Get the current HEAD commit SHA."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def git_diff_since(path: Path, base: str, limit: int = 20) -> tuple[list[str], bool]:
    """Get file changes since a base commit."""
    result = subprocess.run(
        ["git", "diff", "--name-status", f"{base}..HEAD"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [], False
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return lines[:limit], True


def git_status_changes(path: Path, limit: int = 20) -> tuple[list[str], bool]:
    """Get uncommitted file changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [], False
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return lines[:limit], True


def strip_code_fence(text: str) -> str:
    """Strip markdown code fences from text."""
    if not text:
        return ""
    lines = text.strip().splitlines()
    if not lines:
        return ""
    if lines[0].strip().startswith("```"):
        lines = lines[1:]
        if lines and lines[0].strip().lower() == "json":
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
    return "\n".join(lines).strip()


def extract_capture_block(text: str | None) -> tuple[dict[str, Any] | None, str | None]:
    """Extract glee_memory_capture block from text.

    Returns (payload_dict, cleaned_text) where payload_dict is None if not found.
    """
    if not text:
        return None, text
    match = re.search(
        r"<glee_memory_capture>(.*?)</glee_memory_capture>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None, text
    raw = strip_code_fence(match.group(1))
    payload: dict[str, Any] | None = None
    if raw:
        try:
            parsed: Any = json.loads(raw)
            if isinstance(parsed, dict):
                payload = {str(k): v for k, v in parsed.items()}
        except json.JSONDecodeError:
            payload = None
    cleaned = (text[: match.start()] + text[match.end() :]).strip()
    return payload, cleaned
