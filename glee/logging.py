"""Logging configuration for Glee with SQLite storage."""


import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4
from glee.db.sqlite import close_thread_connections
from loguru import logger

from glee.db.sqlite import get_sqlite_connection, init_sqlite

if TYPE_CHECKING:
    from loguru import Logger

# Patterns for sensitive content redaction
_SENSITIVE_PATTERNS = [
    # API keys (various formats)
    (re.compile(r"(sk-[a-zA-Z0-9]{20,})", re.IGNORECASE), r"[REDACTED_API_KEY]"),
    (re.compile(r"(api[_-]?key\s*[=:]\s*)['\"]?([a-zA-Z0-9_-]{20,})['\"]?", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(secret[_-]?key\s*[=:]\s*)['\"]?([a-zA-Z0-9_-]{20,})['\"]?", re.IGNORECASE), r"\1[REDACTED]"),
    # Bearer tokens
    (re.compile(r"(Bearer\s+)([a-zA-Z0-9._-]{20,})", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    # Passwords in URLs or config
    (re.compile(r"(password\s*[=:]\s*)['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(passwd\s*[=:]\s*)['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(pwd\s*[=:]\s*)['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE), r"\1[REDACTED]"),
    # Connection strings with passwords
    (re.compile(r"(:\/\/[^:]+:)([^@]+)(@)", re.IGNORECASE), r"\1[REDACTED]\3"),
    # AWS credentials
    (re.compile(r"(AKIA[0-9A-Z]{16})", re.IGNORECASE), r"[REDACTED_AWS_KEY]"),
    (re.compile(r"(aws_secret_access_key\s*[=:]\s*)['\"]?([a-zA-Z0-9/+=]{40})['\"]?", re.IGNORECASE), r"\1[REDACTED]"),
    # GitHub tokens
    (re.compile(r"(ghp_[a-zA-Z0-9]{36})", re.IGNORECASE), r"[REDACTED_GH_TOKEN]"),
    (re.compile(r"(gho_[a-zA-Z0-9]{36})", re.IGNORECASE), r"[REDACTED_GH_TOKEN]"),
    # Generic secrets
    (re.compile(r"(token\s*[=:]\s*)['\"]?([a-zA-Z0-9_-]{20,})['\"]?", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(secret\s*[=:]\s*)['\"]?([a-zA-Z0-9_-]{16,})['\"]?", re.IGNORECASE), r"\1[REDACTED]"),
]

# Default logging settings
DEFAULT_LOG_SETTINGS = {
    "enabled": True,
    "redact_sensitive": True,
    "max_agent_logs": 50000,  # Max agent log entries before rotation
    "max_general_logs": 100000,  # Max general log entries before rotation
}


def _get_log_settings(project_path: Path) -> dict[str, Any]:
    """Get logging settings from project config.

    Args:
        project_path: Project path containing .glee directory.

    Returns:
        Logging settings dict with defaults applied.
    """
    settings = DEFAULT_LOG_SETTINGS.copy()

    config_path = project_path / ".glee" / "config.yml"
    if config_path.exists():
        import yaml

        with open(config_path) as f:
            config: dict[str, Any] = yaml.safe_load(f) or {}
            log_config: dict[str, Any] = config.get("logging", {})
            settings.update(log_config)

    return settings


def redact_sensitive(text: str | None) -> str | None:
    """Redact sensitive content from text.

    Args:
        text: Text that may contain sensitive information.

    Returns:
        Text with sensitive patterns redacted, or None if input is None.
    """
    if text is None:
        return None

    result = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


class AgentRunLogger:
    """Logger for agent invocations - stores prompts, outputs, raw responses.

    Supports:
    - Opt-out via config (logging.enabled = false)
    - Sensitive content redaction (logging.redact_sensitive = true)
    - Log rotation (logging.max_agent_logs = N)
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self._settings = _get_log_settings(project_path)
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get thread-local SQLite connection."""
        # Always get thread-local connection to avoid cross-thread issues
        return get_sqlite_connection(self.project_path)

    @property
    def enabled(self) -> bool:
        """Check if agent logging is enabled."""
        return self._settings.get("enabled", True)

    def _init_db(self) -> None:
        """Initialize the agent_logs table using centralized schema."""
        init_sqlite(self.conn, tables=["agent_logs"])

    def _rotate_logs(self) -> None:
        """Delete oldest logs if over the max limit."""
        max_logs = self._settings.get("max_agent_logs", 1000)

        try:
            # Count current logs
            result = self.conn.execute(
                "SELECT COUNT(*) FROM agent_logs"
            ).fetchone()
            count = result[0] if result else 0

            if count > max_logs:
                # Delete oldest entries to get back under limit
                delete_count = count - max_logs
                self.conn.execute(
                    """
                    DELETE FROM agent_logs WHERE id IN (
                        SELECT id FROM agent_logs
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )
                    """,
                    [delete_count],
                )
                self.conn.commit()
        except sqlite3.OperationalError:
            pass  # Table might not exist yet

    def log(
        self,
        agent: str,
        prompt: str,
        output: str | None = None,
        raw: str | None = None,
        error: str | None = None,
        exit_code: int = 0,
        duration_ms: int | None = None,
    ) -> str | None:
        """Log an agent run.

        Args:
            agent: Agent name (claude, codex, gemini).
            prompt: The prompt sent to the agent.
            output: Parsed/final output.
            raw: Raw output from subprocess (for debugging).
            error: Error message if failed.
            exit_code: Process exit code.
            duration_ms: Execution time in milliseconds.

        Returns:
            The log ID, or None if logging is disabled.
        """
        # Check if logging is enabled
        if not self.enabled:
            return None

        # Apply redaction if enabled
        if self._settings.get("redact_sensitive", True):
            prompt = redact_sensitive(prompt) or prompt
            output = redact_sensitive(output)
            raw = redact_sensitive(raw)
            error = redact_sensitive(error)

        log_id = str(uuid4())[:8]
        self.conn.execute(
            """
            INSERT INTO agent_logs
            (id, timestamp, agent, prompt, output, raw, error, exit_code, duration_ms, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                log_id,
                datetime.now().isoformat(),
                agent,
                prompt,
                output,
                raw,
                error,
                exit_code,
                duration_ms,
                1 if exit_code == 0 and error is None else 0,
            ],
        )
        self.conn.commit()

        # Rotate logs if needed
        self._rotate_logs()

        return log_id

    def close(self) -> None:
        """Close thread-local database connections."""
        close_thread_connections()


_agent_logger: AgentRunLogger | None = None


def get_agent_logger(project_path: Path | None = None) -> AgentRunLogger | None:
    """Get or create the agent run logger.

    Args:
        project_path: Project path for .glee directory.

    Returns:
        AgentRunLogger instance or None if no project path.
    """
    global _agent_logger

    if _agent_logger is not None:
        return _agent_logger

    if project_path:
        _agent_logger = AgentRunLogger(project_path)
        return _agent_logger

    return None


def query_agent_logs(
    project_path: Path,
    agent: str | None = None,
    success_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query agent logs from SQLite.

    Args:
        project_path: Project path containing .glee directory.
        agent: Filter by agent name.
        success_only: Only return successful runs.
        limit: Max number of results.

    Returns:
        List of agent log records.
    """
    conn = get_sqlite_connection(project_path)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM agent_logs WHERE 1=1"
    params: list[Any] = []

    if agent:
        query += " AND agent = ?"
        params.append(agent)

    if success_only:
        query += " AND success = 1"

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    try:
        cursor = conn.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        results = []
    finally:
        conn.close()

    return results


def get_agent_log(project_path: Path, log_id: str) -> dict[str, Any] | None:
    """Get a specific agent log entry.

    Args:
        project_path: Project path containing .glee directory.
        log_id: The log ID to fetch.

    Returns:
        Log record or None if not found.
    """
    conn = get_sqlite_connection(project_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute("SELECT * FROM agent_logs WHERE id = ?", [log_id])
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    finally:
        conn.close()

    return dict(row) if row else None


class SQLiteLogHandler:
    """Custom log handler that stores logs in SQLite.

    Supports log rotation via logging.max_general_logs config setting.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self._settings = _get_log_settings(project_path)
        self._write_count = 0  # Track writes to avoid checking rotation on every write
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get thread-local SQLite connection."""
        # Always get thread-local connection to avoid cross-thread issues
        return get_sqlite_connection(self.project_path)

    def _init_db(self) -> None:
        """Initialize the logs table using centralized schema."""
        init_sqlite(self.conn, tables=["logs"])

    def _rotate_logs(self) -> None:
        """Delete oldest logs if over the max limit."""
        max_logs = self._settings.get("max_general_logs", 5000)

        try:
            result = self.conn.execute("SELECT COUNT(*) FROM logs").fetchone()
            count = result[0] if result else 0

            if count > max_logs:
                delete_count = count - max_logs
                self.conn.execute(
                    """
                    DELETE FROM logs WHERE rowid IN (
                        SELECT rowid FROM logs
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )
                    """,
                    [delete_count],
                )
                self.conn.commit()
        except sqlite3.OperationalError:
            pass

    def write(self, message: Any) -> None:
        """Write a log record to SQLite."""
        record = message.record

        self.conn.execute(
            """
            INSERT INTO logs (timestamp, level, message)
            VALUES (?, ?, ?)
            """,
            [
                record["time"].isoformat(),
                record["level"].name,
                record["message"],
            ],
        )
        self.conn.commit()

        # Check rotation every 100 writes to avoid overhead
        self._write_count += 1
        if self._write_count >= 100:
            self._rotate_logs()
            self._write_count = 0

    def close(self) -> None:
        """Close thread-local database connections."""
        from glee.db.sqlite import close_thread_connections
        close_thread_connections()


_log_handler: SQLiteLogHandler | None = None


def setup_logging(project_path: Path | None = None) -> "Logger":
    """Configure loguru logging with SQLite storage.

    Args:
        project_path: Project path for .glee directory. If None, only console logging.

    Returns:
        Configured logger instance.
    """
    global _log_handler

    logger.remove()

    # Console logging
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG",
    )

    # SQLite logging if project path provided
    if project_path:
        _log_handler = SQLiteLogHandler(project_path)
        logger.add(_log_handler.write, level="DEBUG")

    return logger


def query_logs(
    project_path: Path,
    level: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query logs from SQLite.

    Args:
        project_path: Project path containing .glee directory.
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR).
        since: Filter logs after this time.
        until: Filter logs before this time.
        search: Search in message text.
        limit: Max number of results.

    Returns:
        List of log records.
    """
    conn = get_sqlite_connection(project_path)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM logs WHERE 1=1"
    params: list[Any] = []

    if level:
        query += " AND level = ?"
        params.append(level.upper())

    if since:
        query += " AND timestamp >= ?"
        params.append(since.isoformat())

    if until:
        query += " AND timestamp <= ?"
        params.append(until.isoformat())

    if search:
        query += " AND message LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    try:
        cursor = conn.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        results = []
    finally:
        conn.close()

    return results


def get_log_stats(project_path: Path) -> dict[str, Any]:
    """Get log statistics.

    Args:
        project_path: Project path containing .glee directory.

    Returns:
        Dictionary with log stats.
    """
    conn = get_sqlite_connection(project_path)

    try:
        # Total count
        total = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]

        # Count by level
        cursor = conn.execute(
            "SELECT level, COUNT(*) as count FROM logs GROUP BY level"
        )
        by_level = {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        total = 0
        by_level = {}
    finally:
        conn.close()

    return {"total": total, "by_level": by_level}
