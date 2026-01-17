"""Memory management commands."""

import json
import os
from pathlib import Path
from typing import Any, cast

import typer
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from .theme import LEFT_PAD, Theme, console, padded

memory_app = typer.Typer(help="Memory management commands")


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
        console.print(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Added memory [{Theme.PRIMARY}]{memory_id}[/{Theme.PRIMARY}] to [{Theme.ACCENT}]{category}[/{Theme.ACCENT}]")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


def _format_relative_time(dt: Any) -> str:
    """Format datetime as relative time (e.g., '2 hours ago')."""
    from datetime import datetime

    if dt is None:
        return "unknown"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt

    now = datetime.now()
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        now = datetime.now(dt.tzinfo)

    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins} min{'s' if mins != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime("%b %d, %Y")


def _render_session_summaries(results: list[dict[str, Any]]) -> None:
    """Render session summaries in a tree format."""
    tree = Tree(f"[{Theme.HEADER}]🧠 Sessions[/{Theme.HEADER}]")

    for r in results:
        created_at = r.get("created_at")
        relative_time = _format_relative_time(created_at)

        # Parse metadata for session_id
        metadata_raw = r.get("metadata", {})
        metadata: dict[str, Any] = {}
        if isinstance(metadata_raw, str):
            try:
                parsed = json.loads(metadata_raw)
                if isinstance(parsed, dict):
                    metadata = cast(dict[str, Any], parsed)
            except json.JSONDecodeError:
                pass
        elif isinstance(metadata_raw, dict):
            metadata = cast(dict[str, Any], metadata_raw)

        session_id: str = str(metadata.get("session_id", "") or "")

        # Session branch with ID and time
        if session_id:
            session_label = f"[{Theme.ACCENT}]{session_id[:12]}[/{Theme.ACCENT}]  [{Theme.MUTED}]{relative_time}[/{Theme.MUTED}]"
        else:
            session_label = f"[{Theme.MUTED}]{r.get('id', '?')}[/{Theme.MUTED}]  [{Theme.MUTED}]{relative_time}[/{Theme.MUTED}]"

        session_branch = tree.add(session_label)

        # Content as child
        content = r.get("content", "").strip()
        if content:
            session_branch.add(f"[default]{content}[/default]")

    # Use Panel for consistent padding on all sides
    console.print(Padding(
        Panel(tree, border_style=Theme.MUTED, padding=(0, 2)),
        (1, 0, 0, LEFT_PAD)
    ))


@memory_app.command("list")
def memory_list(
    full: bool = typer.Option(False, "--full", "-f", help="Show full content"),
):
    """List memories."""
    from glee.memory import Memory

    memory = None
    try:
        memory = Memory(os.getcwd())

        categories = memory.get_categories()
        if not categories:
            console.print(f"[{Theme.WARNING}]No memories found[/{Theme.WARNING}]")
            return

        memory_tree = Tree(f"[{Theme.HEADER}]🧠 All Memories[/{Theme.HEADER}]")
        for cat in categories:
            results = memory.get_by_category(cat)
            title = cat.replace("-", " ").replace("_", " ").title()
            cat_branch = memory_tree.add(f"[{Theme.ACCENT}]{title}[/{Theme.ACCENT}] [{Theme.MUTED}]({len(results)})[/{Theme.MUTED}]")
            for r in results:
                mem_id = r.get('id', '')[:8]
                content = r.get('content', '')
                if not full and len(content) > 60:
                    content = content[:60] + "..."
                cat_branch.add(f"[{Theme.MUTED}]{mem_id}[/{Theme.MUTED}] {content}")
        console.print(padded(memory_tree))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


@memory_app.command("latest")
def memory_latest(
    limit: int = typer.Option(1, "--limit", "-l", help="Number of recent memories to show"),
):
    """Show the most recent memory entries.

    Examples:
        glee memory latest           Show the most recent memory
        glee memory latest -l 5      Show the 5 most recent memories
    """
    from glee.memory import Memory

    memory = None
    try:
        memory = Memory(os.getcwd())

        if limit <= 0:
            limit = 1

        results = memory.get_latest(limit=limit)
        if not results:
            console.print(f"[{Theme.WARNING}]No memories found[/{Theme.WARNING}]")
            return

        # Check if all results are session_summary category
        if all(r.get("category") == "session_summary" for r in results):
            _render_session_summaries(results)
            return

        # Generic rendering for mixed categories
        console.print()
        title = "Latest Memory" if limit == 1 else f"Latest {len(results)} Memories"
        console.print(f"[{Theme.HEADER}]{title}[/{Theme.HEADER}]")
        console.print()

        for r in results:
            category = r.get("category", "unknown")
            relative_time = _format_relative_time(r.get("created_at"))

            header = Text()
            header.append("● ", style=Theme.PRIMARY)
            header.append(f"{r.get('id', '?')}", style=f"bold {Theme.PRIMARY}")
            header.append("  ", style="default")
            header.append(f"[{category}]", style=Theme.ACCENT)
            header.append("  ", style="default")
            header.append(f"{relative_time}", style=Theme.MUTED)

            console.print(header)

            content = r.get("content", "").strip()
            if content:
                console.print(Padding(Text(content, style="default"), (0, 0, 1, 4)))

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
            console.print(f"[{Theme.WARNING}]No memories found[/{Theme.WARNING}]")
            return

        console.print(Panel(
            f"[{Theme.MUTED}]Query:[/{Theme.MUTED}] [{Theme.PRIMARY}]{query}[/{Theme.PRIMARY}]",
            title=f"[{Theme.HEADER}]🔍 Found {len(results)} memories[/{Theme.HEADER}]",
            border_style=Theme.PRIMARY
        ))
        for r in results:
            console.print(f"\n[{Theme.PRIMARY}]{r.get('id')}[/{Theme.PRIMARY}] [{Theme.ACCENT}]{r.get('category')}[/{Theme.ACCENT}]")
            console.print(f"  {r.get('content')}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("overview")
def memory_overview(
    generate: bool = typer.Option(False, "--generate", "-g", help="Generate/update overview using an AI agent"),
    agent: str | None = typer.Option(None, "--agent", "-a", help="Agent to use (claude, codex, gemini). Auto-detects if not specified."),
):
    """Show or generate project overview memory."""
    from datetime import datetime, timezone

    from glee.helpers import parse_time
    from glee.memory import Memory

    project_path = Path(os.getcwd())

    if generate:
        _generate_overview(project_path, agent)
        return

    # Read mode: show existing overview
    try:
        memory = Memory(str(project_path))
        entries = memory.get_by_category("overview")
        memory.close()

        if not entries:
            console.print("[yellow]No overview memory found.[/yellow]")
            console.print("[dim]Run: glee memory overview --generate[/dim]")
            return

        entry = entries[0]
        content = (entry.get("content") or "").strip()

        # Check age
        created_at = entry.get("created_at")
        age_info = ""
        age_days = 0
        if created_at:
            created_time = parse_time(created_at)
            if created_time:
                now = datetime.now(timezone.utc)
                if created_time.tzinfo is None:
                    created_time = created_time.replace(tzinfo=timezone.utc)
                age_days = (now - created_time).days
                if age_days == 0:
                    age_info = "today"
                elif age_days == 1:
                    age_info = "1 day ago"
                else:
                    age_info = f"{age_days} days ago"

        if age_info:
            console.print(f"[dim]Last updated: {age_info}[/dim]")
            if age_days >= 7:
                console.print("[yellow]Stale - run: glee memory overview --generate[/yellow]")
            console.print()

        console.print(Markdown(content))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _generate_overview(project_path: Path, agent_name: str | None = None) -> None:
    """Generate project overview using an AI agent."""
    from glee.agents import registry
    from glee.memory import Memory

    # Find available agent
    agent_order = ["claude", "codex", "gemini"]
    if agent_name:
        agent_order = [agent_name]

    agent = None
    for name in agent_order:
        candidate = registry.get(name)
        if candidate and candidate.is_available():
            agent = candidate
            break

    if not agent:
        if agent_name:
            console.print(f"[red]Agent '{agent_name}' not available.[/red]")
        else:
            console.print("[red]No AI agent available. Install claude, codex, or gemini CLI.[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]Using {agent.name} to generate overview...[/dim]")

    # Gather project context
    context_lines: list[str] = []

    # Documentation files
    doc_files = [
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "docs/README.md",
        "docs/architecture.md",
    ]

    for doc_file in doc_files:
        doc_path = project_path / doc_file
        if doc_path.exists():
            try:
                content = doc_path.read_text()
                if len(content) > 5000:
                    content = content[:5000] + "\n\n... (truncated)"
                context_lines.append(f"## {doc_file}\n```\n{content}\n```\n")
            except Exception:
                pass

    # Package configuration
    package_files = [
        ("pyproject.toml", "toml"),
        ("package.json", "json"),
        ("Cargo.toml", "toml"),
        ("go.mod", "go"),
    ]

    for pkg_file, lang in package_files:
        pkg_path = project_path / pkg_file
        if pkg_path.exists():
            try:
                content = pkg_path.read_text()
                if len(content) > 3000:
                    content = content[:3000] + "\n\n... (truncated)"
                context_lines.append(f"## {pkg_file}\n```{lang}\n{content}\n```\n")
            except Exception:
                pass

    # Directory structure
    def get_tree(path: Path, prefix: str = "", depth: int = 0) -> list[str]:
        if depth > 3:  # Limit depth for CLI
            return []
        tree_lines: list[str] = []
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            items = [i for i in items if not i.name.startswith(".") and i.name not in (
                "node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build",
                "target", ".pytest_cache", ".mypy_cache"
            )]
            for i, item in enumerate(items[:20]):
                is_last = i == len(items) - 1 or i == 19
                connector = "└── " if is_last else "├── "
                tree_lines.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    tree_lines.extend(get_tree(item, prefix + extension, depth + 1))
        except PermissionError:
            pass
        return tree_lines

    tree = get_tree(project_path)
    context_lines.append(f"## Directory Structure\n```\n" + "\n".join(tree) + "\n```\n")

    # Build prompt
    prompt = f"""Analyze this project and create a comprehensive overview summary.

# Project Context
{"".join(context_lines)}

# Task
Create a project overview covering:
- **Architecture**: Key patterns, module organization, data flow, entry points
- **Conventions**: Coding standards, naming patterns, file organization
- **Dependencies**: Key libraries and their purposes
- **Decisions**: Notable technical choices and trade-offs

Output ONLY the overview content in markdown format, starting with "# Project Overview".
Do not include any other text, explanations, or tool calls - just the overview itself.
"""

    # Run agent
    console.print(f"[dim]Analyzing project...[/dim]")
    result = agent.run(prompt)

    if not result.success:
        console.print(f"[red]Agent failed: {result.error}[/red]")
        raise typer.Exit(1)

    overview_content = result.output.strip()

    # Basic validation
    if not overview_content or len(overview_content) < 100:
        console.print("[red]Agent returned empty or too short response.[/red]")
        raise typer.Exit(1)

    # Clear existing and save new
    memory = Memory(str(project_path))
    memory.clear("overview")
    memory.add(category="overview", content=overview_content)
    memory.close()

    console.print(f"[green]Overview generated and saved.[/green]")
    console.print()
    console.print(overview_content)


@memory_app.command("stats")
def memory_stats():
    """Show memory statistics."""
    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        stats = memory.stats()
        memory.close()

        stats_tree = Tree(f"[{Theme.HEADER}]📊 Memory Statistics[/{Theme.HEADER}]")
        stats_tree.add(f"[{Theme.MUTED}]Total:[/{Theme.MUTED}] [{Theme.PRIMARY}]{stats['total']}[/{Theme.PRIMARY}]")

        if stats["by_category"]:
            cat_branch = stats_tree.add(f"[{Theme.INFO}]By Category[/{Theme.INFO}]")
            for cat, count in sorted(stats["by_category"].items()):
                cat_branch.add(f"[{Theme.ACCENT}]{cat}[/{Theme.ACCENT}]: [{Theme.PRIMARY}]{count}[/{Theme.PRIMARY}]")

        if stats["oldest"] or stats["newest"]:
            time_branch = stats_tree.add(f"[{Theme.INFO}]Time Range[/{Theme.INFO}]")
            if stats["oldest"]:
                oldest = stats["oldest"]
                if hasattr(oldest, "strftime"):
                    oldest = oldest.strftime("%Y-%m-%d %H:%M")
                time_branch.add(f"[{Theme.MUTED}]Oldest:[/{Theme.MUTED}] {oldest}")
            if stats["newest"]:
                newest = stats["newest"]
                if hasattr(newest, "strftime"):
                    newest = newest.strftime("%Y-%m-%d %H:%M")
                time_branch.add(f"[{Theme.MUTED}]Newest:[/{Theme.MUTED}] {newest}")

        console.print(padded(stats_tree))

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
