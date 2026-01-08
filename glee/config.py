"""Configuration management for Glee."""

import os
import secrets
import string
import uuid
from pathlib import Path
from typing import IO, Any

import yaml


def _generate_agent_name(command: str) -> str:
    """Generate unique agent name like 'claude-a1b2c3'."""
    chars = string.ascii_lowercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(6))
    return f"{command}-{suffix}"

# XDG config directory
GLEE_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "glee"
GLEE_PROJECT_DIR = ".glee"


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
                "version": "1.0",
                "defaults": {
                    "dispatch": {"coder": "first", "reviewer": "all"},
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

    # Skip if .gitignore doesn't exist
    if not gitignore_path.exists():
        return

    content = gitignore_path.read_text()
    # Check for exact line match (with or without trailing newline)
    lines = content.splitlines()
    if entry in lines or entry.rstrip("/") in lines:
        return  # Already present

    # Append to existing file
    with open(gitignore_path, "a") as f:
        # Add newline if file doesn't end with one
        if content and not content.endswith("\n"):
            f.write("\n")
        f.write(f"{entry}\n")


def register_mcp_server(project_path: str) -> bool:
    """Register Glee as an MCP server in project's .claude/settings.local.json. Idempotent.

    Returns True if registration was added, False if already registered.
    """
    import json
    import shutil

    project_path = Path(project_path)
    claude_dir = project_path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    settings_path = claude_dir / "settings.local.json"

    # Load existing settings or create empty
    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)
    else:
        settings = {}

    # Initialize mcpServers if not present
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    # Check if already registered
    if "glee" in settings["mcpServers"]:
        return False  # Already registered

    # Find glee executable
    glee_path = shutil.which("glee")
    if not glee_path:
        # Try uv run glee as fallback
        glee_path = "glee"

    # Register Glee MCP server
    settings["mcpServers"]["glee"] = {
        "command": glee_path,
        "args": ["mcp"],
    }

    # Write settings back
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)

    return True


def init_project(project_path: str, project_id: str | None = None) -> dict[str, Any]:
    """Initialize a Glee project. Idempotent - safe to run multiple times.

    Returns dict with 'project' config and 'mcp_registered' bool.
    """
    project_path = os.path.abspath(project_path)
    glee_dir = Path(project_path) / GLEE_PROJECT_DIR

    glee_dir.mkdir(parents=True, exist_ok=True)
    (glee_dir / "sessions").mkdir(exist_ok=True)

    config_path = glee_dir / "config.yml"

    # Check for existing config if not forcing new ID
    existing_config: dict[str, Any] | None = None
    existing_id: str | None = None
    if config_path.exists():
        with open(config_path) as f:
            existing_config = yaml.safe_load(f) or {}
            existing_id = existing_config.get("project", {}).get("id") if not project_id else None

    # Preserve existing agents if re-initializing
    existing_agents = existing_config.get("agents", []) if existing_config else []
    existing_dispatch = existing_config.get("dispatch", {"coder": "first", "reviewer": "all"}) if existing_config else {"coder": "first", "reviewer": "all"}

    config: dict[str, Any] = {
        "project": {
            "id": project_id or existing_id or str(uuid.uuid4()),
            "name": os.path.basename(project_path),
            "path": project_path,
        },
        "agents": existing_agents,
        "dispatch": existing_dispatch,
    }

    with open(config_path, "w") as f:
        _dump_yaml(config, f)

    # Add .glee/ to .gitignore (idempotent)
    _add_to_gitignore(project_path, ".glee/")

    # Register MCP server with Claude in project-local settings (idempotent)
    mcp_registered = register_mcp_server(project_path)

    update_project_registry(config["project"]["id"], config["project"]["name"], project_path)

    # Return config with mcp registration status
    result = dict(config)
    result["_mcp_registered"] = mcp_registered
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
    """Save project configuration with correct key ordering."""
    if project_path is None:
        project_path = os.getcwd()

    ordered = {
        "project": config.get("project", {}),
        "agents": config.get("agents", []),
        "dispatch": config.get("dispatch", {"coder": "first", "reviewer": "all"}),
    }

    with open(Path(project_path) / GLEE_PROJECT_DIR / "config.yml", "w") as f:
        _dump_yaml(ordered, f)


def connect_agent(
    command: str,
    role: str,
    domain: list[str] | None = None,
    focus: list[str] | None = None,
    priority: int | None = None,
    project_path: str | None = None,
) -> dict[str, Any]:
    """Connect an agent to the project."""
    config = get_project_config(project_path)
    if not config:
        raise ValueError("Project not initialized. Run 'glee init' first.")

    # Generate unique name
    name = _generate_agent_name(command)

    # Build agent config in correct order: name, command, role, domain/focus, priority
    agent_config: dict[str, Any] = {"name": name, "command": command, "role": role}
    if role == "coder":
        if domain:
            agent_config["domain"] = domain
        if priority is not None:
            agent_config["priority"] = priority
    elif role == "reviewer":
        if focus:
            agent_config["focus"] = focus
    # Judge role doesn't need additional config fields

    # Add new agent (always new since name is unique)
    agents = config.get("agents", [])
    agents.append(agent_config)

    config["agents"] = agents
    save_project_config(config, project_path)
    return agent_config


def disconnect_agent(
    agent_name: str,
    role: str | None = None,
    project_path: str | None = None,
) -> bool:
    """Disconnect an agent from the project."""
    config = get_project_config(project_path)
    if not config:
        return False

    agents = config.get("agents", [])
    original_len = len(agents)

    if role:
        agents = [a for a in agents if not (a.get("name") == agent_name and a.get("role") == role)]
    else:
        agents = [a for a in agents if a.get("name") != agent_name]

    if len(agents) < original_len:
        config["agents"] = agents
        save_project_config(config, project_path)
        return True
    return False


def get_connected_agents(role: str | None = None, project_path: str | None = None) -> list[dict[str, Any]]:
    """Get connected agents."""
    config = get_project_config(project_path)
    if not config:
        return []

    agents = config.get("agents", [])
    if role:
        agents = [a for a in agents if a.get("role") == role]
    return agents


def get_dispatch_config(project_path: str | None = None) -> dict[str, str]:
    """Get dispatch configuration."""
    config = get_project_config(project_path)
    if not config:
        return {"coder": "first", "reviewer": "all"}
    return config.get("dispatch", {"coder": "first", "reviewer": "all"})


def get_project_context(project_path: str | None = None) -> str | None:
    """Get project context for hook injection."""
    config = get_project_config(project_path)
    if not config:
        return None

    project = config.get("project", {})
    agents = config.get("agents", [])

    lines = [f"## Project: {project.get('name', 'Unknown')}", ""]

    coders = [a for a in agents if a.get("role") == "coder"]
    reviewers = [a for a in agents if a.get("role") == "reviewer"]
    judges = [a for a in agents if a.get("role") == "judge"]

    if coders:
        lines.append("### Coders")
        for a in coders:
            cmd = a.get("command", "unknown")
            domain = ", ".join(a.get("domain", []))
            lines.append(f"- {a.get('name')} ({cmd}): {domain}")
        lines.append("")

    if reviewers:
        lines.append("### Reviewers")
        for a in reviewers:
            cmd = a.get("command", "unknown")
            focus = ", ".join(a.get("focus", []))
            lines.append(f"- {a.get('name')} ({cmd}): {focus}")
        lines.append("")

    if judges:
        lines.append("### Judges")
        for a in judges:
            cmd = a.get("command", "unknown")
            lines.append(f"- {a.get('name')} ({cmd}): arbitrates disputes")
        lines.append("")

    return "\n".join(lines)
