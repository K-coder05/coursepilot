from datetime import datetime, timezone

import httpx
import respx

from coursepilot.models import CourseItem
from coursepilot.notion import NotionClient

TOKEN = "notion-secret-token"
DATABASE_ID = "db-abc-123"


def make_item() -> CourseItem:
    return CourseItem.build(
        course="DATA C104-LEC-001",
        title="Homework 3",
        item_type="assignment",
        due_date=datetime(2026, 9, 15, 23, 59, tzinfo=timezone.utc),
        source="canvas",
        source_url="https://bcourses.berkeley.edu/courses/1/assignments/42",
        extraction_confidence="direct",
    )


def make_client() -> NotionClient:
    return NotionClient(token=TOKEN, database_id=DATABASE_ID)


@respx.mock
def test_create_page_returns_the_new_page_id() -> None:
    respx.post("https://api.notion.com/v1/pages").mock(
        return_value=httpx.Response(200, json={"id": "page-xyz-789"})
    )

    page_id = make_client().create_page(make_item())

    assert page_id == "page-xyz-789"


@respx.mock
def test_create_page_targets_the_configured_database() -> None:
    route = respx.post("https://api.notion.com/v1/pages").mock(
        return_value=httpx.Response(200, json={"id": "page-xyz-789"})
    )

    make_client().create_page(make_item())

    body = route.calls.last.request.content
    import json

    payload = json.loads(body)
    assert payload["parent"] == {"database_id": DATABASE_ID}


@respx.mock
def test_create_page_maps_course_item_fields_to_notion_properties() -> None:
    route = respx.post("https://api.notion.com/v1/pages").mock(
        return_value=httpx.Response(200, json={"id": "page-xyz-789"})
    )

    make_client().create_page(make_item())

    import json

    payload = json.loads(route.calls.last.request.content)
    properties = payload["properties"]

    assert properties["Title"]["title"][0]["text"]["content"] == "Homework 3"
    assert properties["Course"]["rich_text"][0]["text"]["content"] == "DATA C104-LEC-001"
    assert properties["Type"]["select"]["name"] == "assignment"
    assert properties["Due Date"]["date"]["start"] == "2026-09-15T23:59:00+00:00"
    assert properties["Source"]["select"]["name"] == "canvas"
    assert (
        properties["Link"]["url"]
        == "https://bcourses.berkeley.edu/courses/1/assignments/42"
    )
    assert properties["Confidence"]["select"]["name"] == "direct"
    assert "Status" not in properties


@respx.mock
def test_create_page_sends_auth_and_notion_version_headers() -> None:
    route = respx.post("https://api.notion.com/v1/pages").mock(
        return_value=httpx.Response(200, json={"id": "page-xyz-789"})
    )

    make_client().create_page(make_item())

    headers = route.calls.last.request.headers
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert headers["Notion-Version"] == "2022-06-28"
