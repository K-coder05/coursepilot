from datetime import datetime, timezone
from pathlib import Path

from coursepilot.models import CourseItem
from coursepilot.run import FetchResult, run
from coursepilot.store import Store
from coursepilot.validation import RejectedItem


class FakeSource:
    def __init__(
        self, items: list[CourseItem], rejected: list[RejectedItem] | None = None
    ) -> None:
        self._items = items
        self._rejected = rejected or []

    def fetch_course_items(self) -> FetchResult:
        return FetchResult(course_items=self._items, rejected=self._rejected)


class FakeNotionClient:
    def __init__(self) -> None:
        self.created_pages: list[CourseItem] = []
        self.updated_pages: list[tuple[str, CourseItem]] = []
        self.archived_page_ids: list[str] = []
        self._next_page_id = 0

    def create_page(self, item: CourseItem) -> str:
        self.created_pages.append(item)
        self._next_page_id += 1
        return f"fake-page-{self._next_page_id}"

    def update_page(self, page_id: str, item: CourseItem) -> None:
        self.updated_pages.append((page_id, item))

    def archive_page(self, page_id: str) -> None:
        self.archived_page_ids.append(page_id)


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


def make_raw_site_item(
    source_url: str = "https://example.test/raw-site/1", title: str = "Reading response 2"
) -> CourseItem:
    return CourseItem.build(
        course="CS 162",
        title=title,
        item_type="assignment",
        due_date=datetime(2026, 9, 15, 23, 59, tzinfo=timezone.utc),
        source="raw_site",
        source_url=source_url,
        extraction_confidence="llm_high",
    )


def test_run_inserts_all_new_items_into_notion_and_store(tmp_path: Path) -> None:
    items = [make_item("https://example.test/a/1"), make_item("https://example.test/a/2")]
    canvas_client = FakeSource(items)
    notion_client = FakeNotionClient()
    store = Store(tmp_path / "coursepilot.db")

    result = run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)

    assert result.total == 2
    assert result.inserted == 2
    assert result.skipped == 0
    assert {i.id for i in notion_client.created_pages} == {i.id for i in items}
    assert store.existing_ids() == {i.id for i in items}


def test_run_records_returned_notion_page_id_in_store(tmp_path: Path) -> None:
    item = make_item()
    canvas_client = FakeSource([item])
    notion_client = FakeNotionClient()
    store = Store(tmp_path / "coursepilot.db")

    run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)

    stored = store.get(item.id)
    assert stored is not None
    assert stored.notion_page_id == "fake-page-1"


def test_rerunning_with_unchanged_data_creates_no_duplicate_notion_pages(
    tmp_path: Path,
) -> None:
    items = [make_item("https://example.test/a/1"), make_item("https://example.test/a/2")]
    canvas_client = FakeSource(items)
    notion_client = FakeNotionClient()
    store = Store(tmp_path / "coursepilot.db")

    first = run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)
    second = run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)

    assert first.inserted == 2
    assert second.inserted == 0
    assert second.skipped == 2
    assert len(notion_client.created_pages) == 2


def test_run_only_inserts_items_not_already_in_the_store(tmp_path: Path) -> None:
    already_synced = make_item("https://example.test/a/1", title="Already synced")
    new_item = make_item("https://example.test/a/2", title="Brand new")
    store = Store(tmp_path / "coursepilot.db")
    store.insert(already_synced, notion_page_id="pre-existing-page")

    canvas_client = FakeSource([already_synced, new_item])
    notion_client = FakeNotionClient()

    result = run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)

    assert result.total == 2
    assert result.inserted == 1
    assert result.skipped == 1
    assert [i.id for i in notion_client.created_pages] == [new_item.id]


def test_run_updates_notion_and_store_when_due_date_changes(tmp_path: Path) -> None:
    original = make_item("https://example.test/a/1")
    store = Store(tmp_path / "coursepilot.db")
    store.insert(original, notion_page_id="existing-page")
    changed = original.model_copy(
        update={
            "due_date": datetime(2026, 9, 20, 23, 59, tzinfo=timezone.utc),
            "content_hash": "changed-hash",
        }
    )
    canvas_client = FakeSource([changed])
    notion_client = FakeNotionClient()

    result = run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)

    assert result.updated == 1
    assert result.inserted == 0
    assert result.skipped == 0
    assert notion_client.updated_pages == [("existing-page", changed)]
    stored = store.get(original.id)
    assert stored is not None
    assert stored.item.due_date == changed.due_date


def test_run_skips_unchanged_active_item_with_no_notion_call(tmp_path: Path) -> None:
    item = make_item()
    store = Store(tmp_path / "coursepilot.db")
    store.insert(item, notion_page_id="existing-page")
    canvas_client = FakeSource([item])
    notion_client = FakeNotionClient()

    result = run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)

    assert result.skipped == 1
    assert result.updated == 0
    assert notion_client.updated_pages == []
    assert notion_client.created_pages == []


def test_run_archives_item_missing_from_the_current_fetch(tmp_path: Path) -> None:
    present = make_item("https://example.test/a/1")
    removed = make_item("https://example.test/a/2")
    store = Store(tmp_path / "coursepilot.db")
    store.insert(present, notion_page_id="present-page")
    store.insert(removed, notion_page_id="removed-page")
    canvas_client = FakeSource([present])
    notion_client = FakeNotionClient()

    result = run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)

    assert result.archived == 1
    assert notion_client.archived_page_ids == ["removed-page"]
    stored = store.get(removed.id)
    assert stored is not None
    assert stored.active is False


def test_run_archives_a_raw_site_item_missing_from_the_current_fetch(tmp_path: Path) -> None:
    present = make_raw_site_item("https://example.test/raw-site/1")
    removed = make_raw_site_item("https://example.test/raw-site/2")
    store = Store(tmp_path / "coursepilot.db")
    store.insert(present, notion_page_id="present-page")
    store.insert(removed, notion_page_id="removed-page")
    raw_site_client = FakeSource([present])
    notion_client = FakeNotionClient()

    result = run(
        sources={"raw_site": raw_site_client}, store=store, notion_client=notion_client
    )

    assert result.archived == 1
    assert notion_client.archived_page_ids == ["removed-page"]
    stored = store.get(removed.id)
    assert stored is not None
    assert stored.active is False


def test_run_reactivates_an_archived_item_that_reappears(tmp_path: Path) -> None:
    item = make_item()
    store = Store(tmp_path / "coursepilot.db")
    store.insert(item, notion_page_id="existing-page")
    store.archive(item.id)
    canvas_client = FakeSource([item])
    notion_client = FakeNotionClient()

    result = run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)

    assert result.reactivated == 1
    assert result.skipped == 0
    assert notion_client.updated_pages == [("existing-page", item)]
    stored = store.get(item.id)
    assert stored is not None
    assert stored.active is True


def test_run_updates_notion_and_store_when_raw_site_item_content_changes(
    tmp_path: Path,
) -> None:
    original = make_raw_site_item()
    store = Store(tmp_path / "coursepilot.db")
    store.insert(original, notion_page_id="existing-page")
    changed = original.model_copy(
        update={
            "due_date": datetime(2026, 9, 20, 23, 59, tzinfo=timezone.utc),
            "content_hash": "changed-hash",
        }
    )
    raw_site_client = FakeSource([changed])
    notion_client = FakeNotionClient()

    result = run(
        sources={"raw_site": raw_site_client}, store=store, notion_client=notion_client
    )

    assert result.updated == 1
    assert result.inserted == 0
    assert notion_client.updated_pages == [("existing-page", changed)]
    stored = store.get(original.id)
    assert stored is not None
    assert stored.item.due_date == changed.due_date


def test_run_reactivates_an_archived_raw_site_item_that_reappears(tmp_path: Path) -> None:
    item = make_raw_site_item()
    store = Store(tmp_path / "coursepilot.db")
    store.insert(item, notion_page_id="existing-page")
    store.archive(item.id)
    raw_site_client = FakeSource([item])
    notion_client = FakeNotionClient()

    result = run(
        sources={"raw_site": raw_site_client}, store=store, notion_client=notion_client
    )

    assert result.reactivated == 1
    assert result.skipped == 0
    stored = store.get(item.id)
    assert stored is not None
    assert stored.active is True


def test_run_archive_then_restore_across_three_runs(tmp_path: Path) -> None:
    item = make_item()
    store = Store(tmp_path / "coursepilot.db")
    notion_client = FakeNotionClient()

    first = run(sources={"canvas": FakeSource([item])}, store=store, notion_client=notion_client)
    second = run(sources={"canvas": FakeSource([])}, store=store, notion_client=notion_client)
    third = run(sources={"canvas": FakeSource([item])}, store=store, notion_client=notion_client)

    assert first.inserted == 1
    assert second.archived == 1
    assert third.reactivated == 1
    stored = store.get(item.id)
    assert stored is not None
    assert stored.active is True


def test_run_archiving_never_touches_other_sources(tmp_path: Path) -> None:
    raw_site_item = make_raw_site_item()
    fetched_item = make_item("https://example.test/a/1")
    store = Store(tmp_path / "coursepilot.db")
    store.insert(raw_site_item, notion_page_id="raw-site-page")
    canvas_client = FakeSource([fetched_item])
    notion_client = FakeNotionClient()

    result = run(sources={"canvas": canvas_client}, store=store, notion_client=notion_client)

    assert result.archived == 0
    assert notion_client.archived_page_ids == []
    stored = store.get(raw_site_item.id)
    assert stored is not None
    assert stored.active is True


def test_run_processes_canvas_and_raw_site_together_in_one_invocation(
    tmp_path: Path,
) -> None:
    canvas_item = make_item("https://example.test/a/1")
    raw_site_item = make_raw_site_item()
    store = Store(tmp_path / "coursepilot.db")
    notion_client = FakeNotionClient()

    result = run(
        sources={
            "canvas": FakeSource([canvas_item]),
            "raw_site": FakeSource([raw_site_item]),
        },
        store=store,
        notion_client=notion_client,
    )

    assert result.total == 2
    assert result.inserted == 2
    assert {i.id for i in notion_client.created_pages} == {canvas_item.id, raw_site_item.id}
    assert store.existing_ids() == {canvas_item.id, raw_site_item.id}


def test_run_archives_only_the_source_whose_fetch_dropped_the_item(tmp_path: Path) -> None:
    canvas_item = make_item("https://example.test/a/1")
    raw_site_item = make_raw_site_item()
    store = Store(tmp_path / "coursepilot.db")
    store.insert(canvas_item, notion_page_id="canvas-page")
    store.insert(raw_site_item, notion_page_id="raw-site-page")
    notion_client = FakeNotionClient()

    result = run(
        sources={"canvas": FakeSource([]), "raw_site": FakeSource([raw_site_item])},
        store=store,
        notion_client=notion_client,
    )

    assert result.archived == 1
    assert notion_client.archived_page_ids == ["canvas-page"]
    canvas_stored = store.get(canvas_item.id)
    raw_site_stored = store.get(raw_site_item.id)
    assert canvas_stored is not None and canvas_stored.active is False
    assert raw_site_stored is not None and raw_site_stored.active is True


def test_rerunning_five_times_with_unchanged_data_across_both_sources_is_idempotent(
    tmp_path: Path,
) -> None:
    canvas_item = make_item("https://example.test/a/1")
    raw_site_item = make_raw_site_item()
    store = Store(tmp_path / "coursepilot.db")
    notion_client = FakeNotionClient()

    def make_sources() -> dict[str, FakeSource]:
        return {
            "canvas": FakeSource([canvas_item]),
            "raw_site": FakeSource([raw_site_item]),
        }

    results = [
        run(sources=make_sources(), store=store, notion_client=notion_client)
        for _ in range(5)
    ]

    first, *reruns = results
    assert first.inserted == 2
    for rerun_result in reruns:
        assert rerun_result.inserted == 0
        assert rerun_result.updated == 0
        assert rerun_result.archived == 0
        assert rerun_result.reactivated == 0
        assert rerun_result.skipped == 2

    assert store.existing_ids() == {canvas_item.id, raw_site_item.id}
    assert len(notion_client.created_pages) == 2
    assert notion_client.updated_pages == []
    assert notion_client.archived_page_ids == []


def test_run_surfaces_rejected_items_from_a_source_without_writing_them_to_notion(
    tmp_path: Path,
) -> None:
    good_item = make_raw_site_item()
    rejection = RejectedItem(title="Malformed reading", reason="unparseable date")
    store = Store(tmp_path / "coursepilot.db")
    notion_client = FakeNotionClient()

    result = run(
        sources={"raw_site": FakeSource([good_item], rejected=[rejection])},
        store=store,
        notion_client=notion_client,
    )

    assert result.rejected == [rejection]
    assert result.inserted == 1
    assert {i.id for i in notion_client.created_pages} == {good_item.id}
    assert store.existing_ids() == {good_item.id}


def test_run_collects_rejected_items_across_both_sources(tmp_path: Path) -> None:
    canvas_rejection = RejectedItem(title="Bad canvas item", reason="malformed")
    raw_site_rejection = RejectedItem(title="Bad raw-site item", reason="unparseable date")
    store = Store(tmp_path / "coursepilot.db")
    notion_client = FakeNotionClient()

    result = run(
        sources={
            "canvas": FakeSource([], rejected=[canvas_rejection]),
            "raw_site": FakeSource([], rejected=[raw_site_rejection]),
        },
        store=store,
        notion_client=notion_client,
    )

    assert sorted(result.rejected, key=lambda r: r.title) == sorted(
        [canvas_rejection, raw_site_rejection], key=lambda r: r.title
    )


def test_ids_never_collide_across_sources_even_with_the_same_title_and_url(
    tmp_path: Path,
) -> None:
    same_url = "https://example.test/shared-path"
    canvas_item = make_item(same_url, title="Homework 3")
    raw_site_item = make_raw_site_item(same_url, title="Homework 3")
    store = Store(tmp_path / "coursepilot.db")
    notion_client = FakeNotionClient()

    result = run(
        sources={
            "canvas": FakeSource([canvas_item]),
            "raw_site": FakeSource([raw_site_item]),
        },
        store=store,
        notion_client=notion_client,
    )

    assert canvas_item.id != raw_site_item.id
    assert result.inserted == 2
    assert store.existing_ids() == {canvas_item.id, raw_site_item.id}
