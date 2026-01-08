from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

if TYPE_CHECKING:
    from loguru import Logger, Message


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg2://glee:glee@localhost:5432/glee"
        )
        _engine = create_engine(database_url, poolclass=QueuePool, pool_size=5)
    return _engine


def db_sink(message: Message) -> None:
    """Loguru sink that writes to PostgreSQL."""
    record = message.record

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO logs (timestamp, level, message, module, function, line, extra)
                    VALUES (:timestamp, :level, :message, :module, :function, :line, :extra)
                """),
                {
                    "timestamp": record["time"].isoformat(),
                    "level": record["level"].name,
                    "message": record["message"],
                    "module": record["module"],
                    "function": record["function"],
                    "line": record["line"],
                    "extra": dict(record["extra"]) if record["extra"] else None,
                }
            )
            conn.commit()
    except Exception:
        # Don't let logging errors crash the app
        pass


def setup_logging(enable_db: bool = True) -> Logger:
    """Configure loguru logging."""
    # Remove default handler
    logger.remove()

    # Console output
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
    )

    # Database output
    if enable_db:
        logger.add(db_sink, level="INFO")

    return logger
