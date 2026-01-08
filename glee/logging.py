"""Logging configuration for Glee."""

import sys

from loguru import logger


def setup_logging() -> logger:
    """Configure loguru logging."""
    logger.remove()

    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG",
    )

    return logger
