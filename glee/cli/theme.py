"""Theme and utilities for Glee CLI."""

from rich.console import Console, RenderableType
from rich.padding import Padding


class Theme:
    """Consistent color theme for CLI output."""

    PRIMARY = "cyan"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    MUTED = "dim"
    ACCENT = "magenta"
    INFO = "blue"
    HEADER = "bold cyan"
    TITLE = "bold white"


# Layout constants
LEFT_PAD = 2  # Left margin for all output

# Shared console instance
console = Console()


def padded(renderable: RenderableType, top: int = 1, bottom: int = 1) -> Padding:
    """Wrap a renderable with consistent padding (top, right, bottom, left)."""
    return Padding(renderable, (top, 0, bottom, LEFT_PAD))


def get_version() -> str:
    """Get the package version."""
    from importlib.metadata import version

    return version("glee")
