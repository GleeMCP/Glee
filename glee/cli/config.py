"""Configuration management commands."""

import typer
from rich.tree import Tree

from .theme import Theme, console, padded

config_app = typer.Typer(help="Configuration management")

# Supported config keys
CONFIG_KEYS = {
    "reviewer.primary": "Primary reviewer CLI (codex, claude, gemini)",
    "reviewer.secondary": "Secondary reviewer CLI for second opinions",
    "credentials.github": "GitHub credential label to use for this project",
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
        glee config set credentials.github github-work
    """
    from glee.agents import registry
    from glee.config import get_project_config, set_credential, set_reviewer
    from glee.connect import storage

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

    if key.startswith("credentials."):
        service = key.split(".")[1]  # "github"

        # Validate credential exists
        cred = storage.ConnectionStorage.get(value)
        if not cred:
            console.print(f"[red]Credential not found: {value}[/red]")
            console.print(f"Run: glee connect list")
            raise typer.Exit(1)

        try:
            set_credential(service=service, label=value)
            console.print(f"[green]Set {key} = {value}[/green]")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    elif key.startswith("reviewer."):
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
        glee config unset credentials.github
    """
    from glee.config import clear_credential, clear_reviewer, get_project_config

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

    if key.startswith("credentials."):
        service = key.split(".")[1]
        if clear_credential(service=service):
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
        glee config get                      Show all config
        glee config get reviewer.primary     Show specific key
        glee config get credentials.github   Show GitHub credential
    """
    from glee.config import get_credentials, get_project_config, get_reviewers

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    reviewers = get_reviewers()
    credentials = get_credentials()

    if key is None:
        # Show all config
        from glee.config import get_autonomy_config

        config_tree = Tree(f"[{Theme.HEADER}]⚙️  Configuration[/{Theme.HEADER}]")

        # Credentials
        creds_branch = config_tree.add(f"[{Theme.INFO}]🔑 Credentials[/{Theme.INFO}]")
        if credentials:
            for service, label in credentials.items():
                creds_branch.add(f"[{Theme.MUTED}]{service}:[/{Theme.MUTED}] [{Theme.PRIMARY}]{label}[/{Theme.PRIMARY}]")
        else:
            creds_branch.add(f"[{Theme.MUTED}]github:[/{Theme.MUTED}] [{Theme.MUTED}]auto-detect[/{Theme.MUTED}]")

        # Autonomy
        try:
            autonomy = get_autonomy_config()
            autonomy_branch = config_tree.add(f"[{Theme.INFO}]🤖 Autonomy[/{Theme.INFO}]")
            autonomy_branch.add(f"[{Theme.MUTED}]level:[/{Theme.MUTED}] [{Theme.PRIMARY}]{autonomy.level}[/{Theme.PRIMARY}]")

            if autonomy.checkpoint_policy:
                policy_branch = autonomy_branch.add(f"[{Theme.MUTED}]checkpoint_policy:[/{Theme.MUTED}]")
                for severity, action in autonomy.checkpoint_policy.items():
                    policy_branch.add(f"[{Theme.MUTED}]{severity}:[/{Theme.MUTED}] [{Theme.ACCENT}]{action}[/{Theme.ACCENT}]")

            if autonomy.require_approval_for:
                autonomy_branch.add(f"[{Theme.MUTED}]require_approval_for:[/{Theme.MUTED}] [{Theme.ACCENT}]{', '.join(autonomy.require_approval_for)}[/{Theme.ACCENT}]")
        except Exception:
            pass  # No autonomy config set

        # Reviewers
        reviewer_branch = config_tree.add(f"[{Theme.INFO}]👥 Reviewers[/{Theme.INFO}]")
        reviewer_branch.add(f"[{Theme.MUTED}]primary:[/{Theme.MUTED}] [{Theme.PRIMARY}]{reviewers.get('primary', 'codex')}[/{Theme.PRIMARY}]")
        secondary = reviewers.get("secondary")
        if secondary:
            reviewer_branch.add(f"[{Theme.MUTED}]secondary:[/{Theme.MUTED}] [{Theme.ACCENT}]{secondary}[/{Theme.ACCENT}]")
        else:
            reviewer_branch.add(f"[{Theme.MUTED}]secondary:[/{Theme.MUTED}] [{Theme.MUTED}]not set[/{Theme.MUTED}]")

        console.print(padded(config_tree))
        return

    if key == "reviewer.primary":
        console.print(reviewers.get("primary", "codex"))
    elif key == "reviewer.secondary":
        secondary = reviewers.get("secondary")
        if secondary:
            console.print(secondary)
        else:
            console.print("[dim](not set)[/dim]")
    elif key.startswith("credentials."):
        service = key.split(".")[1]
        label = credentials.get(service)
        if label:
            console.print(label)
        else:
            console.print("[dim](auto-detect)[/dim]")
    else:
        console.print(f"[red]Unknown config key: {key}[/red]")
        raise typer.Exit(1)


@config_app.command("list")
def config_list():
    """List all configuration values.

    Alias for 'glee config get' without arguments.
    """
    config_get(key=None)
