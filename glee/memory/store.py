"""Memory store combining LanceDB (vector) and DuckDB (SQL)."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import lancedb
from fastembed import TextEmbedding
from pydantic import BaseModel

from glee.db.duckdb import init_duckdb

# Validation patterns to prevent LanceDB filter injection
_CATEGORY_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
_MEMORY_ID_PATTERN = re.compile(r"^[a-f0-9]{8}$")

# Singleton embedding model (expensive to load, share across Memory instances)
_shared_embedder: TextEmbedding | None = None


def _get_embedder() -> TextEmbedding:
    """Get or create the shared embedding model singleton."""
    global _shared_embedder
    if _shared_embedder is None:
        _shared_embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _shared_embedder


def _validate_category(category: str) -> str:
    """Validate category to prevent filter injection.

    Args:
        category: Category string to validate

    Returns:
        The validated category

    Raises:
        ValueError: If category contains invalid characters
    """
    if not _CATEGORY_PATTERN.match(category):
        raise ValueError(
            f"Invalid category '{category}': must contain only alphanumeric, "
            "underscore, or hyphen characters"
        )
    return category


def _validate_memory_id(memory_id: str) -> str:
    """Validate memory ID to prevent filter injection.

    Args:
        memory_id: Memory ID to validate

    Returns:
        The validated memory ID

    Raises:
        ValueError: If memory ID is not a valid 8-char hex string
    """
    if not _MEMORY_ID_PATTERN.match(memory_id):
        raise ValueError(
            f"Invalid memory_id '{memory_id}': must be an 8-character hex string"
        )
    return memory_id


class MemoryEntry(BaseModel):
    """A memory entry."""

    id: str
    category: str  # architecture, convention, review, decision
    content: str
    metadata: dict[str, Any] = {}
    created_at: datetime = datetime.now()


class Memory:
    """Memory store for project context."""

    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path)
        self.glee_dir = self.project_path / ".glee"
        self.lance_path = self.glee_dir / "memory.lance"
        self.duck_path = self.glee_dir / "memory.duckdb"

        # Initialize databases
        self._lance_db: lancedb.DBConnection | None = None
        self._duck_conn: duckdb.DuckDBPyConnection | None = None

    @property
    def embedder(self) -> TextEmbedding:
        """Get shared embedding model singleton."""
        return _get_embedder()

    @property
    def lance(self) -> lancedb.DBConnection:
        """Get LanceDB connection."""
        if self._lance_db is None:
            self._lance_db = lancedb.connect(str(self.lance_path))
        return self._lance_db

    @property
    def duck(self) -> duckdb.DuckDBPyConnection:
        """Get DuckDB connection."""
        if self._duck_conn is None:
            self._duck_conn = duckdb.connect(str(self.duck_path))
            self._init_duck_schema()
        return self._duck_conn

    def _init_duck_schema(self) -> None:
        """Initialize DuckDB schema using centralized definitions."""
        if self._duck_conn is not None:
            init_duckdb(self._duck_conn, tables=["memories", "stats"])

    def _embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        embeddings = list(self.embedder.embed([text]))
        return embeddings[0].tolist()

    def add(
        self,
        category: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a memory entry.

        Args:
            category: Type of memory (architecture, convention, review, decision)
            content: The content to remember
            metadata: Optional metadata

        Returns:
            The memory ID
        """
        import uuid

        memory_id = str(uuid.uuid4())[:8]
        now = datetime.now()

        # Store in DuckDB (structured)
        self.duck.execute(
            """
            INSERT INTO memories (id, category, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [memory_id, category, content, json.dumps(metadata or {}), now],
        )

        # Store in LanceDB (vector)
        vector = self._embed(content)
        table_name = "memories"

        data = [{
            "id": memory_id,
            "category": category,
            "content": content,
            "vector": vector,
        }]

        try:
            table = self.lance.open_table(table_name)
            table.add(data)  # type: ignore[reportUnknownMemberType]
        except Exception:
            # Table doesn't exist, create it
            self.lance.create_table(table_name, data)  # type: ignore[reportUnknownMemberType]

        return memory_id

    def search(
        self,
        query: str,
        category: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search memories by semantic similarity.

        Args:
            query: Search query
            category: Optional category filter
            limit: Max results

        Returns:
            List of matching memories
        """
        try:
            table = self.lance.open_table("memories")
        except Exception:
            return []

        vector = self._embed(query)
        results = table.search(vector).limit(limit)  # type: ignore[reportUnknownMemberType]

        if category:
            validated_category = _validate_category(category)
            results = results.where(f"category = '{validated_category}'")

        return list(results.to_list())  # type: ignore[reportUnknownMemberType]

    def get_by_category(self, category: str) -> list[dict[str, Any]]:
        """Get all memories in a category."""
        result = self.duck.execute(
            "SELECT * FROM memories WHERE category = ? ORDER BY created_at DESC",
            [category],
        ).fetchall()

        columns = ["id", "category", "content", "metadata", "created_at"]
        return [dict(zip(columns, row)) for row in result]

    def get_categories(self) -> list[str]:
        """Get all unique categories."""
        result = self.duck.execute(
            "SELECT DISTINCT category FROM memories ORDER BY category"
        ).fetchall()
        return [row[0] for row in result]

    def get_context(self, max_per_category: int = 5) -> str:
        """Get formatted context for hook injection.

        Dynamically includes all categories found in memory.

        Args:
            max_per_category: Maximum entries to show per category (default: 5)
        """
        lines: list[str] = []

        # Get all categories dynamically
        categories = self.get_categories()

        for category in categories:
            memories = self.get_by_category(category)
            if memories:
                # Format category name: "my-category" -> "My Category"
                title = category.replace("-", " ").replace("_", " ").title()
                lines.append(f"### {title}")
                for m in memories[:max_per_category]:
                    lines.append(f"- {m['content']}")
                lines.append("")

        return "\n".join(lines)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry by ID.

        Args:
            memory_id: The memory ID to delete

        Returns:
            True if deleted, False if not found
        """
        # Check if exists in DuckDB
        result = self.duck.execute(
            "SELECT id FROM memories WHERE id = ?", [memory_id]
        ).fetchone()

        if not result:
            return False

        # Delete from DuckDB
        self.duck.execute("DELETE FROM memories WHERE id = ?", [memory_id])

        # Delete from LanceDB (validate to prevent injection)
        try:
            validated_id = _validate_memory_id(memory_id)
            table = self.lance.open_table("memories")
            table.delete(f"id = '{validated_id}'")  # type: ignore[reportUnknownMemberType]
        except ValueError:
            pass  # Invalid ID format, skip LanceDB deletion
        except Exception:
            pass  # Table might not exist

        return True

    def clear(self, category: str | None = None) -> int:
        """Clear memories.

        Args:
            category: If specified, only clear this category. Otherwise clear all.

        Returns:
            Number of memories deleted
        """
        if category:
            # Count first
            result = self.duck.execute(
                "SELECT COUNT(*) FROM memories WHERE category = ?", [category]
            ).fetchone()
            count = result[0] if result else 0

            # Delete from DuckDB
            self.duck.execute("DELETE FROM memories WHERE category = ?", [category])

            # Delete from LanceDB (validate to prevent injection)
            try:
                validated_category = _validate_category(category)
                table = self.lance.open_table("memories")
                table.delete(f"category = '{validated_category}'")  # type: ignore[reportUnknownMemberType]
            except ValueError:
                pass  # Invalid category format, skip LanceDB deletion
            except Exception:
                pass  # Table might not exist
        else:
            # Count first
            result = self.duck.execute("SELECT COUNT(*) FROM memories").fetchone()
            count = result[0] if result else 0

            # Delete all from DuckDB
            self.duck.execute("DELETE FROM memories")

            # Drop and recreate LanceDB table
            try:
                self.lance.drop_table("memories")
            except Exception:
                pass

        return count

    def get_latest(self, limit: int = 1) -> list[dict[str, Any]]:
        """Get the most recent memories across all categories.

        Args:
            limit: Number of recent memories to return (default: 1)

        Returns:
            List of most recent memory entries
        """
        result = self.duck.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
            [limit],
        ).fetchall()

        columns = ["id", "category", "content", "metadata", "created_at"]
        return [dict(zip(columns, row)) for row in result]

    def stats(self) -> dict[str, Any]:
        """Get memory statistics.

        Returns:
            Dictionary with stats: total, by_category, oldest, newest
        """
        stats: dict[str, Any] = {
            "total": 0,
            "by_category": {},
            "oldest": None,
            "newest": None,
        }

        # Total count
        result = self.duck.execute("SELECT COUNT(*) FROM memories").fetchone()
        stats["total"] = result[0] if result else 0

        if stats["total"] == 0:
            return stats

        # Count by category
        rows = self.duck.execute(
            "SELECT category, COUNT(*) FROM memories GROUP BY category"
        ).fetchall()
        stats["by_category"] = {row[0]: row[1] for row in rows}

        # Oldest and newest
        oldest = self.duck.execute(
            "SELECT created_at FROM memories ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        if oldest:
            stats["oldest"] = oldest[0]

        newest = self.duck.execute(
            "SELECT created_at FROM memories ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if newest:
            stats["newest"] = newest[0]

        return stats

    def close(self) -> None:
        """Close database connections."""
        if self._duck_conn:
            self._duck_conn.close()
            self._duck_conn = None
        self._lance_db = None
