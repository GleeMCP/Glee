"""Connect AI providers and services."""

import typer
from rich.padding import Padding
from rich.text import Text
from rich.tree import Tree

from .theme import Theme, console, padded

connect_app = typer.Typer(help="Connect AI providers")


def _do_codex_oauth(label: str) -> bool:
    """Run Codex OAuth flow. Returns True on success."""
    import asyncio
    import time

    from glee.connect import storage
    from glee.connect.codex import authenticate, extract_account_id

    try:
        tokens, error = asyncio.run(authenticate())

        if error:
            console.print(f"[{Theme.ERROR}]Authentication failed: {error}[/{Theme.ERROR}]")
            return False

        if not tokens:
            console.print(f"[{Theme.ERROR}]No tokens received[/{Theme.ERROR}]")
            return False

        account_id = extract_account_id(tokens.access_token)
        expires_ms = int((time.time() + tokens.expires_in) * 1000)

        # Use API key if available (from token exchange), otherwise fall back to access_token
        access_token = tokens.api_key if tokens.api_key else tokens.access_token

        # Check if credential with same label exists
        existing = storage.ConnectionStorage.get(label)

        credential = storage.AIProviderOAuthCredential(
            id=existing.id if existing else "",
            label=label,
            sdk="openai",
            vendor="openai",
            refresh=tokens.refresh_token,
            access=access_token,
            expires=expires_ms,
            account_id=account_id,
        )

        if existing:
            storage.ConnectionStorage.update(existing.id, credential)
            console.print(f"[{Theme.SUCCESS}]✓ Updated {label}[/{Theme.SUCCESS}]")
        else:
            storage.ConnectionStorage.add(credential)
            console.print(f"[{Theme.SUCCESS}]✓ Added {label}[/{Theme.SUCCESS}]")

        if account_id:
            console.print(f"  [{Theme.MUTED}]Account:[/{Theme.MUTED}] {account_id}")
        if tokens.api_key:
            console.print(f"  [{Theme.MUTED}]API Key:[/{Theme.MUTED}] {tokens.api_key[:20]}...")
        return True

    except Exception as e:
        console.print(f"[{Theme.ERROR}]Error: {e}[/{Theme.ERROR}]")
        return False


def _do_copilot_oauth(label: str) -> bool:
    """Run GitHub Copilot OAuth flow. Returns True on success."""
    import asyncio

    from glee.connect import storage
    from glee.connect.copilot import authenticate

    try:
        tokens, error = asyncio.run(authenticate())

        if error:
            console.print(f"[{Theme.ERROR}]Authentication failed: {error}[/{Theme.ERROR}]")
            return False

        if not tokens:
            console.print(f"[{Theme.ERROR}]No tokens received[/{Theme.ERROR}]")
            return False

        # Check if credential with same label exists
        existing = storage.ConnectionStorage.get(label)

        credential = storage.AIProviderOAuthCredential(
            id=existing.id if existing else "",
            label=label,
            sdk="openai",  # Copilot uses OpenAI-compatible API
            vendor="github",
            refresh=tokens.access_token,  # Same token for both
            access=tokens.access_token,
            expires=0,  # Doesn't expire
        )

        if existing:
            storage.ConnectionStorage.update(existing.id, credential)
            console.print(f"[{Theme.SUCCESS}]✓ Updated {label}[/{Theme.SUCCESS}]")
        else:
            storage.ConnectionStorage.add(credential)
            console.print(f"[{Theme.SUCCESS}]✓ Added {label}[/{Theme.SUCCESS}]")

        return True

    except Exception as e:
        console.print(f"[{Theme.ERROR}]Error: {e}[/{Theme.ERROR}]")
        return False


@connect_app.callback(invoke_without_command=True)
def connect_tui(ctx: typer.Context):
    """Connect AI providers and services.

    Examples:
        glee connect          # Interactive setup
        glee connect status   # Show connected providers
    """
    if ctx.invoked_subcommand is not None:
        return

    from rich.prompt import Prompt

    from glee.connect import storage

    # Build connection menu with categories
    console.print()
    console.print(f"  [{Theme.MUTED}]─── AI Providers ───[/{Theme.MUTED}]")
    console.print(f"    [{Theme.PRIMARY}]1[/{Theme.PRIMARY}]  Codex        [{Theme.MUTED}]· OpenAI OAuth[/{Theme.MUTED}]")
    console.print(f"    [{Theme.PRIMARY}]2[/{Theme.PRIMARY}]  Copilot      [{Theme.MUTED}]· GitHub OAuth[/{Theme.MUTED}]")
    console.print(f"    [{Theme.PRIMARY}]3[/{Theme.PRIMARY}]  OpenRouter   [{Theme.MUTED}]· Multi-model gateway[/{Theme.MUTED}]")
    console.print(f"    [{Theme.PRIMARY}]4[/{Theme.PRIMARY}]  OpenAI SDK   [{Theme.MUTED}]· Groq, Together, etc.[/{Theme.MUTED}]")
    console.print(f"    [{Theme.PRIMARY}]5[/{Theme.PRIMARY}]  Anthropic    [{Theme.MUTED}]· Direct API[/{Theme.MUTED}]")
    console.print(f"    [{Theme.PRIMARY}]6[/{Theme.PRIMARY}]  Vertex AI    [{Theme.MUTED}]· Google Cloud[/{Theme.MUTED}]")
    console.print(f"    [{Theme.PRIMARY}]7[/{Theme.PRIMARY}]  Bedrock      [{Theme.MUTED}]· AWS[/{Theme.MUTED}]")
    console.print()
    console.print(f"  [{Theme.MUTED}]─── Services ───[/{Theme.MUTED}]")
    console.print(f"    [{Theme.PRIMARY}]8[/{Theme.PRIMARY}]  GitHub       [{Theme.MUTED}]· PR reviews, API access[/{Theme.MUTED}]")
    console.print()

    choice = Prompt.ask(f"  [{Theme.PRIMARY}]Select[/{Theme.PRIMARY}]", show_default=False, default="")
    if not choice:
        return

    label = Prompt.ask(f"  [{Theme.PRIMARY}]Label[/{Theme.PRIMARY}]")
    if not label:
        return

    if choice == "1":  # Codex OAuth
        _do_codex_oauth(label)

    elif choice == "2":  # Copilot OAuth
        _do_copilot_oauth(label)

    elif choice == "3":  # OpenRouter
        console.print()
        console.print(f"  [{Theme.MUTED}]Get your API key at: https://openrouter.ai/keys[/{Theme.MUTED}]")
        console.print()
        api_key = Prompt.ask(f"  [{Theme.PRIMARY}]API key[/{Theme.PRIMARY}]", password=True)
        if api_key:
            existing = storage.ConnectionStorage.get(label)
            credential = storage.AIProviderAPICredential(
                id=existing.id if existing else "",
                label=label,
                sdk="openrouter",
                vendor="openrouter",
                key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            if existing:
                storage.ConnectionStorage.update(existing.id, credential)
                console.print(f"  [{Theme.SUCCESS}]✓ Updated {label}[/{Theme.SUCCESS}]")
            else:
                storage.ConnectionStorage.add(credential)
                console.print(f"  [{Theme.SUCCESS}]✓ Added {label}[/{Theme.SUCCESS}]")

    elif choice == "4":  # OpenAI SDK
        from rich import box
        from rich.table import Table

        vendors = list(storage.VENDOR_URLS.items())

        vendor_table = Table(show_header=True, header_style=f"bold {Theme.HEADER}", box=box.ROUNDED, title="OpenAI-Compatible Providers", title_style=f"bold {Theme.PRIMARY}")
        vendor_table.add_column("#", style=f"bold {Theme.PRIMARY}", justify="right")
        vendor_table.add_column("Vendor", style=Theme.PRIMARY)
        vendor_table.add_column("Base URL", style=Theme.MUTED)

        for i, (name, url) in enumerate(vendors, 1):
            vendor_table.add_row(str(i), name, url)

        console.print()
        console.print(Padding(vendor_table, (0, 2)))
        console.print()

        ep_choice = Prompt.ask(f"  [{Theme.PRIMARY}]Vendor (number or name)[/{Theme.PRIMARY}]", show_default=False, default="")
        if ep_choice.isdigit() and 1 <= int(ep_choice) <= len(vendors):
            vendor, base_url = vendors[int(ep_choice) - 1]
        else:
            vendor = ep_choice
            base_url = Prompt.ask(f"  [{Theme.PRIMARY}]Base URL[/{Theme.PRIMARY}]")

        api_key = Prompt.ask(f"  [{Theme.PRIMARY}]API key[/{Theme.PRIMARY}]", default="")

        existing = storage.ConnectionStorage.get(label)
        credential = storage.AIProviderAPICredential(
            id=existing.id if existing else "",
            label=label,
            sdk="openai",
            vendor=vendor,
            key=api_key,
            base_url=base_url,
        )
        if existing:
            storage.ConnectionStorage.update(existing.id, credential)
            console.print(f"  [{Theme.SUCCESS}]✓ Updated {label}[/{Theme.SUCCESS}]")
        else:
            storage.ConnectionStorage.add(credential)
            console.print(f"  [{Theme.SUCCESS}]✓ Added {label}[/{Theme.SUCCESS}]")

    elif choice == "5":  # Anthropic direct
        api_key = Prompt.ask(f"  [{Theme.PRIMARY}]API key[/{Theme.PRIMARY}]")
        if api_key:
            existing = storage.ConnectionStorage.get(label)
            credential = storage.AIProviderAPICredential(
                id=existing.id if existing else "",
                label=label,
                sdk="anthropic",
                vendor="anthropic",
                key=api_key,
                base_url="https://api.anthropic.com",
            )
            if existing:
                storage.ConnectionStorage.update(existing.id, credential)
                console.print(f"  [{Theme.SUCCESS}]✓ Updated {label}[/{Theme.SUCCESS}]")
            else:
                storage.ConnectionStorage.add(credential)
                console.print(f"  [{Theme.SUCCESS}]✓ Added {label}[/{Theme.SUCCESS}]")

    elif choice == "6":  # Vertex AI
        console.print()
        console.print(f"  [{Theme.MUTED}]Vertex AI uses Google Cloud credentials (ADC)[/{Theme.MUTED}]")
        console.print(f"  [{Theme.MUTED}]Run: gcloud auth application-default login[/{Theme.MUTED}]")
        console.print()
        project_id = Prompt.ask(f"  [{Theme.PRIMARY}]GCP Project ID[/{Theme.PRIMARY}]")
        region = Prompt.ask(f"  [{Theme.PRIMARY}]Region[/{Theme.PRIMARY}]", default="us-central1")
        if project_id:
            existing = storage.ConnectionStorage.get(label)
            credential = storage.AIProviderAPICredential(
                id=existing.id if existing else "",
                label=label,
                sdk="vertex",
                vendor="google",
                key=project_id,  # Store project ID in key field
                base_url=region,  # Store region in base_url field
            )
            if existing:
                storage.ConnectionStorage.update(existing.id, credential)
                console.print(f"  [{Theme.SUCCESS}]✓ Updated {label}[/{Theme.SUCCESS}]")
            else:
                storage.ConnectionStorage.add(credential)
                console.print(f"  [{Theme.SUCCESS}]✓ Added {label}[/{Theme.SUCCESS}]")

    elif choice == "7":  # Bedrock
        console.print()
        console.print(f"  [{Theme.MUTED}]Bedrock uses AWS credentials[/{Theme.MUTED}]")
        console.print(f"  [{Theme.MUTED}]Configure: aws configure[/{Theme.MUTED}]")
        console.print()
        region = Prompt.ask(f"  [{Theme.PRIMARY}]AWS Region[/{Theme.PRIMARY}]", default="us-east-1")
        existing = storage.ConnectionStorage.get(label)
        credential = storage.AIProviderAPICredential(
            id=existing.id if existing else "",
            label=label,
            sdk="bedrock",
            vendor="aws",
            key="",  # Uses AWS credentials from environment
            base_url=region,  # Store region in base_url field
        )
        if existing:
            storage.ConnectionStorage.update(existing.id, credential)
            console.print(f"  [{Theme.SUCCESS}]✓ Updated {label}[/{Theme.SUCCESS}]")
        else:
            storage.ConnectionStorage.add(credential)
            console.print(f"  [{Theme.SUCCESS}]✓ Added {label}[/{Theme.SUCCESS}]")

    elif choice == "8":  # GitHub
        console.print()
        console.print(f"  [{Theme.MUTED}]GitHub Personal Access Token[/{Theme.MUTED}]")
        console.print(f"  [{Theme.MUTED}]Create at: https://github.com/settings/tokens[/{Theme.MUTED}]")
        console.print(f"  [{Theme.MUTED}]Classic token scopes: repo, read:org[/{Theme.MUTED}]")
        console.print(f"  [{Theme.MUTED}]Fine-grained: Contents (read/write), Pull requests (read/write)[/{Theme.MUTED}]")
        console.print()
        token = Prompt.ask(f"  [{Theme.PRIMARY}]Token[/{Theme.PRIMARY}]", password=True)
        if token:
            # Show masked confirmation
            masked = token[:4] + "*" * (len(token) - 8) + token[-4:] if len(token) > 8 else "*" * len(token)
            console.print(f"  [{Theme.MUTED}]Token: {masked}[/{Theme.MUTED}]")
            # Check if credential with same label exists
            existing = storage.ConnectionStorage.get(label)
            credential = storage.ServiceCredential(
                id=existing.id if existing else "",
                label=label,
                vendor="github",
                key=token,
                base_url="https://api.github.com",
            )
            if existing:
                storage.ConnectionStorage.update(existing.id, credential)
                console.print(f"  [{Theme.SUCCESS}]✓ Updated {label}[/{Theme.SUCCESS}]")
            else:
                storage.ConnectionStorage.add(credential)
                console.print(f"  [{Theme.SUCCESS}]✓ Added {label}[/{Theme.SUCCESS}]")


@connect_app.command("status")
def connect_status():
    """Show connection status for all providers.

    Examples:
        glee connect status
    """
    from glee.connect import storage

    console.print(padded(Text.assemble(
        ("🔌 ", "bold"),
        ("Connected Providers", f"bold {Theme.PRIMARY}"),
    ), bottom=0))

    creds = storage.ConnectionStorage.all()
    if not creds:
        console.print(padded(Text("No providers connected. Run: glee connect", style=Theme.MUTED)))
        return

    auth_tree = Tree(f"[{Theme.HEADER}]Credentials[/{Theme.HEADER}]")

    for c in creds:
        if isinstance(c, storage.AIProviderOAuthCredential):
            status = f"[{Theme.WARNING}]expired[/{Theme.WARNING}]" if c.is_expired() else f"[{Theme.SUCCESS}]active[/{Theme.SUCCESS}]"
            branch = auth_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {c.label} [{Theme.ACCENT}]oauth[/{Theme.ACCENT}] {status}")
            branch.add(f"[{Theme.MUTED}]id:[/{Theme.MUTED}] {c.id}")
            branch.add(f"[{Theme.MUTED}]vendor:[/{Theme.MUTED}] {c.vendor} [{Theme.ACCENT}]{c.sdk}[/{Theme.ACCENT}]")
            if c.account_id:
                branch.add(f"[{Theme.MUTED}]account:[/{Theme.MUTED}] {c.account_id}")
        elif isinstance(c, storage.AIProviderAPICredential):
            masked = c.key[:8] + "..." if len(c.key) > 8 else "***"
            branch = auth_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {c.label} [{Theme.MUTED}]{masked}[/{Theme.MUTED}]")
            branch.add(f"[{Theme.MUTED}]id:[/{Theme.MUTED}] {c.id}")
            branch.add(f"[{Theme.MUTED}]vendor:[/{Theme.MUTED}] {c.vendor} [{Theme.ACCENT}]{c.sdk}[/{Theme.ACCENT}]")
            if c.base_url:
                branch.add(f"[{Theme.MUTED}]url:[/{Theme.MUTED}] {c.base_url}")
        else:  # ServiceCredential
            masked = c.key[:8] + "..." if len(c.key) > 8 else "***"
            branch = auth_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {c.label} [{Theme.MUTED}]{masked}[/{Theme.MUTED}]")
            branch.add(f"[{Theme.MUTED}]id:[/{Theme.MUTED}] {c.id}")
            branch.add(f"[{Theme.MUTED}]vendor:[/{Theme.MUTED}] {c.vendor} [{Theme.ACCENT}]service[/{Theme.ACCENT}]")
            if c.base_url:
                branch.add(f"[{Theme.MUTED}]url:[/{Theme.MUTED}] {c.base_url}")

    console.print(padded(auth_tree))


@connect_app.command("list")
def connect_list(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for piping"),
):
    """List all connected providers.

    Examples:
        glee connect list
        glee connect list --json | jq '.[] | .label'
    """
    import json

    from glee.connect import storage

    creds = storage.ConnectionStorage.all()

    if json_output:
        data = [
            {"id": c.id, "label": c.label, "type": c.type, "vendor": c.vendor, "sdk": c.sdk}
            for c in creds
        ]
        print(json.dumps(data, indent=2))
        return

    if not creds:
        console.print(padded(f"[{Theme.WARNING}]No providers connected. Run: glee connect[/{Theme.WARNING}]"))
        return

    from rich import box
    from rich.table import Table

    console.print(padded(Text.assemble(
        ("🔑 ", "bold"),
        ("Credentials", f"bold {Theme.PRIMARY}"),
    ), bottom=0))

    table = Table(show_header=True, header_style=f"bold {Theme.HEADER}", box=box.SIMPLE_HEAD)
    table.add_column("Type", style=Theme.ACCENT)
    table.add_column("ID", style=Theme.MUTED)
    table.add_column("Label", style=Theme.PRIMARY)
    table.add_column("Vendor")
    table.add_column("SDK")

    for c in creds:
        table.add_row(c.type, c.id, c.label, c.vendor, c.sdk or "-")

    console.print(Padding(table, (0, 2)))
    console.print()


@connect_app.command("test")
def connect_test(
    id_or_label: str | None = typer.Argument(None, help="Credential ID or label (omit to list all)"),
):
    """Test a provider connection.

    Examples:
        glee connect test           # List providers to choose from
        glee connect test codex
        glee connect test a1b2c3d4e5
    """
    from glee.connect import storage

    # If no ID provided, show list and prompt
    if id_or_label is None:
        creds = storage.ConnectionStorage.all()
        if not creds:
            console.print(padded(f"[{Theme.WARNING}]No providers connected. Run: glee connect[/{Theme.WARNING}]"))
            return

        from rich import box
        from rich.table import Table

        console.print(padded(f"[{Theme.WARNING}]No credential specified. Available:[/{Theme.WARNING}]"))
        console.print()

        table = Table(show_header=True, header_style=f"bold {Theme.HEADER}", box=box.ROUNDED)
        table.add_column("Label", style=Theme.PRIMARY)
        table.add_column("ID", style=Theme.MUTED)
        table.add_column("Vendor")
        table.add_column("SDK", style=Theme.ACCENT)

        for c in creds:
            table.add_row(c.label, c.id, c.vendor, c.sdk or "-")

        console.print(Padding(table, (0, 2)))
        console.print()
        console.print(padded(f"[{Theme.MUTED}]Run: glee connect test <label>[/{Theme.MUTED}]"))
        return

    cred = storage.ConnectionStorage.get(id_or_label)
    if not cred:
        console.print(padded(f"[{Theme.ERROR}]Credential not found: {id_or_label}[/{Theme.ERROR}]"))
        return

    from glee.connect import Connection

    label = f"{cred.label} ({cred.vendor})"

    console.print(padded(Text.assemble(
        ("🧪 ", "bold"),
        (f"Testing {label}", f"bold {Theme.PRIMARY}"),
    ), bottom=0))

    try:
        conn = Connection(cred)
        response = conn.chat("Say Hello")
        console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {response.content}"))
    except Exception as e:
        console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] {e}"))


@connect_app.command("remove")
def connect_remove(
    id_or_label: str = typer.Argument(..., help="Connection ID or label"),
):
    """Remove connection by ID or label.

    Examples:
        glee connect remove github-work
        glee connect remove a1b2c3d4e5
    """
    from glee.connect import storage

    cred = storage.ConnectionStorage.get(id_or_label)
    if cred:
        storage.ConnectionStorage.remove(id_or_label)
        console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Removed {cred.label} ({cred.id})"))
    else:
        console.print(padded(f"[{Theme.WARNING}]No credentials found for: {id_or_label}[/{Theme.WARNING}]"))


@connect_app.command("edit")
def connect_edit(
    id_or_label: str = typer.Argument(..., help="Connection ID or label"),
    label: str | None = typer.Option(None, "--label", "-l", help="New label"),
):
    """Edit connection properties (e.g., rename label).

    Examples:
        glee connect edit github --label github-personal
        glee connect edit a1b2c3d4e5 --label github-work
    """
    from rich.prompt import Prompt

    from glee.connect import storage

    cred = storage.ConnectionStorage.get(id_or_label)
    if not cred:
        console.print(padded(f"[{Theme.ERROR}]Credential not found: {id_or_label}[/{Theme.ERROR}]"))
        return

    console.print(padded(f"Editing [{Theme.PRIMARY}]{cred.label}[/{Theme.PRIMARY}] ({cred.id})"))

    # Prompt for new label if not provided
    if label is None:
        label = Prompt.ask(f"  [{Theme.PRIMARY}]New label[/{Theme.PRIMARY}]", default=cred.label)

    if label == cred.label:
        console.print(padded(f"[{Theme.MUTED}]No changes made[/{Theme.MUTED}]"))
        return

    # Check if new label conflicts with existing
    existing = storage.ConnectionStorage.get(label)
    if existing and existing.id != cred.id:
        console.print(padded(f"[{Theme.ERROR}]Label '{label}' already exists[/{Theme.ERROR}]"))
        return

    # Update the label
    cred.label = label
    storage.ConnectionStorage.update(cred.id, cred)
    console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Renamed to {label}"))


@connect_app.command("codex")
def connect_codex(
    label: str | None = typer.Option(None, "--label", "-l", help="Label for this credential"),
):
    """Connect Codex (OpenAI OAuth).

    Examples:
        glee connect codex
        glee connect codex --label codex-work
    """
    from rich.prompt import Prompt

    if label is None:
        label = Prompt.ask(f"  [{Theme.PRIMARY}]Label[/{Theme.PRIMARY}]")
    _do_codex_oauth(label)


@connect_app.command("copilot")
def connect_copilot(
    label: str | None = typer.Option(None, "--label", "-l", help="Label for this credential"),
):
    """Connect GitHub Copilot (OAuth).

    Examples:
        glee connect copilot
        glee connect copilot --label copilot-work
    """
    from rich.prompt import Prompt

    if label is None:
        label = Prompt.ask(f"  [{Theme.PRIMARY}]Label[/{Theme.PRIMARY}]")
    _do_copilot_oauth(label)


@connect_app.command("github")
def connect_github(
    label: str | None = typer.Option(None, "--label", "-l", help="Label for this credential (e.g., github-work)"),
):
    """Connect GitHub (Personal Access Token).

    Examples:
        glee connect github
        glee connect github --label github-work
    """
    from rich.prompt import Prompt

    from glee.connect import storage

    console.print()
    console.print(f"  [{Theme.MUTED}]GitHub Personal Access Token[/{Theme.MUTED}]")
    console.print(f"  [{Theme.MUTED}]Create at: https://github.com/settings/tokens[/{Theme.MUTED}]")
    console.print(f"  [{Theme.MUTED}]Classic token scopes: repo, read:org[/{Theme.MUTED}]")
    console.print(f"  [{Theme.MUTED}]Fine-grained: Contents (read/write), Pull requests (read/write)[/{Theme.MUTED}]")
    console.print()

    # Prompt for label if not provided
    if label is None:
        label = Prompt.ask(f"  [{Theme.PRIMARY}]Label[/{Theme.PRIMARY}]")

    token = Prompt.ask(f"  [{Theme.PRIMARY}]Token[/{Theme.PRIMARY}]", password=True)
    if token:
        # Show masked confirmation
        masked = token[:4] + "*" * (len(token) - 8) + token[-4:] if len(token) > 8 else "*" * len(token)
        console.print(f"  [{Theme.MUTED}]Token: {masked}[/{Theme.MUTED}]")
        # Check if credential with same label exists
        existing = storage.ConnectionStorage.get(label)
        credential = storage.ServiceCredential(
            id=existing.id if existing else "",
            label=label,
            vendor="github",
            key=token,
            base_url="https://api.github.com",
        )
        if existing:
            storage.ConnectionStorage.update(existing.id, credential)
            console.print(f"  [{Theme.SUCCESS}]✓ Updated {label}[/{Theme.SUCCESS}]")
        else:
            storage.ConnectionStorage.add(credential)
            console.print(f"  [{Theme.SUCCESS}]✓ Added {label}[/{Theme.SUCCESS}]")
