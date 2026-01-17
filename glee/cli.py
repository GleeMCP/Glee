"""Glee CLI - Stage Manager for Your AI Orchestra.

This module re-exports the CLI from glee.cli package for backwards compatibility.
"""

from glee.cli import app, main

__all__ = ["app", "main"]

if __name__ == "__main__":
    main()
