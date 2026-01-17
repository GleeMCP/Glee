"""GitHub integration for Glee.

Provides:
- Authentication via glee connect
- PR fetching and review posting
- Branch comparison
- Diff parsing utilities
"""

from glee.github.auth import get_token, require_token
from glee.github.client import GitHubClient, PR, PRFile, Review, ReviewComment
from glee.github.diff import parse_patch, get_added_lines, format_diff_for_review

__all__ = [
    "get_token",
    "require_token",
    "GitHubClient",
    "PR",
    "PRFile",
    "Review",
    "ReviewComment",
    "parse_patch",
    "get_added_lines",
    "format_diff_for_review",
]
