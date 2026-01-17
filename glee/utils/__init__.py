"""Utility functions for Glee."""

import secrets
import string


def generate_id(length: int = 10) -> str:
    """Generate a random alphanumeric ID."""
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))
