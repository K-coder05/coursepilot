from datetime import datetime, timezone
from pathlib import Path

from coursepilot.models import CourseItem
from coursepilot.run import run
from coursepilot.store import Store


class FakeCanvasClient:
    def __init__(self, items: list[CourseItem]) -> None:
        self._items = items

    def fetch_course_items(self) -> list[CourseItem]:
        return self._items


class FakeNotionClient:
    def __init__(self) -> None:
        self.created_pages: list[CourseItem] = []
        self._next_page_id = 0

    def create_page(self, item: CourseItem) -> str:
        self.created_pages.append(item)
        self._next_page_id += 1
        return f"fake-page-{self._next_page_id}"


def make_item(source_url: str = "https://example.test/a/1", title: str = "Homework 3") -> CourseItem:
    return CourseItem.build(
        course="DATA C104-LEC-001",
        title=title,
        item_type="assignment",
        due_date=datetime(2026, 9, 15, 23, 59, tzinfo=timezone.utc),
        source="canvas",
        source_url=source_url,
        extraction_confidence="direct",
    )


def test_run_inserts_all_new_items_into_notion_and_store(tmp_path: Path) -> None:
    items = [make_item("https://example.test/a/1"), make_item("https://example.test/a/2")]
    canvas_client = FakeCanvasClient(items)
    notion_client = FakeNotionClient()
    store = Store(tmp_path / "coursepilot.db")

    result = run(canvas_client=canvas_client, store=store, notion_client=notion_client)

    assert result.total == 2
    assert result.inserted == 2
    assert result.skipped == 0
    assert {i.id for i in notion_client.created_pages} == {i.id for i in items}
    assert store.existing_ids() == {i.id for i in items}


def test_run_records_returned_notion_page_id_in_store(tmp_path: Path) -> None:
    item = make_item()
    canvas_client = FakeCanvasClient([item])
    notion_client = FakeNotionClient()
    store = Store(tmp_path / "coursepilot.db")

    run(canvas_client=canvas_client, store=store, notion_client=notion_client)

    stored = store.get(item.id)
    assert stored is not None
    assert stored.notion_page_id == "fake-page-1"


def test_rerunning_with_unchanged_data_creates_no_duplicate_notion_pages(
    tmp_path: Path,
) -> None:
    items = [make_item("https://example.test/a/1"), make_item("https://example.test/a/2")]
    canvas_client = FakeCanvasClient(items)
    notion_client = FakeNotionClient()
    store = Store(tmp_path / "coursepilot.db")

    first = run(canvas_client=canvas_client, store=store, notion_client=notion_client)
    second = run(canvas_client=canvas_client, store=store, notion_client=notion_client)

    assert first.inserted == 2
    assert second.inserted == 0
    assert second.skipped == 2
    assert len(notion_client.created_pages) == 2


def test_run_only_inserts_items_not_already_in_the_store(tmp_path: Path) -> None:
    already_synced = make_item("https://example.test/a/1", title="Already synced")
    new_item = make_item("https://example.test/a/2", title="Brand new")
    store = Store(tmp_path / "coursepilot.db")
    store.insert(already_synced, notion_page_id="pre-existing-page")

    canvas_client = FakeCanvasClient([already_synced, new_item])
    notion_client = FakeNotionClient()

    result = run(canvas_client=canvas_client, store=store, notion_client=notion_client)

    assert result.total == 2
    assert result.inserted == 1
    assert result.skipped == 1
    assert [i.id for i in notion_client.created_pages] == [new_item.id]
