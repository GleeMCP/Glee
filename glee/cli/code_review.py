"""Code review and session commands."""

import json
import os
from pathlib import Path
from typing import Any, cast

import typer
from loguru import logger
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.tree import Tree

from .theme import Theme, console


def _parse_github_target(target: str) -> tuple[str, str | None, str | None, int | None]:
    """Parse GitHub target string.

    Args:
        target: Target like 'github:pr#123', 'github:owner/repo#123', 'github:branch/feature'

    Returns:
        Tuple of (type, owner, repo, number_or_branch)
        type is 'pr' or 'branch'
    """
    import re

    # github:pr#123 or github:owner/repo#123
    pr_match = re.match(r"github:(?:([^/]+)/([^#]+))?#?(\d+)", target)
    if pr_match:
        owner = pr_match.group(1)
        repo = pr_match.group(2)
        number = int(pr_match.group(3))
        return ("pr", owner, repo, number)

    # github:branch/feature
    branch_match = re.match(r"github:branch/(.+)", target)
    if branch_match:
        branch = branch_match.group(1)
        return ("branch", None, None, branch)  # type: ignore[return-value]

    raise ValueError(f"Invalid GitHub target: {target}")


def _get_repo_info() -> tuple[str, str]:
    """Get owner/repo from git remote."""
    import re
    import subprocess

    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError("Could not get git remote URL")

    url = result.stdout.strip()
    # Handle SSH: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@github\.com:([^/]+)/(.+?)(?:\.git)?$", url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)

    # Handle HTTPS: https://github.com/owner/repo.git
    https_match = re.match(r"https://github\.com/([^/]+)/(.+?)(?:\.git)?$", url)
    if https_match:
        return https_match.group(1), https_match.group(2)

    raise ValueError(f"Could not parse GitHub URL: {url}")


def _review_github(target: str, focus: str | None, dry_run: bool) -> None:
    """Handle GitHub PR/branch review."""
    import asyncio
    import platform
    import subprocess
    from datetime import datetime

    from glee.agents import registry
    from glee.dispatch import get_primary_reviewer
    from glee.github import GitHubClient, format_diff_for_review, get_token

    # Check GitHub connection
    token = get_token()
    if not token:
        console.print(f"[{Theme.ERROR}]GitHub not connected. Run: glee connect[/{Theme.ERROR}]")
        raise typer.Exit(1)

    # Parse target
    try:
        target_type, owner, repo, number_or_branch = _parse_github_target(target)
    except ValueError as e:
        console.print(f"[{Theme.ERROR}]{e}[/{Theme.ERROR}]")
        raise typer.Exit(1)

    # Get owner/repo from git remote if not specified
    if not owner or not repo:
        try:
            owner, repo = _get_repo_info()
        except ValueError as e:
            console.print(f"[{Theme.ERROR}]{e}[/{Theme.ERROR}]")
            raise typer.Exit(1)

    if target_type == "branch":
        console.print(f"[{Theme.WARNING}]Branch review not yet implemented[/{Theme.WARNING}]")
        raise typer.Exit(1)

    # PR review
    pr_number = number_or_branch
    console.print(f"[{Theme.INFO}]Fetching PR #{pr_number} from {owner}/{repo}...[/{Theme.INFO}]")

    async def do_review() -> None:
        async with GitHubClient(token) as gh:
            # Fetch PR details
            pr = await gh.get_pr(owner, repo, pr_number)  # type: ignore[arg-type]
            files = await gh.get_pr_files(owner, repo, pr_number)  # type: ignore[arg-type]

            console.print(f"[{Theme.MUTED}]PR: {pr.title}[/{Theme.MUTED}]")
            console.print(f"[{Theme.MUTED}]Files changed: {len(files)}[/{Theme.MUTED}]")
            console.print()

            # Format diff for review
            diff_content: list[str] = []
            for f in files:
                diff_content.append(format_diff_for_review(f.filename, f.patch))

            full_diff = "\n".join(diff_content)

            # Build review prompt
            focus_str = f"\nFocus on: {focus}" if focus else ""
            review_prompt = f"""Review this GitHub PR:

**PR #{pr.number}: {pr.title}**
Author: {pr.user}
Branch: {pr.head_ref} → {pr.base_ref}
{focus_str}

{full_diff}

For each issue found, output in this format:
[SEVERITY] file:line - description

Where SEVERITY is HIGH, MEDIUM, or LOW.
End with either APPROVED or NEEDS_CHANGES."""

            # Get reviewer
            reviewer_cli = get_primary_reviewer()
            agent = registry.get(reviewer_cli)
            if not agent:
                console.print(f"[{Theme.ERROR}]Reviewer {reviewer_cli} not found[/{Theme.ERROR}]")
                return

            console.print(f"[{Theme.INFO}]Running {reviewer_cli} review...[/{Theme.INFO}]")
            console.print()

            # Run review (blocking)
            result = agent.run(review_prompt, stream=True)

            if result.error:
                console.print(f"[{Theme.ERROR}]Review failed: {result.error}[/{Theme.ERROR}]")
                return

            review_output = result.output

            # Save report to file
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            report_dir = Path(".glee/reviews")
            report_dir.mkdir(parents=True, exist_ok=True)
            report_path = report_dir / f"pr-{pr_number}-{timestamp}.md"

            report_content = f"""# PR Review: #{pr.number} {pr.title}

**URL:** {pr.html_url}
**Author:** {pr.user}
**Branch:** {pr.head_ref} → {pr.base_ref}
**Reviewed:** {datetime.now().isoformat()}
**Reviewer:** {reviewer_cli}

---

{review_output}
"""
            report_path.write_text(report_content)
            console.print(f"[{Theme.MUTED}]Report saved: {report_path}[/{Theme.MUTED}]")

            # Count issues
            issues_found = review_output.upper().count("[HIGH]") + review_output.upper().count("[MEDIUM]") + review_output.upper().count("[LOW]")

            # Add to open_loop memory for warmup injection
            try:
                from glee.memory.store import Memory
                memory = Memory(Path.cwd())
                review_id = f"pr-{pr_number}-{timestamp}"
                memory.add(
                    category="open_loop",
                    content=f"PR #{pr_number} review completed - {issues_found} issues found. Use glee.code_review.get('{review_id}') to see details.",
                    metadata={
                        "type": "code_review",
                        "review_id": review_id,
                        "pr_number": pr_number,
                        "result_path": str(report_path),
                        "issues_found": issues_found,
                        "html_url": pr.html_url,
                    },
                )
                console.print(f"[{Theme.MUTED}]Added to open_loop for next session[/{Theme.MUTED}]")
            except Exception as e:
                logger.warning(f"Failed to add to open_loop: {e}")

            if dry_run:
                console.print()
                console.print(f"[{Theme.WARNING}]Dry run - not posting comments[/{Theme.WARNING}]")
            else:
                # TODO: Parse review output and post inline comments
                console.print()
                console.print(f"[{Theme.MUTED}]Comment posting not yet implemented[/{Theme.MUTED}]")

            # Send notification
            def notify(title: str, message: str) -> None:
                if platform.system() == "Darwin":
                    script = f'display notification "{message}" with title "{title}" sound name "Funk"'
                    subprocess.run(["osascript", "-e", script], capture_output=True)
                elif platform.system() == "Linux":
                    subprocess.run(["notify-send", title, message], capture_output=True)

            notify("✨ Glee", f"✅ PR #{pr_number} Reviewed\n📋 {issues_found} issues found")

    asyncio.run(do_review())


def code_review(
    app: typer.Typer,
    target: str | None,
    focus: str | None,
    second_opinion: bool,
    dry_run: bool,
) -> None:
    """Run code review with configured reviewer.

    Supports local targets (files, directories, git changes) and remote targets (GitHub PRs).

    Examples:
        glee code-review .                    # Review current directory
        glee code-review git:changes          # Review uncommitted changes
        glee code-review github:pr#123        # Review PR and post comments
        glee code-review github:pr#123 --dry-run  # Preview without posting
    """
    review_target = target or "."

    # Check if this is a GitHub target
    if review_target.startswith("github:"):
        _review_github(review_target, focus, dry_run)
        return

    # Local review (existing logic)
    from glee.agents import registry
    from glee.agents.base import AgentResult
    from glee.config import get_project_config
    from glee.dispatch import get_primary_reviewer, get_secondary_reviewer

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)
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

    # Review plan panel
    plan_content = Text()
    plan_content.append("Target: ", style=Theme.MUTED)
    plan_content.append(f"{review_target}\n", style=Theme.PRIMARY)
    plan_content.append("Reviewers: ", style=Theme.MUTED)
    plan_content.append(f"{', '.join(reviewers_to_run)}", style=Theme.ACCENT)
    if focus_list:
        plan_content.append("\nFocus: ", style=Theme.MUTED)
        plan_content.append(f"{', '.join(focus_list)}", style=Theme.INFO)

    console.print(Panel(plan_content, title=f"[{Theme.HEADER}]📋 Review Plan[/{Theme.HEADER}]", border_style=Theme.PRIMARY))
    console.print()

    logger.info(f"Starting review with: {', '.join(reviewers_to_run)}")
    console.print(f"[{Theme.INFO}]Running review...[/{Theme.INFO}]")
    console.print()

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
    console.print(Rule(f"[{Theme.HEADER}]Review Summary[/{Theme.HEADER}]", style=Theme.MUTED))
    console.print()

    all_approved = True
    summary_tree = Tree(f"[{Theme.INFO}]📊 Results[/{Theme.INFO}]")
    for reviewer_name, data in results.items():
        if data["error"]:
            summary_tree.add(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] {reviewer_name}: [{Theme.ERROR}]{data['error']}[/{Theme.ERROR}]")
            all_approved = False
        elif data["result"]:
            result = data["result"]
            if result.error:
                summary_tree.add(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] {reviewer_name}: [{Theme.ERROR}]Error[/{Theme.ERROR}]")
                all_approved = False
            else:
                if "NEEDS_CHANGES" in result.output.upper():
                    summary_tree.add(f"[{Theme.WARNING}]![/{Theme.WARNING}] {reviewer_name}: [{Theme.WARNING}]Changes requested[/{Theme.WARNING}]")
                    all_approved = False
                else:
                    summary_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {reviewer_name}: [{Theme.SUCCESS}]Approved[/{Theme.SUCCESS}]")

    console.print(summary_tree)
    console.print()

    if all_approved:
        logger.info("Review completed: approved")
        console.print(Panel(
            f"[{Theme.SUCCESS}]✓ All reviewers approved[/{Theme.SUCCESS}]",
            border_style=Theme.SUCCESS,
            padding=(0, 2)
        ))
    else:
        logger.warning("Review completed: changes requested")
        console.print(Panel(
            f"[{Theme.WARNING}]⚠ Changes requested[/{Theme.WARNING}]",
            border_style=Theme.WARNING,
            padding=(0, 2)
        ))


def warmup_session() -> None:
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


def summarize_session(
    from_source: str,
    session_id: str | None,
) -> None:
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

        def find_project_root(start: Path) -> Path | None:
            for candidate in [start] + list(start.parents):
                if (candidate / ".glee" / "config.yml").exists():
                    return candidate
            return None

        project_hint = conversation.get("project_path") or os.getcwd()
        project_path = Path(project_hint).expanduser()
        if project_path.is_file():
            project_path = project_path.parent
        project_root = find_project_root(project_path.resolve())
        if not project_root or not get_project_config(str(project_root)):
            log(f"No project config found for {project_path}")
            console.print("[red]No project config found. Run 'glee init' in the project.[/red]")
            return

        if log_file is None or (project_root / ".glee" / "stream_logs") != log_file.parent:
            log_dir = project_root / ".glee" / "stream_logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"summarize-session-{datetime.now().strftime('%Y%m%d')}.log"

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
                str(project_root),
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
