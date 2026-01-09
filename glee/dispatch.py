"""Agent dispatch and selection logic.

Simplified model:
- No "coder" role - main agent handles coding
- Reviewers are configured by CLI preference (codex, claude, gemini)
- Primary reviewer runs first, secondary only on user request
"""

from glee.config import get_reviewers


def get_primary_reviewer(project_path: str | None = None) -> str:
    """Get the primary reviewer CLI.

    Returns:
        CLI command (e.g., "codex", "claude", "gemini")
    """
    reviewers = get_reviewers(project_path)
    return reviewers.get("primary", "codex")


def get_secondary_reviewer(project_path: str | None = None) -> str | None:
    """Get the secondary reviewer CLI (for second opinions).

    Returns:
        CLI command or None if not configured
    """
    reviewers = get_reviewers(project_path)
    return reviewers.get("secondary")


def has_secondary_reviewer(project_path: str | None = None) -> bool:
    """Check if a secondary reviewer is configured."""
    return get_secondary_reviewer(project_path) is not None
