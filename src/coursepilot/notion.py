from typing import Any

import httpx

from coursepilot.models import CourseItem

_NOTION_VERSION = "2022-06-28"


class NotionClient:
    """Creates Notion database pages for CourseItems. Insert-only: never reads Notion back."""

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
                "properties": _properties_for(item),
            },
        )
        response.raise_for_status()
        page_id: str = response.json()["id"]
        return page_id


def _properties_for(item: CourseItem) -> dict[str, Any]:
    return {
        "Title": {"title": [{"text": {"content": item.title}}]},
        "Course": {"rich_text": [{"text": {"content": item.course}}]},
        "Type": {"select": {"name": item.item_type}},
        "Due Date": {"date": {"start": item.due_date.isoformat()}},
        "Source": {"select": {"name": item.source}},
        "Link": {"url": item.source_url},
        "Confidence": {"select": {"name": item.extraction_confidence}},
    }
