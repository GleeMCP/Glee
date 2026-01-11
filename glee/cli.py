"""Glee CLI - Stage Manager for Your AI Orchestra."""

import json
import os
from pathlib import Path
from typing import Any, cast

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from glee.logging import get_agent_logger, setup_logging

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
console = Console()


def get_version() -> str:
    """Get the package version."""
    from importlib.metadata import version
    return version("glee")


@app.command()
def version():
    """Show Glee version."""
    console.print(f"glee {get_version()}")


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
    import json

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


@app.command()
def status():
    """Show Glee status and current project configuration."""
    from glee.agents import registry
    from glee.config import get_project_config, get_reviewers

    # === Global Status ===
    console.print(f"[bold]Glee v{get_version()}[/bold]")

    # CLI availability
    cli_agents = ["claude", "codex", "gemini"]
    for i, cli_name in enumerate(cli_agents):
        agent = registry.get(cli_name)
        is_last_cli = i == len(cli_agents) - 1
        prefix = "└─" if is_last_cli else "├─"
        if agent and agent.is_available():
            console.print(f"{prefix} {cli_name.title()} CLI: [green]found ✓[/green]")
        else:
            console.print(f"{prefix} {cli_name.title()} CLI: [dim]not found[/dim]")

    console.print()

    # === Project Status ===
    config = get_project_config()
    if not config:
        console.print("[dim]Current directory: not configured[/dim]")
        return

    project = config.get("project", {})
    console.print(f"[bold]Project: {project.get('name')}[/bold]")

    # MCP Server registration
    mcp_registered = check_mcp_registration()
    mcp_status = "[green]registered ✓[/green]" if mcp_registered else "[dim]not registered[/dim]"
    console.print(f"├─ MCP: {mcp_status}")

    # Show reviewers
    reviewers = get_reviewers()
    primary = reviewers.get("primary", "codex")
    secondary = reviewers.get("secondary")

    primary_agent = registry.get(primary)
    primary_available = "✓" if primary_agent and primary_agent.is_available() else "✗"
    console.print(f"├─ Primary reviewer: [{primary_available}] {primary}")

    if secondary:
        secondary_agent = registry.get(secondary)
        secondary_available = "✓" if secondary_agent and secondary_agent.is_available() else "✗"
        console.print(f"└─ Secondary reviewer: [{secondary_available}] {secondary}")
    else:
        console.print("└─ Secondary reviewer: [dim]not set[/dim]")


@app.command()
def agents():
    """List available agent CLIs."""
    from glee.agents import registry

    table = Table(title="Available Agent CLIs")
    table.add_column("Name", style="cyan")
    table.add_column("Command", style="green")
    table.add_column("Available", style="magenta")

    for name, agent in registry.agents.items():
        available = "[green]Yes[/green]" if agent.is_available() else "[red]No[/red]"
        table.add_row(name, agent.command, available)

    console.print(table)


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


# Config subcommands
config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


# Supported config keys
CONFIG_KEYS = {
    "reviewer.primary": "Primary reviewer CLI (codex, claude, gemini)",
    "reviewer.secondary": "Secondary reviewer CLI for second opinions",
}


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g., reviewer.primary)"),
    value: str = typer.Argument(..., help="Value to set"),
):
    """Set a configuration value.

    Examples:
        glee config set reviewer.primary codex
        glee config set reviewer.secondary gemini
    """
    from glee.agents import registry
    from glee.config import get_project_config, set_reviewer

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    if key not in CONFIG_KEYS:
        console.print(f"[red]Unknown config key: {key}[/red]")
        console.print("\nAvailable keys:")
        for k, desc in CONFIG_KEYS.items():
            console.print(f"  {k}: {desc}")
        raise typer.Exit(1)

    if key.startswith("reviewer."):
        tier = key.split(".")[1]  # "primary" or "secondary"

        # Validate command
        if value not in registry.agents:
            console.print(f"[red]Unknown reviewer: {value}[/red]")
            console.print(f"Available: {', '.join(registry.agents.keys())}")
            raise typer.Exit(1)

        # Check CLI is available
        agent_instance = registry.agents[value]
        if not agent_instance.is_available():
            console.print(f"[yellow]Warning: {value} CLI is not installed[/yellow]")

        try:
            set_reviewer(command=value, tier=tier)
            console.print(f"[green]Set {key} = {value}[/green]")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@config_app.command("unset")
def config_unset(
    key: str = typer.Argument(..., help="Config key to unset"),
):
    """Unset a configuration value.

    Examples:
        glee config unset reviewer.secondary
    """
    from glee.config import clear_reviewer, get_project_config

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    if key == "reviewer.primary":
        console.print("[red]Cannot unset primary reviewer. Use 'glee config set' to change it.[/red]")
        raise typer.Exit(1)

    if key == "reviewer.secondary":
        if clear_reviewer(tier="secondary"):
            console.print(f"[green]Unset {key}[/green]")
        else:
            console.print(f"[yellow]{key} was not set[/yellow]")
        return

    console.print(f"[red]Unknown config key: {key}[/red]")
    raise typer.Exit(1)


@config_app.command("get")
def config_get(
    key: str | None = typer.Argument(None, help="Config key to get (or omit to show all)"),
):
    """Get configuration value(s).

    Examples:
        glee config get                    Show all config
        glee config get reviewer.primary   Show specific key
    """
    from glee.config import get_project_config, get_reviewers

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    reviewers = get_reviewers()

    if key is None:
        # Show all config
        console.print("[bold]Configuration:[/bold]")
        console.print(f"  reviewer.primary = {reviewers.get('primary', 'codex')}")
        secondary = reviewers.get("secondary")
        if secondary:
            console.print(f"  reviewer.secondary = {secondary}")
        else:
            console.print("  reviewer.secondary = [dim](not set)[/dim]")
        return

    if key == "reviewer.primary":
        console.print(reviewers.get("primary", "codex"))
    elif key == "reviewer.secondary":
        secondary = reviewers.get("secondary")
        if secondary:
            console.print(secondary)
        else:
            console.print("[dim](not set)[/dim]")
    else:
        console.print(f"[red]Unknown config key: {key}[/red]")
        raise typer.Exit(1)


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
        console.print(f"[red]Unknown agent: {agent}[/red]")
        console.print(f"Valid agents: {', '.join(valid_agents)}")
        raise typer.Exit(1)

    project_path = os.getcwd()
    project_id = str(uuid.uuid4()) if new_id else None

    config = init_project(project_path, project_id, agent=agent)
    console.print("[green]Initialized Glee project:[/green]")
    console.print(f"  ID: {config['project']['id']}")
    console.print(f"  Config: .glee/config.yml")

    reviewers = config.get("reviewers", {})
    console.print(f"  Primary reviewer: {reviewers.get('primary', 'codex')}")

    if agent == "claude":
        if config.get("_mcp_registered"):
            console.print("  MCP: [green].mcp.json created[/green]")
        else:
            console.print("  MCP: [dim].mcp.json already exists[/dim]")
        if config.get("_hook_registered"):
            console.print("  Hooks: [green]SessionStart + SessionEnd registered[/green]")
        else:
            console.print("  Hooks: [dim]already configured[/dim]")
    else:
        console.print(f"  {agent.title()}: [yellow]hook integration not yet implemented[/yellow]")


@app.command()
def review(
    target: str | None = typer.Argument(None, help="What to review: file, directory, 'git:changes', 'git:staged', or description"),
    focus: str | None = typer.Option(None, "--focus", "-f", help="Focus areas (comma-separated: security, performance, etc.)"),
    second_opinion: bool = typer.Option(False, "--second-opinion", "-2", help="Also run secondary reviewer"),
) -> None:
    """Run code review with configured reviewer.

    By default runs primary reviewer only. Use --second-opinion to also run secondary.
    """
    from glee.agents import registry
    from glee.agents.base import AgentResult
    from glee.config import get_project_config
    from glee.dispatch import get_primary_reviewer, get_secondary_reviewer

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    review_target = target or "."
    focus_list = [f.strip() for f in focus.split(",")] if focus else None

    # Get reviewers
    primary = get_primary_reviewer()
    reviewers_to_run = [primary]

    if second_opinion:
        secondary = get_secondary_reviewer()
        if secondary:
            reviewers_to_run.append(secondary)
        else:
            console.print("[yellow]Warning: No secondary reviewer configured[/yellow]")

    console.print("[bold]Review Plan[/bold]")
    console.print(f"  Target: {review_target}")
    console.print(f"  Reviewer(s): {', '.join(reviewers_to_run)}")
    if focus_list:
        console.print(f"  Focus: {', '.join(focus_list)}")
    console.print()

    logger.info(f"Starting review with: {', '.join(reviewers_to_run)}")
    console.print("[green]Running review...[/green]\n")

    results: dict[str, dict[str, Any]] = {}

    def run_single_review(reviewer_cli: str) -> tuple[str, AgentResult | None, str | None]:
        agent = registry.get(reviewer_cli)
        if not agent:
            return reviewer_cli, None, f"CLI {reviewer_cli} not found in registry"
        if not agent.is_available():
            return reviewer_cli, None, f"CLI {reviewer_cli} not installed"

        try:
            result = agent.run_review(target=review_target, focus=focus_list)
            return reviewer_cli, result, None
        except Exception as e:
            return reviewer_cli, None, str(e)

    # Run reviews (sequentially for now, could parallelize if both requested)
    for reviewer_cli in reviewers_to_run:
        name, result, error = run_single_review(reviewer_cli)
        results[name] = {"result": result, "error": error}

    # Display summary
    console.print()
    console.print("[bold]Review Summary[/bold]")
    console.print("=" * 60)

    all_approved = True
    for reviewer_name, data in results.items():
        if data["error"]:
            console.print(f"  {reviewer_name}: [red]Error - {data['error']}[/red]")
            all_approved = False
        elif data["result"]:
            result = data["result"]
            if result.error:
                console.print(f"  {reviewer_name}: [red]Error[/red]")
                all_approved = False
            else:
                if "NEEDS_CHANGES" in result.output.upper():
                    console.print(f"  {reviewer_name}: [yellow]Changes requested[/yellow]")
                    all_approved = False
                else:
                    console.print(f"  {reviewer_name}: [green]Approved[/green]")

    console.print()
    console.print("=" * 60)
    if all_approved:
        logger.info("Review completed: approved")
        console.print("[bold green]✓ Approved[/bold green]")
    else:
        logger.warning("Review completed: changes requested")
        console.print("[bold yellow]⚠ Changes requested[/bold yellow]")


@app.command("warmup-session")
def warmup_session():
    """Output session warmup context (memory, sessions, git)."""
    from glee.config import get_project_config
    from glee.warmup import build_warmup_text

    try:
        if not get_project_config():
            return
        output = build_warmup_text(os.getcwd())
        if not output:
            return
        console.print(output, markup=False, highlight=False)
    except Exception as e:
        console.print(f"Error: {e}", markup=False)
        raise typer.Exit(1)


@app.command("summarize-session")
def summarize_session(
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
    import sys
    from datetime import datetime
    from pathlib import Path

    from glee.agents import registry
    from glee.claude_session import (
        format_conversation_for_summary,
        get_claude_session_file,
        parse_claude_session,
    )
    from glee.config import get_project_config
    from glee.memory.capture import capture_memory

    # Set up logging to .glee/stream_logs/
    log_file: Path | None = None
    glee_dir = Path(os.getcwd()) / ".glee"
    if glee_dir.exists():
        log_dir = glee_dir / "stream_logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"summarize-session-{datetime.now().strftime('%Y%m%d')}.log"

    def log(msg: str) -> None:
        if log_file:
            with open(log_file, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] {msg}\n")

    log(f"summarize-session started with --from={from_source}")

    # Currently only Claude is supported for session summarization
    if from_source != "claude":
        log(f"Agent '{from_source}' is not supported for session summarization")
        console.print(f"[red]Agent '{from_source}' is not supported. Only 'claude' is currently supported for session summarization.[/red]")
        return

    if not get_project_config():
        log("No project config found")
        return

    try:
        # Get the agent
        agent = registry.get(from_source)
        if not agent:
            log(f"Unknown agent: {from_source}")
            console.print(f"[red]Unknown agent: {from_source}[/red]")
            return

        if not agent.is_available():
            log(f"Agent '{from_source}' is not available")
            console.print(f"[red]Agent '{from_source}' is not available[/red]")
            return

        session_file: Path | None = None
        effective_session_id: str | None = None
        save_to_db = False

        # Option 1: --session-id provided (manual - print only)
        if session_id:
            log(f"Manual mode with session_id={session_id}")
            session_file = get_claude_session_file(os.getcwd(), session_id)
            if not session_file:
                log(f"Session not found: {session_id}")
                console.print(f"[red]Session not found: {session_id}[/red]")
                raise typer.Exit(1)
            effective_session_id = session_id
            save_to_db = False

        # Option 2: Read from stdin (hook mode - save to DB)
        else:
            if sys.stdin.isatty():
                log("No stdin data (tty)")
                console.print("[red]No stdin data. Use --session-id or run from a SessionEnd hook.[/red]")
                return

            transcript_path: str | None = None
            stdin_session_id: str | None = None

            try:
                stdin_data = sys.stdin.read()
                log(f"Read stdin: {len(stdin_data)} bytes")
                if stdin_data.strip():
                    hook_data = json.loads(stdin_data)
                    transcript_path = hook_data.get("transcript_path")
                    stdin_session_id = hook_data.get("session_id")
                    log(f"Hook data: session_id={stdin_session_id}, transcript_path={transcript_path}")
            except (json.JSONDecodeError, OSError) as e:
                log(f"Failed to parse stdin JSON: {e}")
                console.print(f"[red]Failed to parse stdin JSON: {e}[/red]")
                return

            if not transcript_path:
                log("No transcript_path in stdin")
                console.print("[red]No transcript_path in stdin. Expected SessionEnd hook data.[/red]")
                return

            session_file = Path(transcript_path).expanduser()
            effective_session_id = stdin_session_id
            save_to_db = True

        if not session_file or not session_file.exists():
            log(f"Session file not found: {session_file}")
            console.print("[yellow]No session file found[/yellow]")
            return

        log(f"Parsing session file: {session_file}")
        conversation = parse_claude_session(session_file)
        if not conversation or not conversation["messages"]:
            log("No conversation found in session")
            console.print("[yellow]No conversation found in session[/yellow]")
            return

        if not effective_session_id:
            effective_session_id = conversation["session_id"]

        log(f"Conversation has {len(conversation['messages'])} messages")

        # Format conversation for the agent
        conversation_text = format_conversation_for_summary(conversation, max_chars=8000)

        console.print(f"[dim]Generating structured summary using {from_source}...[/dim]")
        log(f"Calling {from_source} to generate summary")

        # Prompt for structured output
        prompt = f"""Analyze this coding session and extract structured information.

Conversation:
{conversation_text}

Respond in this exact JSON format (no markdown, just raw JSON):
{{
  "goal": "The main task or objective (1 sentence)",
  "decisions": ["Decision 1", "Decision 2"],
  "open_loops": ["Unfinished task 1", "Unfinished task 2"],
  "summary": "2-3 sentence summary of what was accomplished"
}}

If a field doesn't apply, use an empty string or empty array. Be concise."""

        result = agent.run(prompt)
        if result.error:
            log(f"Agent error: {result.error}")
            console.print(f"[red]Error: {result.error}[/red]")
            return

        log(f"Agent returned {len(result.output)} chars")

        # Parse the JSON response
        output = result.output.strip()
        # Remove markdown code blocks if present
        if output.startswith("```"):
            output = output.split("\n", 1)[1] if "\n" in output else output
            if output.endswith("```"):
                output = output.rsplit("```", 1)[0]
            output = output.strip()

        structured: dict[str, Any] = {}
        try:
            parsed = json.loads(output)
            if not isinstance(parsed, dict):
                log(f"JSON is not a dict (got {type(parsed).__name__}), using raw output")
                console.print("[yellow]Response is not a JSON object, using raw output[/yellow]")
                structured = {"summary": output}
            else:
                structured = cast(dict[str, Any], parsed)
                log(f"Parsed structured response: {list(structured.keys())}")
        except json.JSONDecodeError as e:
            log(f"JSON parse error: {e}, using raw output")
            console.print("[yellow]Could not parse structured response, using raw output[/yellow]")
            structured = {"summary": output}

        if save_to_db:
            # Save to memory
            log(f"Saving to DB with session_id={effective_session_id}")
            capture_result = capture_memory(
                os.getcwd(),
                structured,
                source="summarize_session",
                session_id=effective_session_id,
            )

            added = capture_result.get("added", {})
            cleared = capture_result.get("cleared", {})
            log(f"Saved: added={added}, cleared={cleared}")

            if cleared:
                console.print("[bold]Cleared:[/bold]")
                for cat, count in sorted(cleared.items()):
                    console.print(f"  {cat}: {count}")
            if added:
                console.print("[bold]Added:[/bold]")
                for cat, count in sorted(added.items()):
                    console.print(f"  {cat}: {count}")
        else:
            # Print only
            log("Print mode (no save)")
            console.print("\n[bold]Structured Summary:[/bold]")
            if structured.get("goal"):
                console.print(f"[cyan]Goal:[/cyan] {structured['goal']}")
            if structured.get("decisions"):
                console.print("[cyan]Decisions:[/cyan]")
                for d in structured["decisions"]:
                    console.print(f"  • {d}")
            if structured.get("open_loops"):
                console.print("[cyan]Open Loops:[/cyan]")
                for o in structured["open_loops"]:
                    console.print(f"  • {o}")
            if structured.get("summary"):
                console.print(f"[cyan]Summary:[/cyan] {structured['summary']}")

        log("summarize-session completed successfully")
    except Exception as e:
        log(f"Exception: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Memory subcommands
memory_app = typer.Typer(help="Memory management commands")
app.add_typer(memory_app, name="memory")


@memory_app.command("add")
def memory_add(
    category: str = typer.Option(..., "--category", "-c", help="Memory category"),
    content: str = typer.Option(..., "--content", help="Content to remember"),
    metadata: str | None = typer.Option(None, "--metadata", help="JSON metadata"),
):
    """Add a memory entry."""
    from glee.memory import Memory

    memory = None
    try:
        memory = Memory(os.getcwd())

        metadata_obj: dict[str, Any] | None = None
        if metadata is not None:
            try:
                metadata_obj = json.loads(metadata)
            except json.JSONDecodeError as e:
                console.print(f"[red]Invalid JSON for --metadata: {e}[/red]")
                raise typer.Exit(1)
            if not isinstance(metadata_obj, dict):
                console.print("[red]--metadata must be a JSON object.[/red]")
                raise typer.Exit(1)

        memory_id = memory.add(category=category, content=content, metadata=metadata_obj)
        console.print(f"[green]Added memory {memory_id} to {category}[/green]")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


@memory_app.command("list")
def memory_list(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
):
    """List memories."""
    from glee.memory import Memory

    memory = None
    try:
        memory = Memory(os.getcwd())

        if limit <= 0:
            limit = 50

        if category:
            results = memory.get_by_category(category)[:limit]
            if not results:
                console.print(f"[yellow]No memories in category '{category}'[/yellow]")
                return

            title = category.replace("-", " ").replace("_", " ").title()
            console.print(f"[bold]{title} ({len(results)} entries):[/bold]")
            for r in results:
                console.print(f"\n[cyan]{r.get('id')}[/cyan] ({r.get('created_at')})")
                console.print(f"  {r.get('content')}")
            return

        categories = memory.get_categories()
        if not categories:
            console.print("[yellow]No memories found[/yellow]")
            return

        console.print("[bold]All Memories:[/bold]\n")
        for cat in categories:
            results = memory.get_by_category(cat)[:limit]
            title = cat.replace("-", " ").replace("_", " ").title()
            console.print(f"[bold cyan]{title}[/bold cyan] ({len(results)} entries)")
            for r in results:
                console.print(f"  [{r.get('id')}] {r.get('content')}")
            console.print()
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


@memory_app.command("delete")
def memory_delete(
    by: str = typer.Option(..., "--by", help="Delete by: 'id' or 'category'"),
    value: str = typer.Option(..., "--value", help="The ID or category to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm destructive actions"),
):
    """Delete memory by ID or category."""
    from glee.memory import Memory

    memory = None
    try:
        memory = Memory(os.getcwd())

        if by == "id":
            deleted = memory.delete(value)
            if deleted:
                console.print(f"[green]Deleted memory {value}[/green]")
            else:
                console.print(f"[yellow]Memory {value} not found[/yellow]")
        elif by == "category":
            if not confirm:
                if not typer.confirm(f"Delete all memories in '{value}'?"):
                    console.print("[dim]Cancelled[/dim]")
                    return
            count = memory.clear(value)
            console.print(f"[green]Deleted {count} memories from '{value}'[/green]")
        else:
            console.print("[red]--by must be 'id' or 'category'.[/red]")
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(..., help="Search query"),
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(5, "--limit", "-l", help="Max results"),
):
    """Search memories by semantic similarity."""
    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        results = memory.search(query=query, category=category, limit=limit)
        memory.close()

        if not results:
            console.print("[yellow]No memories found[/yellow]")
            return

        console.print(f"[bold]Found {len(results)} memories:[/bold]")
        for r in results:
            console.print(f"\n[cyan]{r.get('id')}[/cyan] ({r.get('category')})")
            console.print(f"  {r.get('content')}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("overview")
def memory_overview():
    """Show formatted memory overview (for LLM context)."""
    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        overview = memory.get_context()
        memory.close()

        if not overview:
            console.print("[yellow]No memories found[/yellow]")
            return

        console.print(overview)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("stats")
def memory_stats():
    """Show memory statistics."""
    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        stats = memory.stats()
        memory.close()

        console.print("[bold]Memory Statistics[/bold]")
        console.print(f"  Total: {stats['total']}")

        if stats["by_category"]:
            console.print()
            console.print("[bold]By Category:[/bold]")
            for cat, count in sorted(stats["by_category"].items()):
                console.print(f"  {cat}: {count}")

        if stats["oldest"]:
            oldest = stats["oldest"]
            if hasattr(oldest, "strftime"):
                oldest = oldest.strftime("%Y-%m-%d %H:%M")
            console.print(f"\n  Oldest: {oldest}")

        if stats["newest"]:
            newest = stats["newest"]
            if hasattr(newest, "strftime"):
                newest = newest.strftime("%Y-%m-%d %H:%M")
            console.print(f"  Newest: {newest}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Logs subcommands
logs_app = typer.Typer(help="Log management commands")
app.add_typer(logs_app, name="logs")


@logs_app.command("show")
def logs_show(
    level: str | None = typer.Option(None, "--level", "-l", help="Filter by level"),
    search: str | None = typer.Option(None, "--search", "-s", help="Search in message text"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results"),
):
    """Show recent logs."""
    from glee.logging import query_logs

    project_path = Path(os.getcwd())
    results = query_logs(project_path, level=level, search=search, limit=limit)

    if not results:
        console.print("[yellow]No logs found[/yellow]")
        return

    console.print(f"[bold]Recent logs ({len(results)} entries):[/bold]\n")
    for log in results:
        level_color = {
            "DEBUG": "dim",
            "INFO": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
        }.get(log["level"], "white")

        timestamp = log["timestamp"][:19]
        console.print(
            f"[dim]{timestamp}[/dim] [{level_color}]{log['level']:8}[/{level_color}] {log['message']}"
        )


@logs_app.command("stats")
def logs_stats():
    """Show log statistics."""
    from glee.logging import get_log_stats

    project_path = Path(os.getcwd())
    stats = get_log_stats(project_path)

    if stats["total"] == 0:
        console.print("[yellow]No logs found[/yellow]")
        return

    console.print("[bold]Log Statistics[/bold]")
    console.print(f"  Total: {stats['total']}")
    console.print()
    console.print("[bold]By Level:[/bold]")
    for level, count in sorted(stats["by_level"].items()):
        console.print(f"  {level}: {count}")


@logs_app.command("agents")
def logs_agents(
    agent: str | None = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    success_only: bool = typer.Option(False, "--success", "-s", help="Only show successful runs"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
):
    """Show agent run history."""
    from glee.logging import query_agent_logs

    project_path = Path(os.getcwd())
    results = query_agent_logs(project_path, agent=agent, success_only=success_only, limit=limit)

    if not results:
        console.print("[yellow]No agent logs found[/yellow]")
        return

    table = Table(title=f"Agent Logs (last {len(results)})")
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Time", style="dim", width=19)
    table.add_column("Agent", style="green", width=8)
    table.add_column("Duration", style="yellow", width=8)
    table.add_column("Status", width=8)
    table.add_column("Prompt", style="white", max_width=40, overflow="ellipsis")

    for log in results:
        timestamp = log["timestamp"][:19]
        duration = f"{log['duration_ms']}ms" if log["duration_ms"] else "-"
        status = "[green]OK[/green]" if log["success"] else "[red]FAIL[/red]"
        prompt = (log["prompt"][:37] + "...") if len(log["prompt"]) > 40 else log["prompt"]
        prompt = prompt.replace("\n", " ")

        table.add_row(log["id"], timestamp, log["agent"], duration, status, prompt)

    console.print(table)


@logs_app.command("detail")
def logs_detail(
    log_id: str = typer.Argument(..., help="Log ID to show details for"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Show raw output"),
):
    """Show details of a specific agent log."""
    from glee.logging import get_agent_log

    project_path = Path(os.getcwd())
    log = get_agent_log(project_path, log_id)

    if not log:
        console.print(f"[red]Log {log_id} not found[/red]")
        raise typer.Exit(1)

    console.print("[bold]Agent Log Details[/bold]")
    console.print(f"  ID: [cyan]{log['id']}[/cyan]")
    console.print(f"  Time: {log['timestamp']}")
    console.print(f"  Agent: [green]{log['agent']}[/green]")
    console.print(f"  Duration: {log['duration_ms']}ms")
    status = "[green]Success[/green]" if log["success"] else "[red]Failed[/red]"
    console.print(f"  Status: {status}")
    console.print()

    console.print("[bold]Prompt:[/bold]")
    console.print(log["prompt"])
    console.print()

    if raw and log.get("raw"):
        console.print("[bold]Raw Output:[/bold]")
        console.print(log["raw"])
    elif log.get("output"):
        console.print("[bold]Output:[/bold]")
        console.print(log["output"])

    if log.get("error"):
        console.print()
        console.print("[bold red]Error:[/bold red]")
        console.print(log["error"])


@app.command()
def mcp():
    """Run Glee MCP server (for Claude Code integration)."""
    import asyncio

    from glee.mcp_server import run_server

    asyncio.run(run_server())


if __name__ == "__main__":
    app()
