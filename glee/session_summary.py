"""Session summary capture helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from glee.helpers import (
    git_diff_since,
    git_head,
    git_status_changes,
    parse_metadata,
)
from glee.memory.capture import capture_memory
from glee.memory.store import Memory
from glee.session import get_latest_session


def summarize_session(
    project_path: str | Path,
    summary: str | None = None,
    claude_session_id: str | None = None,
) -> dict[str, dict[str, int]]:
    """Capture a lightweight session summary into memory.

    Args:
        project_path: Path to the project root
        summary: Optional summary text
        claude_session_id: Optional Claude Code session ID for linking to conversation
    """
    project_path = Path(project_path)
    if not (project_path / ".glee").exists():
        return {"added": {}, "cleared": {}}

    session, session_id = get_latest_session(project_path)

    auto_summary = ""
    if session:
        desc = (session.get("description") or "").strip()
        status = session.get("status", "unknown")
        if desc:
            auto_summary = f"{desc} ({status})"

    # Use provided summary, or auto-generated from session
    # If neither exists, skip creating a useless entry
    summary_text = (summary.strip() if summary else auto_summary) or ""
    if not summary_text:
        return {"added": {}, "cleared": {}}

    # Use Claude session ID if provided, otherwise use Glee session ID
    effective_session_id = claude_session_id or session_id

    memory = Memory(str(project_path))
    session_summaries = memory.get_by_category("session_summary")
    memory.close()

    git_base: str | None = None
    if session_summaries:
        # Use [-1] to get the latest session summary (appended, not cleared)
        meta = parse_metadata(session_summaries[-1].get("metadata"))
        git_base = meta.get("git_base")

    changes: list[str] = []
    changes_available = False
    if git_base:
        changes, changes_available = git_diff_since(project_path, git_base)
    if not changes_available:
        changes, changes_available = git_status_changes(project_path)

    payload: dict[str, Any] = {"summary": summary_text}

    head = git_head(project_path)
    if head:
        payload["git_base"] = head

    if changes_available:
        payload["recent_changes"] = changes

    return capture_memory(
        str(project_path),
        payload,
        source="summarize_session",
        session_id=effective_session_id,
    )
