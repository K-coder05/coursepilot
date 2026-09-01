from typing import Any

import httpx

from coursepilot.models import CourseItem

_NOTION_VERSION = "2022-06-28"


class NotionClient:
    """Creates and updates Notion database pages for CourseItems.

    Archival is represented by the sync-managed "Archived" checkbox property, not
    Notion's native page-archived (trash) flag: Notion permanently deletes trashed
    pages after ~30 days, which would violate the requirement that archived items
    are retained, never deleted.
    """

    def __init__(self, *, token: str, database_id: str) -> None:
        self._database_id = database_id
        self._client = httpx.Client(
            base_url="https://api.notion.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": _NOTION_VERSION,
            },
        )

    def create_page(self, item: CourseItem) -> str:
        response = self._client.post(
            "/v1/pages",
            json={
                "parent": {"database_id": self._database_id},
                "properties": _properties_for(item, archived=False),
            },
        )
        response.raise_for_status()
        page_id: str = response.json()["id"]
        return page_id

    def update_page(self, page_id: str, item: CourseItem) -> None:
        """Write an item's current fields to its Notion page and mark it not archived."""
        response = self._client.patch(
            f"/v1/pages/{page_id}",
            json={"properties": _properties_for(item, archived=False)},
        )
        response.raise_for_status()

    def archive_page(self, page_id: str) -> None:
        """Flag a Notion page as archived via the Archived property. Never deletes the page."""
        response = self._client.patch(
            f"/v1/pages/{page_id}",
            json={"properties": {"Archived": {"checkbox": True}}},
        )
        response.raise_for_status()


def _properties_for(item: CourseItem, *, archived: bool) -> dict[str, Any]:
    return {
        "Title": {"title": [{"text": {"content": item.title}}]},
        "Course": {"rich_text": [{"text": {"content": item.course}}]},
        "Type": {"select": {"name": item.item_type}},
        "Due Date": {"date": {"start": item.due_date.isoformat()}},
        "Source": {"select": {"name": item.source}},
        "Link": {"url": item.source_url},
        "Confidence": {"select": {"name": item.extraction_confidence}},
        "Archived": {"checkbox": archived},
    }
