from dataclasses import dataclass
from typing import Mapping, Protocol

from coursepilot.models import CourseItem, Source
from coursepilot.store import Store
from coursepilot.validation import RejectedItem


@dataclass(frozen=True)
class FetchResult:
    """What one source produced in a run: the CourseItems to sync, plus anything
    that source rejected (e.g. an unparseable date) instead of coercing."""

    course_items: list[CourseItem]
    rejected: list[RejectedItem]


class CourseItemSource(Protocol):
    def fetch_course_items(self) -> FetchResult: ...


class PageSink(Protocol):
    def create_page(self, item: CourseItem) -> str: ...
    def update_page(self, page_id: str, item: CourseItem) -> None: ...
    def archive_page(self, page_id: str) -> None: ...


@dataclass(frozen=True)
class RunResult:
    total: int
    inserted: int
    updated: int
    archived: int
    reactivated: int
    skipped: int
    rejected: list[RejectedItem]


def run(
    *,
    sources: Mapping[Source, CourseItemSource],
    store: Store,
    notion_client: PageSink,
) -> RunResult:
    """Fetch CourseItems from every configured source and sync them into the local
    store and Notion.

    New ids are inserted; changed ids are updated in place; ids missing from a
    source's fetch are archived (never deleted) -- scoped to that source, so one
    source's disappearing items never archive another source's rows; an archived id
    reappearing is reactivated. Diff/write logic is identical regardless of which
    source an item came from. The sole seam: every adapter is injected, so this is
    reusable by the CLI now and a scheduler later without restructuring.
    """
    inserted = updated = archived = reactivated = skipped = 0
    total = 0
    rejected: list[RejectedItem] = []
    fetched_ids_by_source: dict[Source, set[str]] = {name: set() for name in sources}

    for name, source in sources.items():
        fetch_result = source.fetch_course_items()
        items = fetch_result.course_items
        rejected.extend(fetch_result.rejected)
        total += len(items)
        fetched_ids = fetched_ids_by_source[name]

        for item in items:
            fetched_ids.add(item.id)

            stored = store.get(item.id)
            if stored is None:
                notion_page_id = notion_client.create_page(item)
                store.insert(item, notion_page_id=notion_page_id)
                inserted += 1
                continue

            if stored.active and stored.item.content_hash == item.content_hash:
                skipped += 1
                continue

            notion_client.update_page(stored.notion_page_id, item)
            store.update(item)
            if stored.active:
                updated += 1
            else:
                reactivated += 1

    for name, fetched_ids in fetched_ids_by_source.items():
        for missing_id in store.active_ids(source=name) - fetched_ids:
            missing_stored = store.get(missing_id)
            if missing_stored is None:
                continue
            notion_client.archive_page(missing_stored.notion_page_id)
            store.archive(missing_id)
            archived += 1

    return RunResult(
        total=total,
        inserted=inserted,
        updated=updated,
        archived=archived,
        reactivated=reactivated,
        skipped=skipped,
        rejected=rejected,
    )
