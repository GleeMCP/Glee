"""Configuration management for Glee."""

import os
import uuid
from pathlib import Path
from typing import IO, Any

import yaml


# XDG config directory
GLEE_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "glee"
GLEE_PROJECT_DIR = ".glee"

# Supported reviewer CLIs
SUPPORTED_REVIEWERS = ["codex", "claude", "gemini"]


def _dump_yaml(data: dict[str, Any], file: IO[str]) -> None:
    """Dump YAML with consistent formatting."""
    yaml.dump(data, file, default_flow_style=False, sort_keys=False)


def ensure_global_config() -> None:
    """Ensure global config directory exists."""
    GLEE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config_path = GLEE_CONFIG_DIR / "config.yml"
    if not config_path.exists():
        with open(config_path, "w") as f:
            _dump_yaml({
                "version": "2.0",
                "defaults": {
                    "reviewers": {"primary": "codex"},
                    "memory": {"embedding_model": "BAAI/bge-small-en-v1.5"},
                },
            }, f)

    projects_path = GLEE_CONFIG_DIR / "projects.yml"
    if not projects_path.exists():
        with open(projects_path, "w") as f:
            _dump_yaml({"projects": []}, f)


def get_projects_registry() -> list[dict[str, Any]]:
    """Get projects registry."""
    ensure_global_config()
    with open(GLEE_CONFIG_DIR / "projects.yml") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return data.get("projects", [])


def save_projects_registry(projects: list[dict[str, Any]]) -> None:
    """Save projects registry."""
    ensure_global_config()
    with open(GLEE_CONFIG_DIR / "projects.yml", "w") as f:
        _dump_yaml({"projects": projects}, f)


def update_project_registry(project_id: str, name: str, path: str) -> None:
    """Update the global projects registry."""
    projects = get_projects_registry()

    for p in projects:
        if p.get("id") == project_id:
            p["name"] = name
            p["path"] = path
            break
    else:
        projects.append({"id": project_id, "name": name, "path": path})

    save_projects_registry(projects)


def _add_to_gitignore(project_path: str, entry: str) -> None:
    """Add an entry to .gitignore if not already present."""
    gitignore_path = Path(project_path) / ".gitignore"

    if not gitignore_path.exists():
        return

    content = gitignore_path.read_text()
    lines = content.splitlines()
    if entry in lines or entry.rstrip("/") in lines:
        return

    with open(gitignore_path, "a") as f:
        if content and not content.endswith("\n"):
            f.write("\n")
        f.write(f"{entry}\n")


def register_mcp_server(project_path: str) -> bool:
    """Register Glee as an MCP server in project's .mcp.json. Idempotent."""
    import json

    project_dir = Path(project_path)
    mcp_config_path = project_dir / ".mcp.json"

    if mcp_config_path.exists():
        with open(mcp_config_path) as f:
            config = json.load(f)
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    if "glee" in config["mcpServers"]:
        return False

    config["mcpServers"]["glee"] = {
        "command": "glee",
        "args": ["mcp"],
    }

    with open(mcp_config_path, "w") as f:
        json.dump(config, f, indent=2)

    return True


def register_session_hook(project_path: str) -> bool:
    """Register Glee memory overview hook in Claude Code settings. Idempotent."""
    import json

    project_dir = Path(project_path)
    claude_dir = project_dir / ".claude"
    settings_path = claude_dir / "settings.local.json"

    claude_dir.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        with open(settings_path) as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                settings = {}
    else:
        settings = {}

    if "hooks" not in settings:
        settings["hooks"] = {}

    session_hooks = settings["hooks"].get("SessionStart", [])

    for hook_config in session_hooks:
        if isinstance(hook_config, dict):
            hooks_list = hook_config.get("hooks", [])
            for h in hooks_list:
                if isinstance(h, dict) and "glee memory overview" in h.get("command", ""):
                    return False

    glee_hook = {
        "matcher": "startup|resume|compact",
        "hooks": [
            {
                "type": "command",
                "command": "glee memory overview 2>/dev/null || true",
            }
        ],
    }

    session_hooks.append(glee_hook)
    settings["hooks"]["SessionStart"] = session_hooks

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)

    return True


def init_project(project_path: str, project_id: str | None = None, agent: str | None = None) -> dict[str, Any]:
    """Initialize a Glee project. Idempotent.

    Args:
        project_path: Path to the project directory
        project_id: Optional project ID (generated if not provided)
        agent: Primary agent to integrate with (claude, codex, gemini, or None)

    Returns dict with 'project' config and status flags.
    """
    project_path = os.path.abspath(project_path)
    glee_dir = Path(project_path) / GLEE_PROJECT_DIR

    glee_dir.mkdir(parents=True, exist_ok=True)
    (glee_dir / "sessions").mkdir(exist_ok=True)
    (glee_dir / "stream_logs").mkdir(exist_ok=True)

    config_path = glee_dir / "config.yml"

    # Check for existing config
    existing_config: dict[str, Any] = {}
    existing_id: str | None = None
    if config_path.exists():
        with open(config_path) as f:
            existing_config = yaml.safe_load(f) or {}
            if not project_id:
                existing_id = existing_config.get("project", {}).get("id")

    # Preserve existing reviewers config
    existing_reviewers = existing_config.get("reviewers", {"primary": "codex"})

    config: dict[str, Any] = {
        "project": {
            "id": project_id or existing_id or str(uuid.uuid4()),
            "name": os.path.basename(project_path),
        },
        "reviewers": existing_reviewers,
    }

    with open(config_path, "w") as f:
        _dump_yaml(config, f)

    _add_to_gitignore(project_path, ".glee/")

    # Agent-specific integrations
    mcp_registered = False
    hook_registered = False
    if agent == "claude":
        claude_code_mcp_json_exists = (Path(project_path) / ".mcp.json").exists()
        mcp_registered = register_mcp_server(project_path)
        if mcp_registered and not claude_code_mcp_json_exists:
            _add_to_gitignore(project_path, ".mcp.json")
        hook_registered = register_session_hook(project_path)

    update_project_registry(config["project"]["id"], config["project"]["name"], project_path)

    result = dict(config)
    result["_mcp_registered"] = mcp_registered
    result["_hook_registered"] = hook_registered
    return result


def get_project_config(project_path: str | None = None) -> dict[str, Any] | None:
    """Get project configuration."""
    if project_path is None:
        project_path = os.getcwd()

    config_path = Path(project_path) / GLEE_PROJECT_DIR / "config.yml"
    if not config_path.exists():
        return None

    with open(config_path) as f:
        return yaml.safe_load(f)


def save_project_config(config: dict[str, Any], project_path: str | None = None) -> None:
    """Save project configuration."""
    if project_path is None:
        project_path = os.getcwd()

    ordered = {
        "project": config.get("project", {}),
        "reviewers": config.get("reviewers", {"primary": "codex"}),
    }

    with open(Path(project_path) / GLEE_PROJECT_DIR / "config.yml", "w") as f:
        _dump_yaml(ordered, f)


def set_reviewer(
    command: str,
    tier: str = "primary",
    project_path: str | None = None,
) -> dict[str, Any]:
    """Set a reviewer preference.

    Args:
        command: CLI command (codex, claude, gemini)
        tier: "primary" or "secondary"
        project_path: Optional project path

    Returns:
        Updated reviewers config
    """
    if command not in SUPPORTED_REVIEWERS:
        raise ValueError(f"Unsupported reviewer: {command}. Supported: {', '.join(SUPPORTED_REVIEWERS)}")

    if tier not in ("primary", "secondary"):
        raise ValueError(f"Invalid tier: {tier}. Valid: primary, secondary")

    config = get_project_config(project_path)
    if not config:
        raise ValueError("Project not initialized. Run 'glee init' first.")

    reviewers = config.get("reviewers", {})
    reviewers[tier] = command

    config["reviewers"] = reviewers
    save_project_config(config, project_path)
    return reviewers


def get_reviewers(project_path: str | None = None) -> dict[str, str]:
    """Get configured reviewers.

    Returns:
        Dict with 'primary' and optionally 'secondary' reviewer CLIs
    """
    config = get_project_config(project_path)
    if not config:
        return {"primary": "codex"}
    return config.get("reviewers", {"primary": "codex"})


def clear_reviewer(tier: str = "secondary", project_path: str | None = None) -> bool:
    """Clear a reviewer preference.

    Args:
        tier: "secondary" only (primary is required)
        project_path: Optional project path

    Returns:
        True if cleared, False if not set
    """
    if tier == "primary":
        raise ValueError("Cannot clear primary reviewer. Use set_reviewer to change it.")

    config = get_project_config(project_path)
    if not config:
        return False

    reviewers = config.get("reviewers", {})
    if tier in reviewers:
        del reviewers[tier]
        config["reviewers"] = reviewers
        save_project_config(config, project_path)
        return True
    return False
