"""Diff parsing utilities for GitHub PR reviews."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DiffHunk:
    """A single hunk from a unified diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[str]


@dataclass
class DiffLine:
    """A single line from a diff with context."""

    line_type: str  # "+", "-", " " (context)
    content: str
    old_line: int | None  # Line number in old file
    new_line: int | None  # Line number in new file


def parse_patch(patch: str) -> list[DiffHunk]:
    """Parse a unified diff patch into hunks.

    Args:
        patch: Unified diff patch string.

    Returns:
        List of diff hunks.
    """
    if not patch:
        return []

    hunks: list[DiffHunk] = []
    hunk_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")

    current_hunk: DiffHunk | None = None
    lines_buffer: list[str] = []

    for line in patch.split("\n"):
        match = hunk_pattern.match(line)
        if match:
            # Save previous hunk
            if current_hunk:
                current_hunk.lines = lines_buffer
                hunks.append(current_hunk)

            # Start new hunk
            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) else 1
            header = match.group(5).strip()

            current_hunk = DiffHunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                header=header,
                lines=[],
            )
            lines_buffer = []
        elif current_hunk is not None:
            lines_buffer.append(line)

    # Save last hunk
    if current_hunk:
        current_hunk.lines = lines_buffer
        hunks.append(current_hunk)

    return hunks


def parse_hunk_lines(hunk: DiffHunk) -> list[DiffLine]:
    """Parse hunk lines with line numbers.

    Args:
        hunk: A diff hunk.

    Returns:
        List of diff lines with line numbers.
    """
    result: list[DiffLine] = []
    old_line = hunk.old_start
    new_line = hunk.new_start

    for line in hunk.lines:
        if not line:
            continue

        line_type = line[0] if line else " "
        content = line[1:] if len(line) > 1 else ""

        if line_type == "+":
            result.append(DiffLine(
                line_type="+",
                content=content,
                old_line=None,
                new_line=new_line,
            ))
            new_line += 1
        elif line_type == "-":
            result.append(DiffLine(
                line_type="-",
                content=content,
                old_line=old_line,
                new_line=None,
            ))
            old_line += 1
        else:
            # Context line
            result.append(DiffLine(
                line_type=" ",
                content=content,
                old_line=old_line,
                new_line=new_line,
            ))
            old_line += 1
            new_line += 1

    return result


def get_added_lines(patch: str) -> list[tuple[int, str]]:
    """Get all added lines from a patch.

    Args:
        patch: Unified diff patch string.

    Returns:
        List of (line_number, content) tuples for added lines.
    """
    result: list[tuple[int, str]] = []

    for hunk in parse_patch(patch):
        for diff_line in parse_hunk_lines(hunk):
            if diff_line.line_type == "+" and diff_line.new_line is not None:
                result.append((diff_line.new_line, diff_line.content))

    return result


def format_diff_for_review(filename: str, patch: str | None) -> str:
    """Format a file's diff for AI review.

    Args:
        filename: Name of the file.
        patch: Unified diff patch string.

    Returns:
        Formatted string for AI review.
    """
    if not patch:
        return f"## {filename}\n(binary file or no changes)\n"

    lines = [f"## {filename}\n```diff"]
    lines.append(patch)
    lines.append("```\n")

    return "\n".join(lines)
