import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from coursepilot.models import CourseItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS course_items (
    id TEXT PRIMARY KEY,
    course TEXT NOT NULL,
    title TEXT NOT NULL,
    item_type TEXT NOT NULL,
    due_date TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    last_synced_at TEXT NOT NULL,
    extraction_confidence TEXT NOT NULL,
    notion_page_id TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class StoredCourseItem:
    item: CourseItem
    notion_page_id: str

    @property
    def last_synced_at(self) -> datetime | None:
        return self.item.last_synced_at


class Store:
    """The local SQLite source of truth for which CourseItems have been synced."""

    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(db_path)
        with self._conn:
            self._conn.execute(_SCHEMA)

    def existing_ids(self) -> set[str]:
        rows = self._conn.execute("SELECT id FROM course_items").fetchall()
        return {row[0] for row in rows}

    def insert(self, item: CourseItem, *, notion_page_id: str) -> None:
        synced_item = item.model_copy(update={"last_synced_at": datetime.now(timezone.utc)})
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO course_items (
                    id, course, title, item_type, due_date, source, source_url,
                    content_hash, last_synced_at, extraction_confidence, notion_page_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    course=excluded.course,
                    title=excluded.title,
                    item_type=excluded.item_type,
                    due_date=excluded.due_date,
                    source=excluded.source,
                    source_url=excluded.source_url,
                    content_hash=excluded.content_hash,
                    last_synced_at=excluded.last_synced_at,
                    extraction_confidence=excluded.extraction_confidence,
                    notion_page_id=excluded.notion_page_id
                """,
                (
                    synced_item.id,
                    synced_item.course,
                    synced_item.title,
                    synced_item.item_type,
                    synced_item.due_date.isoformat(),
                    synced_item.source,
                    synced_item.source_url,
                    synced_item.content_hash,
                    synced_item.last_synced_at.isoformat()
                    if synced_item.last_synced_at
                    else None,
                    synced_item.extraction_confidence,
                    notion_page_id,
                ),
            )

    def get(self, item_id: str) -> StoredCourseItem | None:
        row = self._conn.execute(
            """
            SELECT course, title, item_type, due_date, source, source_url,
                   content_hash, last_synced_at, extraction_confidence, notion_page_id
            FROM course_items WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        (
            course,
            title,
            item_type,
            due_date,
            source,
            source_url,
            content_hash,
            last_synced_at,
            extraction_confidence,
            notion_page_id,
        ) = row
        item = CourseItem(
            id=item_id,
            course=course,
            title=title,
            item_type=item_type,
            due_date=datetime.fromisoformat(due_date),
            source=source,
            source_url=source_url,
            content_hash=content_hash,
            last_synced_at=datetime.fromisoformat(last_synced_at),
            extraction_confidence=extraction_confidence,
        )
        return StoredCourseItem(item=item, notion_page_id=notion_page_id)

    def close(self) -> None:
        self._conn.close()
