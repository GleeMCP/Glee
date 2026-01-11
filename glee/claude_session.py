"""Read Claude Code session files for conversation history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict


class ConversationMessage(TypedDict):
    """A message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str


class ConversationSummary(TypedDict):
    """Summary of a Claude Code conversation."""

    session_id: str
    project_path: str
    messages: list[ConversationMessage]
    started_at: str | None
    ended_at: str | None


def get_claude_projects_dir() -> Path:
    """Get the Claude Code projects directory."""
    return Path.home() / ".claude" / "projects"


def project_path_to_claude_folder(project_path: str | Path) -> str:
    """Convert a project path to Claude's folder naming convention.

    Claude Code stores projects in folders like:
    -Users-yumin-ventures-grow-stack-maily
    """
    project_path = str(Path(project_path).resolve())
    # Replace path separators with dashes
    return project_path.replace("/", "-").replace("\\", "-")


def get_claude_session_file(
    project_path: str | Path,
    session_id: str,
) -> Path | None:
    """Get a Claude Code session file by ID.

    Args:
        project_path: Path to the project root
        session_id: Session ID from Claude Code hook stdin

    Returns:
        Path to the session .jsonl file, or None if not found
    """
    claude_projects = get_claude_projects_dir()
    project_folder = project_path_to_claude_folder(project_path)
    session_dir = claude_projects / project_folder

    if not session_dir.exists():
        return None

    session_file = session_dir / f"{session_id}.jsonl"
    if session_file.exists():
        return session_file

    return None


def parse_claude_session(session_file: Path) -> ConversationSummary | None:
    """Parse a Claude Code session file and extract the conversation."""
    if not session_file.exists():
        return None

    messages: list[ConversationMessage] = []
    session_id = session_file.stem
    project_path = ""
    started_at: str | None = None
    ended_at: str | None = None

    try:
        with open(session_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type")
                timestamp = obj.get("timestamp", "")

                # Track project path from first message
                if not project_path and obj.get("cwd"):
                    project_path = obj["cwd"]

                # Track timestamps
                if timestamp:
                    if started_at is None:
                        started_at = timestamp
                    ended_at = timestamp

                if msg_type not in ("user", "assistant"):
                    continue

                msg = obj.get("message", {})
                content = msg.get("content", [])

                # Extract text content
                text_parts: list[str] = []
                if isinstance(content, list):
                    content_list: list[Any] = content
                    for c in content_list:
                        if isinstance(c, dict) and c.get("type") == "text":
                            text_parts.append(str(c.get("text", "")))
                elif isinstance(content, str):
                    text_parts.append(content)

                if text_parts:
                    messages.append({
                        "role": msg_type,
                        "content": "\n".join(text_parts),
                        "timestamp": timestamp,
                    })
    except (OSError, IOError):
        return None

    if not messages:
        return None

    return {
        "session_id": session_id,
        "project_path": project_path,
        "messages": messages,
        "started_at": started_at,
        "ended_at": ended_at,
    }


def format_conversation_for_summary(conversation: ConversationSummary, max_chars: int = 4000) -> str:
    """Format a conversation into a string suitable for summarization.

    Truncates if too long, keeping the beginning and end.
    """
    lines: list[str] = []

    for msg in conversation["messages"]:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"].strip()

        # Skip command outputs and system messages
        if content.startswith("<local-command"):
            continue
        if content.startswith("<command-name>"):
            continue

        lines.append(f"{role}: {content}")
        lines.append("")

    full_text = "\n".join(lines)

    if len(full_text) <= max_chars:
        return full_text

    # Keep first half and last quarter
    first_part = max_chars * 2 // 3
    last_part = max_chars // 3
    return full_text[:first_part] + "\n\n... (truncated) ...\n\n" + full_text[-last_part:]


def generate_summary_from_conversation(conversation: ConversationSummary) -> str:
    """Generate a simple summary from a conversation.

    Extracts the first user message as the task and notes key outcomes.
    """
    if not conversation["messages"]:
        return ""

    # Get first user message as the task
    first_user_msg = ""
    for msg in conversation["messages"]:
        if msg["role"] == "user":
            content = msg["content"].strip()
            # Skip command messages
            if not content.startswith("<"):
                first_user_msg = content
                break

    if not first_user_msg:
        return ""

    # Truncate if too long
    if len(first_user_msg) > 200:
        first_user_msg = first_user_msg[:200] + "..."

    # Count exchanges
    user_count = sum(1 for m in conversation["messages"] if m["role"] == "user")
    assistant_count = sum(1 for m in conversation["messages"] if m["role"] == "assistant")

    summary = f"Task: {first_user_msg}"
    if user_count > 1 or assistant_count > 1:
        summary += f" ({user_count} user messages, {assistant_count} assistant responses)"

    return summary
