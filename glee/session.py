"""Session management for glee_task.

Sessions enable resumable conversations with CLI agents.
Since CLI agents are stateless, Glee stores conversation history
and injects it on resume.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import NotRequired, TypedDict


class Message(TypedDict):
    """A message in a session."""

    role: str  # "user" or "assistant"
    content: str


class Session(TypedDict):
    """A session with an agent."""

    session_id: str
    agent_name: NotRequired[str | None]  # Subagent name from .glee/agents/ (None if using CLI directly)
    agent_cli: str  # CLI used: codex, claude, gemini
    description: str
    created_at: str
    updated_at: str
    status: str  # "active", "completed", "error"
    messages: list[Message]


def get_sessions_dir(project_path: str | Path) -> Path:
    """Get the sessions directory for a project."""
    sessions_dir = Path(project_path) / ".glee" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def generate_session_id() -> str:
    """Generate a new session ID."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"task-{short_uuid}"


def create_session(
    project_path: str | Path,
    description: str,
    agent_cli: str,
    initial_prompt: str,
    agent_name: str | None = None,
) -> Session:
    """Create a new session.

    Args:
        project_path: Path to the project root
        description: Short task description
        agent_cli: CLI to use (codex, claude, gemini)
        initial_prompt: The initial user prompt
        agent_name: Optional subagent name from .glee/agents/
    """
    session_id = generate_session_id()
    now = datetime.now().isoformat()

    session: Session = {
        "session_id": session_id,
        "agent_name": agent_name,
        "agent_cli": agent_cli,
        "description": description,
        "created_at": now,
        "updated_at": now,
        "status": "active",
        "messages": [{"role": "user", "content": initial_prompt}],
    }

    save_session(project_path, session)
    return session


def load_session(project_path: str | Path, session_id: str) -> Session | None:
    """Load an existing session."""
    sessions_dir = get_sessions_dir(project_path)
    session_file = sessions_dir / f"{session_id}.json"

    if not session_file.exists():
        return None

    try:
        with open(session_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_session(project_path: str | Path, session: Session) -> None:
    """Save a session to disk."""
    sessions_dir = get_sessions_dir(project_path)
    session_file = sessions_dir / f"{session['session_id']}.json"

    session["updated_at"] = datetime.now().isoformat()

    with open(session_file, "w") as f:
        json.dump(session, f, indent=2)


def add_message(
    project_path: str | Path,
    session_id: str,
    role: str,
    content: str,
) -> Session | None:
    """Add a message to a session."""
    session = load_session(project_path, session_id)
    if not session:
        return None

    session["messages"].append({"role": role, "content": content})
    save_session(project_path, session)
    return session


def build_context_prompt(session: Session, new_prompt: str) -> str:
    """Build a prompt with previous conversation context."""
    if len(session["messages"]) <= 1:
        # No previous context, just return the new prompt
        return new_prompt

    lines = ["<previous_conversation>"]
    for msg in session["messages"]:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    lines.append("</previous_conversation>")
    lines.append("")
    lines.append(f"User: {new_prompt}")

    return "\n".join(lines)


def complete_session(
    project_path: str | Path,
    session_id: str,
    output: str,
    status: str = "completed",
) -> Session | None:
    """Mark a session as completed and add the assistant response."""
    session = load_session(project_path, session_id)
    if not session:
        return None

    session["messages"].append({"role": "assistant", "content": output})
    session["status"] = status
    save_session(project_path, session)
    return session
