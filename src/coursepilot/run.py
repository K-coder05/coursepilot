from dataclasses import dataclass
from typing import Protocol

from coursepilot.models import CourseItem
from coursepilot.store import Store


class CourseItemSource(Protocol):
    def fetch_course_items(self) -> list[CourseItem]: ...


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


def run(
    *, canvas_client: CourseItemSource, store: Store, notion_client: PageSink
) -> RunResult:
    """Fetch CourseItems from Canvas and sync them into the local store and Notion.

    New ids are inserted; changed ids are updated in place; ids missing from the fetch
    are archived (never deleted); an archived id reappearing is reactivated. The sole
    seam: every adapter is injected, so this is reusable by the CLI now and a
    scheduler later without restructuring.
    """
    items = canvas_client.fetch_course_items()

    inserted = updated = archived = reactivated = skipped = 0
    fetched_ids: set[str] = set()

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

    # This ticket's sync engine only handles the Canvas source; archival is scoped
    # to "canvas" so a future raw_site run sharing this store never touches its rows.
    for missing_id in store.active_ids(source="canvas") - fetched_ids:
        missing_stored = store.get(missing_id)
        if missing_stored is None:
            continue
        notion_client.archive_page(missing_stored.notion_page_id)
        store.archive(missing_id)
        archived += 1

    return RunResult(
        total=len(items),
        inserted=inserted,
        updated=updated,
        archived=archived,
        reactivated=reactivated,
        skipped=skipped,
    )
