from datetime import datetime, timezone
from pathlib import Path

from coursepilot.models import CourseItem
from coursepilot.store import Store


def make_item(source_url: str = "https://example.test/a/1") -> CourseItem:
    return CourseItem.build(
        course="DATA C104-LEC-001",
        title="Homework 3",
        item_type="assignment",
        due_date=datetime(2026, 9, 15, 23, 59, tzinfo=timezone.utc),
        source="canvas",
        source_url=source_url,
        extraction_confidence="direct",
    )


def test_new_store_has_no_existing_ids(tmp_path: Path) -> None:
    store = Store(tmp_path / "coursepilot.db")

    assert store.existing_ids() == set()


def test_insert_adds_id_to_existing_ids(tmp_path: Path) -> None:
    store = Store(tmp_path / "coursepilot.db")
    item = make_item()

    store.insert(item, notion_page_id="notion-page-1")

    assert store.existing_ids() == {item.id}


def test_insert_stamps_last_synced_at_and_records_notion_page_id(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "coursepilot.db")
    item = make_item()

    store.insert(item, notion_page_id="notion-page-1")
    stored = store.get(item.id)

    assert stored is not None
    assert stored.notion_page_id == "notion-page-1"
    assert stored.last_synced_at is not None
    assert stored.last_synced_at.tzinfo is not None


def test_get_returns_none_for_unknown_id(tmp_path: Path) -> None:
    store = Store(tmp_path / "coursepilot.db")

    assert store.get("nonexistent") is None


def test_data_persists_across_store_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "coursepilot.db"
    item = make_item()
    Store(db_path).insert(item, notion_page_id="notion-page-1")

    reopened = Store(db_path)

    assert reopened.existing_ids() == {item.id}
    assert reopened.get(item.id).notion_page_id == "notion-page-1"


def test_insert_is_idempotent_for_the_same_id(tmp_path: Path) -> None:
    store = Store(tmp_path / "coursepilot.db")
    item = make_item()

    store.insert(item, notion_page_id="notion-page-1")
    store.insert(item, notion_page_id="notion-page-1")

    assert store.existing_ids() == {item.id}


def test_distinct_items_are_tracked_independently(tmp_path: Path) -> None:
    store = Store(tmp_path / "coursepilot.db")
    item_a = make_item("https://example.test/a/1")
    item_b = make_item("https://example.test/a/2")

    store.insert(item_a, notion_page_id="notion-page-1")
    store.insert(item_b, notion_page_id="notion-page-2")

    assert store.existing_ids() == {item_a.id, item_b.id}
