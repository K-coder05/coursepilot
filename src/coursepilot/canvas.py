from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx

from coursepilot.models import CourseItem, ItemType
from coursepilot.run import FetchResult


class CanvasClient:
    """Fetches assignments and exam calendar events from the Canvas REST API."""

    def __init__(self, *, base_url: str, token: str, course_id: str) -> None:
        self._course_id = course_id
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
        )

    def fetch_course_items(self) -> FetchResult:
        course_code = self._fetch_course_code()
        assignments = self._fetch_assignments(course_code)
        assignment_titles = {item.title for item in assignments}
        exams = self._fetch_exam_calendar_events(course_code, exclude_titles=assignment_titles)
        return FetchResult(course_items=[*assignments, *exams], rejected=[])

    def _fetch_course_code(self) -> str:
        response = self._client.get(f"/api/v1/courses/{self._course_id}")
        response.raise_for_status()
        course_code: str = response.json()["course_code"]
        return course_code

    def _fetch_assignments(self, course_code: str) -> list[CourseItem]:
        raw_assignments = self._paginate(f"/api/v1/courses/{self._course_id}/assignments")
        return _map_to_course_items(
            raw_assignments,
            course_code=course_code,
            title_key="name",
            date_key="due_at",
            item_type_of=_classify_assignment,
        )

    def _fetch_exam_calendar_events(
        self, course_code: str, *, exclude_titles: set[str]
    ) -> list[CourseItem]:
        params = {
            "type": "event",
            "context_codes[]": f"course_{self._course_id}",
        }
        raw_events = self._paginate("/api/v1/calendar_events", params=params)
        raw_events = [event for event in raw_events if event.get("title") not in exclude_titles]
        return _map_to_course_items(
            raw_events,
            course_code=course_code,
            title_key="title",
            date_key="start_at",
            item_type_of=lambda _: "exam",
        )

    def _paginate(
        self, url: str, params: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params: dict[str, str] | None = params
        while next_url is not None:
            response = self._client.get(next_url, params=next_params)
            response.raise_for_status()
            results.extend(response.json())
            next_url = response.links.get("next", {}).get("url")
            next_params = None
        return results


def _map_to_course_items(
    raw_items: list[dict[str, Any]],
    *,
    course_code: str,
    title_key: str,
    date_key: str,
    item_type_of: Callable[[dict[str, Any]], ItemType],
) -> list[CourseItem]:
    items = []
    for raw in raw_items:
        date_value = raw.get(date_key)
        if date_value is None:
            continue
        items.append(
            CourseItem.build(
                course=course_code,
                title=raw[title_key],
                item_type=item_type_of(raw),
                due_date=datetime.fromisoformat(date_value),
                source="canvas",
                source_url=raw["html_url"],
                extraction_confidence="direct",
            )
        )
    return items


def _classify_assignment(assignment: dict[str, Any]) -> ItemType:
    submission_types = assignment.get("submission_types") or []
    if "online_quiz" in submission_types:
        return "quiz"
    return "assignment"
