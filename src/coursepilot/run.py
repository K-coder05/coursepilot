from dataclasses import dataclass
from typing import Protocol

from coursepilot.models import CourseItem
from coursepilot.store import Store


class CourseItemSource(Protocol):
    def fetch_course_items(self) -> list[CourseItem]: ...


class PageSink(Protocol):
    def create_page(self, item: CourseItem) -> str: ...


@dataclass(frozen=True)
class RunResult:
    total: int
    inserted: int
    skipped: int


def run(
    *, canvas_client: CourseItemSource, store: Store, notion_client: PageSink
) -> RunResult:
    """Fetch CourseItems from Canvas and insert any not already in the local store into Notion.

    The sole seam: every adapter is injected, so this is reusable by the CLI now and a
    scheduler later without restructuring.
    """
    items = canvas_client.fetch_course_items()
    existing_ids = store.existing_ids()

    inserted = 0
    for item in items:
        if item.id in existing_ids:
            continue
        notion_page_id = notion_client.create_page(item)
        store.insert(item, notion_page_id=notion_page_id)
        inserted += 1

    return RunResult(total=len(items), inserted=inserted, skipped=len(items) - inserted)
