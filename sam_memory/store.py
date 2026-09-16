"""
SQLite-backed persistent Structured Entity Store for Sam.
Supports CRUD operations, importance scoring, keyword search, and explicit forgetting.
"""
import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from sam_core.logger import get_logger
from sam_memory.models import MemoryEntry, MemorySearchResult

logger = get_logger("memory.store")


class SQLiteMemoryStore:
    """
    Tier 2 persistent entity store backed by SQLite.
    Guarantees thread-safe asynchronous queries and migrations.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None or db_path == ":memory:":
            self.db_path = ":memory:"
            self._in_memory_conn: sqlite3.Connection | None = sqlite3.connect(":memory:", check_same_thread=False)
            self._in_memory_conn.row_factory = sqlite3.Row
        else:
            p = Path(db_path).expanduser().resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(p)
            self._in_memory_conn = None

        self._lock = asyncio.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._in_memory_conn is not None:
            return self._in_memory_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _close_connection(self, conn: sqlite3.Connection) -> None:
        if self._in_memory_conn is None:
            conn.close()

    def _init_db(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        importance INTEGER NOT NULL,
                        tags TEXT NOT NULL,
                        metadata TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_cat ON memories(category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_key ON memories(key)")
        finally:
            self._close_connection(conn)

    async def add_memory(self, entry: MemoryEntry) -> MemoryEntry:
        """Store or replace an existing memory entry."""
        async with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO memories
                        (id, category, key, value, importance, tags, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entry.id,
                            entry.category.lower(),
                            entry.key.lower(),
                            entry.value,
                            entry.importance,
                            json.dumps(entry.tags),
                            json.dumps(entry.metadata),
                            entry.created_at.isoformat(),
                            entry.updated_at.isoformat(),
                        ),
                    )
                logger.debug(f"Stored memory: {entry.category}/{entry.key}")
                return entry
            finally:
                self._close_connection(conn)

    async def get_by_id(self, memory_id: str) -> MemoryEntry | None:
        """Fetch memory by its unique UUID."""
        async with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_entry(row)
            finally:
                self._close_connection(conn)

    async def get_by_key(self, key: str, category: str | None = None) -> MemoryEntry | None:
        """Fetch memory by exact key and optional category."""
        async with self._lock:
            conn = self._get_connection()
            try:
                if category:
                    cur = conn.execute(
                        "SELECT * FROM memories WHERE key = ? AND category = ? LIMIT 1",
                        (key.lower(), category.lower()),
                    )
                else:
                    cur = conn.execute("SELECT * FROM memories WHERE key = ? LIMIT 1", (key.lower(),))
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_entry(row)
            finally:
                self._close_connection(conn)

    async def search_memories(
        self, query: str, category: str | None = None, limit: int = 10
    ) -> list[MemorySearchResult]:
        """Search memories using keyword matching and relevance ranking."""
        async with self._lock:
            conn = self._get_connection()
            try:
                pattern = f"%{query.lower()}%"
                if category:
                    cur = conn.execute(
                        """
                        SELECT * FROM memories
                        WHERE category = ? AND (key LIKE ? OR value LIKE ? OR tags LIKE ?)
                        ORDER BY importance DESC, updated_at DESC LIMIT ?
                        """,
                        (category.lower(), pattern, pattern, pattern, limit),
                    )
                else:
                    cur = conn.execute(
                        """
                        SELECT * FROM memories
                        WHERE key LIKE ? OR value LIKE ? OR tags LIKE ?
                        ORDER BY importance DESC, updated_at DESC LIMIT ?
                        """,
                        (pattern, pattern, pattern, limit),
                    )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    entry = self._row_to_entry(row)
                    # Simple heuristic score combining importance and match
                    score = min(1.0, 0.5 + (entry.importance * 0.1))
                    results.append(MemorySearchResult(entry=entry, score=score))
                return results
            finally:
                self._close_connection(conn)

    async def list_memories(self, category: str | None = None, limit: int = 50) -> list[MemoryEntry]:
        """List stored memories ordered by importance and update time."""
        async with self._lock:
            conn = self._get_connection()
            try:
                if category:
                    cur = conn.execute(
                        "SELECT * FROM memories WHERE category = ? ORDER BY importance DESC, updated_at DESC LIMIT ?",
                        (category.lower(), limit),
                    )
                else:
                    cur = conn.execute(
                        "SELECT * FROM memories ORDER BY importance DESC, updated_at DESC LIMIT ?",
                        (limit,),
                    )
                return [self._row_to_entry(r) for r in cur.fetchall()]
            finally:
                self._close_connection(conn)

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a single memory by ID."""
        async with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                    return cur.rowcount > 0
            finally:
                self._close_connection(conn)

    async def forget(self, query: str, category: str | None = None) -> int:
        """
        Delete all memories matching a search query or key.
        Returns count of memories deleted.
        """
        async with self._lock:
            conn = self._get_connection()
            try:
                pattern = f"%{query.lower()}%"
                with conn:
                    if category:
                        cur = conn.execute(
                            "DELETE FROM memories WHERE category = ? AND (key LIKE ? OR value LIKE ?)",
                            (category.lower(), pattern, pattern),
                        )
                    else:
                        cur = conn.execute(
                            "DELETE FROM memories WHERE key LIKE ? OR value LIKE ?",
                            (pattern, pattern),
                        )
                    deleted = cur.rowcount
                    logger.info(f"Explicit forget for query '{query}': deleted {deleted} items")
                    return deleted
            finally:
                self._close_connection(conn)

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            category=row["category"],
            key=row["key"],
            value=row["value"],
            importance=row["importance"],
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
