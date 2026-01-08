"""Agent dispatch and selection logic.

Design Rules (from docs/arbitration.md):
1. No fallback agent - Each agent should have clear specialization
2. No additional reviewers during dispute - Resolve with judge/human/discard
3. Domain mismatch uses first coder - If no domain matches, use first available
"""

import random
from typing import Any

from glee.config import get_connected_agents, get_dispatch_config


def select_coder(
    domain: str | None = None,
    project_path: str | None = None,
) -> dict[str, Any] | None:
    """Select a coder agent based on domain.

    Design Rule #3: If no coder has matching domain, use first available coder.

    Args:
        domain: Optional domain to match (e.g., "backend", "frontend", "shell")
        project_path: Optional project path

    Returns:
        Selected coder config dict, or None if no coders connected
    """
    coders = get_connected_agents(role="coder", project_path=project_path)
    if not coders:
        return None

    # If domain specified, try to find a matching coder
    if domain:
        for coder in coders:
            coder_domains = coder.get("domain", [])
            if domain in coder_domains:
                return coder

    # Design Rule #3: No match or no domain specified → use first coder
    # Sort by priority if available (lower = higher priority)
    coders_sorted = sorted(coders, key=lambda c: c.get("priority", 999))
    return coders_sorted[0]


def select_reviewers(
    focus: list[str] | None = None,
    project_path: str | None = None,
) -> list[dict[str, Any]]:
    """Select reviewer agents based on dispatch strategy.

    Args:
        focus: Optional focus areas to prefer
        project_path: Optional project path

    Returns:
        List of selected reviewer config dicts
    """
    reviewers = get_connected_agents(role="reviewer", project_path=project_path)
    if not reviewers:
        return []

    dispatch = get_dispatch_config(project_path)
    strategy = dispatch.get("reviewer", "all")

    if strategy == "all":
        return reviewers
    elif strategy == "first":
        return [reviewers[0]]
    elif strategy == "random":
        return [random.choice(reviewers)]
    elif strategy == "round-robin":
        # TODO: Implement round-robin with state tracking
        return [reviewers[0]]
    else:
        return reviewers


def get_judge(project_path: str | None = None) -> dict[str, Any] | None:
    """Get the configured judge agent.

    Design Rule #2: Only one judge handles disputes. No additional reviewers.

    Args:
        project_path: Optional project path

    Returns:
        Judge config dict, or None if no judge connected
    """
    judges = get_connected_agents(role="judge", project_path=project_path)
    if not judges:
        return None
    # Only one judge - return first
    return judges[0]


def has_judge(project_path: str | None = None) -> bool:
    """Check if a judge is configured.

    Args:
        project_path: Optional project path

    Returns:
        True if a judge is connected
    """
    return get_judge(project_path) is not None
