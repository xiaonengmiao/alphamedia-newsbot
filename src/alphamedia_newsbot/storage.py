from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .models import Goal, NewsItem, normalize_text


class SQLiteStorage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    topic_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_run_at TEXT,
                    UNIQUE(chat_id, topic_key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_items (
                    item_hash TEXT NOT NULL,
                    topic_key TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    PRIMARY KEY(item_hash, topic_key)
                )
                """
            )

    @staticmethod
    def topic_key(topic: str) -> str:
        return normalize_text(topic)

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def upsert_goal(self, chat_id: int, topic: str) -> Goal:
        topic = topic.strip()
        if not topic:
            raise ValueError("topic cannot be empty")

        now = self._now()
        key = self.topic_key(topic)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO goals(chat_id, topic, topic_key, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, topic_key) DO UPDATE SET topic = excluded.topic
                """,
                (chat_id, topic, key, now),
            )
            row = conn.execute(
                "SELECT * FROM goals WHERE chat_id = ? AND topic_key = ?",
                (chat_id, key),
            ).fetchone()
        return self._goal_from_row(row)

    def list_goals(self, chat_id: int | None = None) -> list[Goal]:
        query = "SELECT * FROM goals"
        params: tuple[int, ...] = ()
        if chat_id is not None:
            query += " WHERE chat_id = ?"
            params = (chat_id,)
        query += " ORDER BY created_at DESC"
        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._goal_from_row(row) for row in rows]

    def get_goal(self, goal_id: int) -> Goal | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        return self._goal_from_row(row) if row else None

    def delete_goal(self, chat_id: int, topic: str) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM goals WHERE chat_id = ? AND topic_key = ?",
                (chat_id, self.topic_key(topic)),
            )
            return cursor.rowcount > 0

    def delete_goal_by_id(self, goal_id: int) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
            return cursor.rowcount > 0

    def touch_goal(self, goal_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE goals SET last_run_at = ? WHERE id = ?",
                (self._now(), goal_id),
            )

    def filter_unseen(self, topic: str, items: Iterable[NewsItem]) -> list[NewsItem]:
        key = self.topic_key(topic)
        items = list(items)
        if not items:
            return []
        hashes = [item.fingerprint for item in items]
        placeholders = ",".join("?" for _ in hashes)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT item_hash FROM seen_items
                WHERE topic_key = ? AND item_hash IN ({placeholders})
                """,
                (key, *hashes),
            ).fetchall()
        seen = {row["item_hash"] for row in rows}
        return [item for item in items if item.fingerprint not in seen]

    def mark_seen_many(self, topic: str, items: Iterable[NewsItem]) -> None:
        key = self.topic_key(topic)
        now = self._now()
        rows = [
            (item.fingerprint, key, now, now, item.source, item.title, item.url)
            for item in items
        ]
        if not rows:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO seen_items(
                    item_hash, topic_key, first_seen_at, last_seen_at, source, title, url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_hash, topic_key) DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                rows,
            )

    @staticmethod
    def _goal_from_row(row: sqlite3.Row) -> Goal:
        return Goal(
            id=int(row["id"]),
            chat_id=int(row["chat_id"]),
            topic=str(row["topic"]),
            created_at=str(row["created_at"]),
            last_run_at=str(row["last_run_at"]) if row["last_run_at"] else None,
        )
