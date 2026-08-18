from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import OpportunityItem


class Store:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_key TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    region TEXT NOT NULL DEFAULT 'internacional',
                    country TEXT NOT NULL DEFAULT '',
                    company TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    published_at TEXT,
                    collected_at TEXT NOT NULL,
                    score REAL NOT NULL DEFAULT 0,
                    reason TEXT NOT NULL DEFAULT '',
                    raw_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            existing_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(items)").fetchall()
            }
            migrations = [
                ("region", "TEXT NOT NULL DEFAULT 'internacional'"),
                ("country", "TEXT NOT NULL DEFAULT ''"),
            ]
            for column_name, column_sql in migrations:
                if column_name not in existing_columns:
                    conn.execute(f"ALTER TABLE items ADD COLUMN {column_name} {column_sql}")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_items_collected_at ON items(collected_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_items_region_kind ON items(region, kind)"
            )

    def upsert_item(self, item: OpportunityItem) -> bool:
        with self._connect() as conn:
            result = conn.execute(
                """
                INSERT OR IGNORE INTO items (
                    item_key, title, url, source_name, kind, region, country, company, summary,
                    published_at, collected_at, score, reason, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.key,
                    item.title,
                    item.url,
                    item.source_name,
                    item.kind,
                    item.region,
                    item.country,
                    item.company,
                    item.summary,
                    _iso(item.published_at),
                    _iso(item.collected_at),
                    item.score,
                    item.reason,
                    json.dumps(item.raw, ensure_ascii=False),
                ),
            )
            return result.rowcount > 0

    def list_recent_items(self, hours: int = 24) -> list[OpportunityItem]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT title, url, source_name, kind, region, country, company, summary, published_at,
                       collected_at, score, reason, raw_json
                FROM items
                WHERE collected_at >= ?
                ORDER BY score DESC, COALESCE(published_at, collected_at) DESC
                """,
                (_iso(since),),
            ).fetchall()
        return [_row_to_item(row) for row in rows]


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _row_to_item(row: sqlite3.Row) -> OpportunityItem:
    published_at = row["published_at"] or None
    collected_at = row["collected_at"] or None
    return OpportunityItem(
        title=row["title"],
        url=row["url"],
        source_name=row["source_name"],
        kind=row["kind"],
        region=row["region"] or "internacional",
        country=row["country"] or "",
        company=row["company"],
        summary=row["summary"],
        published_at=datetime.fromisoformat(published_at) if published_at else None,
        collected_at=datetime.fromisoformat(collected_at) if collected_at else datetime.now(timezone.utc),
        score=float(row["score"]),
        reason=row["reason"],
        raw=json.loads(row["raw_json"] or "{}"),
    )
