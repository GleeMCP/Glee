"""Log management commands."""

import os
from pathlib import Path

import typer
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .theme import Theme, console, padded

logs_app = typer.Typer(help="Log management commands")


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
        console.print(f"[{Theme.WARNING}]No logs found[/{Theme.WARNING}]")
        return

    console.print(Rule(f"[{Theme.HEADER}]📝 Recent Logs ({len(results)} entries)[/{Theme.HEADER}]", style=Theme.MUTED))
    console.print()
    for log in results:
        level_color = {
            "DEBUG": Theme.MUTED,
            "INFO": Theme.INFO,
            "WARNING": Theme.WARNING,
            "ERROR": Theme.ERROR,
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
        console.print(f"[{Theme.WARNING}]No logs found[/{Theme.WARNING}]")
        return

    stats_tree = Tree(f"[{Theme.HEADER}]📊 Log Statistics[/{Theme.HEADER}]")
    stats_tree.add(f"[{Theme.MUTED}]Total:[/{Theme.MUTED}] [{Theme.PRIMARY}]{stats['total']}[/{Theme.PRIMARY}]")

    level_branch = stats_tree.add(f"[{Theme.INFO}]By Level[/{Theme.INFO}]")
    level_colors = {"DEBUG": Theme.MUTED, "INFO": Theme.INFO, "WARNING": Theme.WARNING, "ERROR": Theme.ERROR}
    for level, count in sorted(stats["by_level"].items()):
        color = level_colors.get(level, "white")
        level_branch.add(f"[{color}]{level}[/{color}]: [{Theme.PRIMARY}]{count}[/{Theme.PRIMARY}]")

    console.print(padded(stats_tree))


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
        console.print(f"[{Theme.WARNING}]No agent logs found[/{Theme.WARNING}]")
        return

    table = Table(
        title=f"🤖 Agent Logs (last {len(results)})",
        title_style=Theme.HEADER,
        border_style=Theme.MUTED,
        header_style=f"bold {Theme.PRIMARY}",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("ID", style=Theme.PRIMARY, width=8)
    table.add_column("Time", style=Theme.MUTED, width=19)
    table.add_column("Agent", style=Theme.ACCENT, width=8)
    table.add_column("Duration", style=Theme.WARNING, width=8)
    table.add_column("Status", justify="center", width=8)
    table.add_column("Prompt", style="white", max_width=40, overflow="ellipsis")

    for log in results:
        timestamp = log["timestamp"][:19]
        duration = f"{log['duration_ms']}ms" if log["duration_ms"] else "-"
        status = Text("● OK", style=Theme.SUCCESS) if log["success"] else Text("✗ FAIL", style=Theme.ERROR)
        prompt = (log["prompt"][:37] + "...") if len(log["prompt"]) > 40 else log["prompt"]
        prompt = prompt.replace("\n", " ")

        table.add_row(log["id"], timestamp, log["agent"], duration, status, prompt)

    console.print(padded(table))


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
        console.print(padded(Panel(
            f"Log [{Theme.PRIMARY}]{log_id}[/{Theme.PRIMARY}] not found",
            title=f"[{Theme.ERROR}]Error[/{Theme.ERROR}]",
            border_style=Theme.ERROR
        )))
        raise typer.Exit(1)

    # Build details tree
    detail_tree = Tree(f"[{Theme.HEADER}]🔍 Agent Log Details[/{Theme.HEADER}]")
    detail_tree.add(f"[{Theme.MUTED}]ID:[/{Theme.MUTED}] [{Theme.PRIMARY}]{log['id']}[/{Theme.PRIMARY}]")
    detail_tree.add(f"[{Theme.MUTED}]Time:[/{Theme.MUTED}] {log['timestamp']}")
    detail_tree.add(f"[{Theme.MUTED}]Agent:[/{Theme.MUTED}] [{Theme.ACCENT}]{log['agent']}[/{Theme.ACCENT}]")
    detail_tree.add(f"[{Theme.MUTED}]Duration:[/{Theme.MUTED}] [{Theme.WARNING}]{log['duration_ms']}ms[/{Theme.WARNING}]")
    if log["success"]:
        detail_tree.add(f"[{Theme.MUTED}]Status:[/{Theme.MUTED}] [{Theme.SUCCESS}]✓ Success[/{Theme.SUCCESS}]")
    else:
        detail_tree.add(f"[{Theme.MUTED}]Status:[/{Theme.MUTED}] [{Theme.ERROR}]✗ Failed[/{Theme.ERROR}]")
    console.print(padded(detail_tree, bottom=0))

    console.print(padded(Panel(
        log["prompt"],
        title=f"[{Theme.INFO}]Prompt[/{Theme.INFO}]",
        border_style=Theme.MUTED,
        padding=(0, 1)
    ), top=0, bottom=0))

    if raw and log.get("raw"):
        console.print(padded(Panel(
            log["raw"],
            title=f"[{Theme.INFO}]Raw Output[/{Theme.INFO}]",
            border_style=Theme.MUTED,
            padding=(0, 1)
        ), top=0, bottom=0))
    elif log.get("output"):
        console.print(padded(Panel(
            log["output"],
            title=f"[{Theme.SUCCESS}]Output[/{Theme.SUCCESS}]",
            border_style=Theme.SUCCESS,
            padding=(0, 1)
        ), top=0, bottom=0))

    if log.get("error"):
        console.print(padded(Panel(
            log["error"],
            title=f"[{Theme.ERROR}]Error[/{Theme.ERROR}]",
            border_style=Theme.ERROR,
            padding=(0, 1)
        ), top=0))
    else:
        console.print()  # Bottom padding
