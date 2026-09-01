from datetime import datetime
from typing import Any

import httpx

from coursepilot.models import CourseItem, ItemType


class CanvasClient:
    """Fetches assignments and exam calendar events from the Canvas REST API."""

    def __init__(self, *, base_url: str, token: str, course_id: str) -> None:
        self._course_id = course_id
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
        )

    def fetch_course_items(self) -> list[CourseItem]:
        course_code = self._fetch_course_code()
        items = [
            *self._fetch_assignments(course_code),
            *self._fetch_exam_calendar_events(course_code),
        ]
        return items

    def _fetch_course_code(self) -> str:
        response = self._client.get(f"/api/v1/courses/{self._course_id}")
        response.raise_for_status()
        course_code: str = response.json()["course_code"]
        return course_code

    def _fetch_assignments(self, course_code: str) -> list[CourseItem]:
        items = []
        for assignment in self._paginate(f"/api/v1/courses/{self._course_id}/assignments"):
            due_at = assignment.get("due_at")
            if due_at is None:
                continue
            items.append(
                CourseItem.build(
                    course=course_code,
                    title=assignment["name"],
                    item_type=_classify_assignment(assignment),
                    due_date=datetime.fromisoformat(due_at),
                    source="canvas",
                    source_url=assignment["html_url"],
                    extraction_confidence="direct",
                )
            )
        return items

    def _fetch_exam_calendar_events(self, course_code: str) -> list[CourseItem]:
        items = []
        params = {
            "type": "event",
            "context_codes[]": f"course_{self._course_id}",
        }
        for event in self._paginate("/api/v1/calendar_events", params=params):
            start_at = event.get("start_at")
            if start_at is None:
                continue
            items.append(
                CourseItem.build(
                    course=course_code,
                    title=event["title"],
                    item_type="exam",
                    due_date=datetime.fromisoformat(start_at),
                    source="canvas",
                    source_url=event["html_url"],
                    extraction_confidence="direct",
                )
            )
        return items

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


def _classify_assignment(assignment: dict[str, Any]) -> ItemType:
    submission_types = assignment.get("submission_types") or []
    if "online_quiz" in submission_types:
        return "quiz"
    if "exam" in assignment["name"].lower():
        return "exam"
    return "assignment"
