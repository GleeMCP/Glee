"""Glee CLI - Stage Manager for Your AI Orchestra."""

import json
import os
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from glee.logging import get_agent_logger, setup_logging

from .code_review import code_review as _code_review_impl
from .code_review import summarize_session as _summarize_session_impl
from .code_review import warmup_session as _warmup_session_impl
from .config import config_app
from .connect import connect_app
from .logs import logs_app
from .memory import memory_app
from .theme import LEFT_PAD, Theme, console, get_version, padded

app = typer.Typer(
    name="glee",
    help="""Stage Manager for Your AI Orchestra

Glee orchestrates AI coding agents with shared memory and code review.

Quick start:
  glee init                              Initialize project
  glee config set reviewer.primary codex Set primary reviewer
  glee status                            View configuration
  glee review src/                       Run code review
""",
    no_args_is_help=True,
)

# Register subapps
app.add_typer(config_app, name="config")
app.add_typer(memory_app, name="memory")
app.add_typer(logs_app, name="logs")
app.add_typer(connect_app, name="connect")


@app.command()
def version():
    """Show Glee version."""
    console.print(padded(Text.assemble(
        ("🎭 ", "bold"),
        ("Glee", f"bold {Theme.PRIMARY}"),
        (f" v{get_version()}", Theme.MUTED),
    ), bottom=0))
    line_width = max(20, (console.width - LEFT_PAD) // 2)
    console.print(padded(Text("─" * line_width, style=Theme.MUTED), top=0))


@app.callback()
def main_callback() -> None:
    """Initialize logging for all commands."""
    project_path = Path(os.getcwd())
    glee_dir = project_path / ".glee"
    if glee_dir.exists():
        setup_logging(project_path)
        get_agent_logger(project_path)
    else:
        setup_logging(None)


@app.command()
def start():
    """Start the Glee daemon."""
    console.print("[green]Starting Glee daemon...[/green]")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def stop():
    """Stop the Glee daemon."""
    console.print("[red]Stopping Glee daemon...[/red]")
    console.print("[yellow]Not implemented yet[/yellow]")


def check_mcp_registration(project_path: str | None = None) -> bool:
    """Check if Glee MCP server is registered in project's .mcp.json."""
    if project_path is None:
        project_path = os.getcwd()

    mcp_config = Path(project_path) / ".mcp.json"
    if not mcp_config.exists():
        return False

    try:
        with open(mcp_config) as f:
            config = json.load(f)
        mcp_servers = config.get("mcpServers", {})
        return "glee" in mcp_servers
    except Exception:
        return False


def check_hooks_registration(project_path: str | None = None) -> dict[str, bool]:
    """Check if Glee hooks are registered in .claude/settings.local.json."""
    if project_path is None:
        project_path = os.getcwd()

    settings_path = Path(project_path) / ".claude" / "settings.local.json"
    result = {"SessionStart": False, "SessionEnd": False, "PreCompact": False}

    if not settings_path.exists():
        return result

    try:
        with open(settings_path) as f:
            settings = json.load(f)
        hooks = settings.get("hooks", {})

        for hook_name in result:
            hook_list = hooks.get(hook_name, [])
            for hook_config in hook_list:
                inner_hooks = hook_config.get("hooks", [])
                for h in inner_hooks:
                    cmd = str(h.get("command", ""))
                    if "glee" in cmd:
                        result[hook_name] = True
                        break
    except Exception:
        pass

    return result


@app.command()
def status():
    """Show Glee status and current project configuration."""
    from glee.agents import registry
    from glee.config import get_project_config, get_reviewers

    # === Header ===
    console.print(padded(Text.assemble(
        ("🎭 ", "bold"),
        ("Glee", f"bold {Theme.PRIMARY}"),
        (f" v{get_version()}", Theme.MUTED),
    ), bottom=0))
    line_width = max(20, (console.width - LEFT_PAD) // 2)
    console.print(padded(Text("─" * line_width, style=Theme.MUTED), top=0, bottom=0))

    # === Agent CLIs ===
    cli_tree = Tree(f"[{Theme.HEADER}]🤖 Agent CLIs[/{Theme.HEADER}]")
    cli_agents = ["claude", "codex", "gemini"]
    for cli_name in cli_agents:
        agent = registry.get(cli_name)
        if agent and agent.is_available():
            cli_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {cli_name.title()}")
        else:
            cli_tree.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] {cli_name.title()} [{Theme.MUTED}]not found[/{Theme.MUTED}]")
    console.print(padded(cli_tree, top=0, bottom=0))

    # === Project Status ===
    config = get_project_config()
    if not config:
        console.print(padded(Panel(
            f"[{Theme.MUTED}]No project configured in current directory[/{Theme.MUTED}]\n"
            f"Run [{Theme.PRIMARY}]glee init <agent>[/{Theme.PRIMARY}] to get started",
            title="[dim]Project[/dim]",
            border_style=Theme.MUTED
        )))
        return

    project = config.get("project", {})
    project_tree = Tree(f"[{Theme.HEADER}]📁 {project.get('name')}[/{Theme.HEADER}]")

    # MCP Server registration
    mcp_registered = check_mcp_registration()
    if mcp_registered:
        project_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] MCP registered")
    else:
        project_tree.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] MCP [{Theme.MUTED}]not registered[/{Theme.MUTED}]")

    # Hooks registration
    hooks = check_hooks_registration()
    hooks_branch = project_tree.add(f"[{Theme.INFO}]🪝 Hooks[/{Theme.INFO}]")
    if hooks["SessionStart"]:
        hooks_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] SessionStart")
    else:
        hooks_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] SessionStart [{Theme.MUTED}]not set[/{Theme.MUTED}]")
    if hooks["SessionEnd"]:
        hooks_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] SessionEnd")
    else:
        hooks_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] SessionEnd [{Theme.MUTED}]not set[/{Theme.MUTED}]")
    if hooks["PreCompact"]:
        hooks_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] PreCompact")
    else:
        hooks_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] PreCompact [{Theme.MUTED}]not set[/{Theme.MUTED}]")

    # Show reviewers
    reviewers = get_reviewers()
    primary = reviewers.get("primary", "codex")
    secondary = reviewers.get("secondary")

    reviewer_branch = project_tree.add(f"[{Theme.INFO}]👥 Reviewers[/{Theme.INFO}]")
    primary_agent = registry.get(primary)
    if primary_agent and primary_agent.is_available():
        reviewer_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Primary: [{Theme.PRIMARY}]{primary}[/{Theme.PRIMARY}]")
    else:
        reviewer_branch.add(f"[{Theme.WARNING}]![/{Theme.WARNING}] Primary: [{Theme.PRIMARY}]{primary}[/{Theme.PRIMARY}] [{Theme.MUTED}]not available[/{Theme.MUTED}]")

    if secondary:
        secondary_agent = registry.get(secondary)
        if secondary_agent and secondary_agent.is_available():
            reviewer_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Secondary: [{Theme.ACCENT}]{secondary}[/{Theme.ACCENT}]")
        else:
            reviewer_branch.add(f"[{Theme.WARNING}]![/{Theme.WARNING}] Secondary: [{Theme.ACCENT}]{secondary}[/{Theme.ACCENT}] [{Theme.MUTED}]not available[/{Theme.MUTED}]")
    else:
        reviewer_branch.add(f"[{Theme.MUTED}]○ Secondary: not set[/{Theme.MUTED}]")

    console.print(padded(project_tree, top=0))


@app.command()
def agents():
    """List available agent CLIs."""
    from glee.agents import registry

    table = Table(
        title="🤖 Available Agent CLIs",
        title_style=Theme.HEADER,
        border_style=Theme.MUTED,
        header_style=f"bold {Theme.PRIMARY}",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("Agent", style=Theme.PRIMARY)
    table.add_column("Command", style=Theme.MUTED)
    table.add_column("Status", justify="center")

    for name, agent in registry.agents.items():
        if agent.is_available():
            status_text = Text("● Ready", style=Theme.SUCCESS)
        else:
            status_text = Text("○ Not found", style=Theme.MUTED)
        table.add_row(name.title(), agent.command, status_text)

    console.print(padded(table))


@app.command()
def lint(
    root: Path = typer.Option(Path("."), "--root", help="Project root containing .glee/tools"),
):
    """Validate tool manifests in .glee/tools."""
    from glee.tools.lint import lint_tools

    try:
        result = lint_tools(root)
    except FileNotFoundError as exc:
        console.print(f"[red]Schema not found: {exc}[/red]")
        raise typer.Exit(1)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Schema is invalid JSON: {exc}[/red]")
        raise typer.Exit(1)

    if not result.tool_files:
        console.print(f"[yellow]No tools found under {result.tools_dir}[/yellow]")
        raise typer.Exit(0)

    if result.errors:
        for error in result.errors:
            console.print(f"[red]{error}[/red]")
        console.print(f"[red]Found {len(result.errors)} schema error(s).[/red]")
        raise typer.Exit(1)

    console.print(f"[green]All tool manifests are valid ({len(result.tool_files)} tool(s)).[/green]")


@app.command()
def init(
    agent: str = typer.Argument(..., help="Primary agent: claude, codex, gemini, cursor, etc."),
    new_id: bool = typer.Option(False, "--new-id", help="Generate new project ID"),
):
    """Initialize Glee in current directory.

    Examples:
        glee init claude    # Integrate with Claude Code (installs SessionStart/SessionEnd hooks)
        glee init codex     # Integrate with Codex CLI
        glee init gemini    # Integrate with Gemini CLI
    """
    import uuid

    from glee.config import init_project

    valid_agents = [
        "claude", "codex", "gemini", "opencode", "crush",
        "mistral", "vibe", "cursor", "trae", "antigravity"
    ]

    if agent not in valid_agents:
        console.print(padded(Panel(
            f"Unknown agent: [{Theme.ERROR}]{agent}[/{Theme.ERROR}]\n\n"
            f"Valid agents: [{Theme.PRIMARY}]{', '.join(valid_agents)}[/{Theme.PRIMARY}]",
            title=f"[{Theme.ERROR}]Error[/{Theme.ERROR}]",
            border_style=Theme.ERROR
        )))
        raise typer.Exit(1)

    project_path = os.getcwd()
    project_id = str(uuid.uuid4()) if new_id else None

    config = init_project(project_path, project_id, agent=agent)

    # Build success tree
    init_tree = Tree(f"[{Theme.SUCCESS}]✓ Initialized Glee project[/{Theme.SUCCESS}]")
    init_tree.add(f"[{Theme.MUTED}]ID:[/{Theme.MUTED}] [{Theme.PRIMARY}]{config['project']['id'][:8]}...[/{Theme.PRIMARY}]")
    init_tree.add(f"[{Theme.MUTED}]Config:[/{Theme.MUTED}] .glee/config.yml")

    reviewers = config.get("reviewers", {})
    init_tree.add(f"[{Theme.MUTED}]Primary reviewer:[/{Theme.MUTED}] [{Theme.PRIMARY}]{reviewers.get('primary', 'codex')}[/{Theme.PRIMARY}]")

    if agent == "claude":
        integration_branch = init_tree.add(f"[{Theme.INFO}]Claude integration[/{Theme.INFO}]")
        if config.get("_mcp_registered"):
            integration_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] MCP: .mcp.json created")
        else:
            integration_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] MCP: already exists")
        if config.get("_hook_registered"):
            integration_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Hooks: SessionStart + SessionEnd")
        else:
            integration_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] Hooks: already configured")
    else:
        init_tree.add(f"[{Theme.WARNING}]![/{Theme.WARNING}] {agent.title()}: hook integration not yet implemented")

    console.print(padded(init_tree))


@app.command()
def mcp():
    """Run Glee MCP server (for Claude Code integration)."""
    import asyncio

    from glee.mcp_server import run_server

    asyncio.run(run_server())


@app.command("code-review")
def code_review_cmd(
    target: str | None = typer.Argument(None, help="What to review: file, directory, 'git:changes', 'git:staged', 'github:pr#123', or description"),
    focus: str | None = typer.Option(None, "--focus", "-f", help="Focus areas (comma-separated: security, performance, etc.)"),
    second_opinion: bool = typer.Option(False, "--second-opinion", "-2", help="Also run secondary reviewer"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be posted without posting (GitHub PRs)"),
) -> None:
    """Run code review with configured reviewer.

    Supports local targets (files, directories, git changes) and remote targets (GitHub PRs).

    Examples:
        glee code-review .                    # Review current directory
        glee code-review git:changes          # Review uncommitted changes
        glee code-review github:pr#123        # Review PR and post comments
        glee code-review github:pr#123 --dry-run  # Preview without posting
    """
    _code_review_impl(app, target, focus, second_opinion, dry_run)


@app.command("warmup-session")
def warmup_session_cmd():
    """Output session warmup context (memory, sessions, git)."""
    _warmup_session_impl()


@app.command("summarize-session")
def summarize_session_cmd(
    from_source: str = typer.Option(..., "--from", help="Agent to use: 'claude', 'codex', 'gemini'"),
    session_id: str | None = typer.Option(None, "--session-id", help="Session ID (prints only, no save)"),
):
    """Summarize the session using an LLM.

    Uses the specified agent to generate structured memory (goal, decisions, open_loops, summary).

    Examples:
        # From SessionEnd hook (stdin) → saves to DB
        glee summarize-session --from=claude

        # Manual with session ID → prints only, no save
        glee summarize-session --from=claude --session-id=abc123
    """
    _summarize_session_impl(from_source, session_id)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
