from datetime import datetime, timezone

import httpx
import respx

from coursepilot.canvas import CanvasClient

BASE_URL = "https://bcourses.berkeley.edu"
TOKEN = "test-token-123"
COURSE_ID = "1"


def make_client() -> CanvasClient:
    return CanvasClient(base_url=BASE_URL, token=TOKEN, course_id=COURSE_ID)


@respx.mock
def test_fetch_course_items_maps_assignment_to_course_item() -> None:
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}").mock(
        return_value=httpx.Response(200, json={"course_code": "DATA C104-LEC-001"})
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 42,
                    "name": "Homework 3",
                    "due_at": "2026-09-15T23:59:00Z",
                    "html_url": f"{BASE_URL}/courses/1/assignments/42",
                    "submission_types": ["online_upload"],
                }
            ],
        )
    )
    respx.get(f"{BASE_URL}/api/v1/calendar_events").mock(
        return_value=httpx.Response(200, json=[])
    )

    items = make_client().fetch_course_items().course_items

    assert len(items) == 1
    item = items[0]
    assert item.course == "DATA C104-LEC-001"
    assert item.title == "Homework 3"
    assert item.item_type == "assignment"
    assert item.due_date == datetime(2026, 9, 15, 23, 59, tzinfo=timezone.utc)
    assert item.source == "canvas"
    assert item.source_url == f"{BASE_URL}/courses/1/assignments/42"
    assert item.extraction_confidence == "direct"


@respx.mock
def test_fetch_course_items_never_reports_rejected_items() -> None:
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}").mock(
        return_value=httpx.Response(200, json={"course_code": "DATA C104-LEC-001"})
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(f"{BASE_URL}/api/v1/calendar_events").mock(
        return_value=httpx.Response(200, json=[])
    )

    result = make_client().fetch_course_items()

    assert result.rejected == []


@respx.mock
def test_fetch_course_items_classifies_online_quiz_submission_type_as_quiz() -> None:
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}").mock(
        return_value=httpx.Response(200, json={"course_code": "DATA C104-LEC-001"})
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 43,
                    "name": "Quiz 2",
                    "due_at": "2026-09-20T23:59:00Z",
                    "html_url": f"{BASE_URL}/courses/1/assignments/43",
                    "submission_types": ["online_quiz"],
                }
            ],
        )
    )
    respx.get(f"{BASE_URL}/api/v1/calendar_events").mock(
        return_value=httpx.Response(200, json=[])
    )

    items = make_client().fetch_course_items().course_items

    assert items[0].item_type == "quiz"


@respx.mock
def test_fetch_course_items_skips_assignments_without_due_date() -> None:
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}").mock(
        return_value=httpx.Response(200, json={"course_code": "DATA C104-LEC-001"})
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 44,
                    "name": "Ungraded reading",
                    "due_at": None,
                    "html_url": f"{BASE_URL}/courses/1/assignments/44",
                    "submission_types": ["none"],
                }
            ],
        )
    )
    respx.get(f"{BASE_URL}/api/v1/calendar_events").mock(
        return_value=httpx.Response(200, json=[])
    )

    items = make_client().fetch_course_items().course_items

    assert items == []


@respx.mock
def test_fetch_course_items_maps_calendar_event_to_exam() -> None:
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}").mock(
        return_value=httpx.Response(200, json={"course_code": "DATA C104-LEC-001"})
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(f"{BASE_URL}/api/v1/calendar_events").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 900,
                    "title": "Midterm 1",
                    "start_at": "2026-10-01T17:00:00Z",
                    "html_url": f"{BASE_URL}/calendar?event_id=900",
                }
            ],
        )
    )

    items = make_client().fetch_course_items().course_items

    assert len(items) == 1
    item = items[0]
    assert item.title == "Midterm 1"
    assert item.item_type == "exam"
    assert item.due_date == datetime(2026, 10, 1, 17, 0, tzinfo=timezone.utc)
    assert item.source_url == f"{BASE_URL}/calendar?event_id=900"


@respx.mock
def test_fetch_course_items_excludes_calendar_events_already_covered_by_an_assignment() -> None:
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}").mock(
        return_value=httpx.Response(200, json={"course_code": "DATA C104-LEC-001"})
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 45,
                    "name": "Midterm 1",
                    "due_at": "2026-10-01T17:00:00Z",
                    "html_url": f"{BASE_URL}/courses/1/assignments/45",
                    "submission_types": ["online_upload"],
                }
            ],
        )
    )
    respx.get(f"{BASE_URL}/api/v1/calendar_events").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 900,
                    "title": "Midterm 1",
                    "start_at": "2026-10-01T17:00:00Z",
                    "html_url": f"{BASE_URL}/calendar?event_id=900",
                }
            ],
        )
    )

    items = make_client().fetch_course_items().course_items

    assert len(items) == 1
    assert items[0].source_url == f"{BASE_URL}/courses/1/assignments/45"


@respx.mock
def test_fetch_course_items_skips_calendar_events_without_start_at() -> None:
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}").mock(
        return_value=httpx.Response(200, json={"course_code": "DATA C104-LEC-001"})
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(f"{BASE_URL}/api/v1/calendar_events").mock(
        return_value=httpx.Response(
            200, json=[{"id": 901, "title": "TBD review session", "start_at": None}]
        )
    )

    items = make_client().fetch_course_items().course_items

    assert items == []


@respx.mock
def test_fetch_course_items_sends_bearer_token() -> None:
    course_route = respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}").mock(
        return_value=httpx.Response(200, json={"course_code": "DATA C104-LEC-001"})
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(f"{BASE_URL}/api/v1/calendar_events").mock(
        return_value=httpx.Response(200, json=[])
    )

    make_client().fetch_course_items().course_items

    sent_request = course_route.calls.last.request
    assert sent_request.headers["Authorization"] == f"Bearer {TOKEN}"


@respx.mock
def test_fetch_course_items_follows_link_header_pagination() -> None:
    next_url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments?page=2"
    page_1 = httpx.Response(
        200,
        json=[
            {
                "id": 1,
                "name": "Page 1 item",
                "due_at": "2026-09-01T00:00:00Z",
                "html_url": f"{BASE_URL}/courses/1/assignments/1",
                "submission_types": ["online_upload"],
            }
        ],
        headers={"Link": f'<{next_url}>; rel="next"'},
    )
    page_2 = httpx.Response(
        200,
        json=[
            {
                "id": 2,
                "name": "Page 2 item",
                "due_at": "2026-09-02T00:00:00Z",
                "html_url": f"{BASE_URL}/courses/1/assignments/2",
                "submission_types": ["online_upload"],
            }
        ],
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}").mock(
        return_value=httpx.Response(200, json={"course_code": "DATA C104-LEC-001"})
    )
    respx.get(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments").mock(
        side_effect=[page_1, page_2]
    )
    respx.get(f"{BASE_URL}/api/v1/calendar_events").mock(
        return_value=httpx.Response(200, json=[])
    )

    items = make_client().fetch_course_items().course_items

    titles = {item.title for item in items}
    assert titles == {"Page 1 item", "Page 2 item"}
