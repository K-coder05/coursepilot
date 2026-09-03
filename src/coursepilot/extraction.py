from typing import Any, cast

import anthropic
from anthropic.types import ToolParam, ToolUseBlock
from pydantic import BaseModel

_MODEL = "claude-opus-4-8"

_TOOL_NAME = "extract_course_items"

_ITEM_FIELDS = ("title", "item_type", "due_date", "course", "extraction_confidence")

_SYSTEM_PROMPT = (
    "You extract assignments, exams, and quizzes from the HTML of a course "
    "website. For each item found, report its title, type, due date, and "
    "the course it belongs to. Due dates must be ISO 8601 with an explicit "
    "UTC offset (e.g. 2026-09-15T23:59:00-07:00); if the page gives no "
    "timezone, use the course's stated timezone. Set extraction_confidence "
    "to \"llm_high\" when the item and its due date are unambiguous, and "
    "\"llm_needs_review\" when either is inferred or uncertain. Only report "
    "items that are actually due assignments, exams, or quizzes — skip "
    "announcements, readings without a due date, and navigation content."
)

_TOOL: ToolParam = {
    "name": _TOOL_NAME,
    "description": "Report the assignments, exams, and quizzes found on a course page.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "item_type": {
                            "type": "string",
                            "enum": ["assignment", "exam", "quiz", "other"],
                        },
                        "due_date": {
                            "type": "string",
                            "description": "ISO 8601 datetime with a UTC offset",
                        },
                        "course": {"type": "string"},
                        "extraction_confidence": {
                            "type": "string",
                            "enum": ["llm_high", "llm_needs_review"],
                        },
                    },
                    "required": [
                        "title",
                        "item_type",
                        "due_date",
                        "course",
                        "extraction_confidence",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    },
}


class ExtractedItem(BaseModel):
    """One LLM-extracted item, not yet validated into a CourseItem."""

    title: str
    item_type: str
    due_date: str
    course: str
    extraction_confidence: str


class ExtractionError(RuntimeError):
    """Raised when the model declines or fails to return the forced extraction tool call."""


class LLMExtractor:
    """Extracts CourseItem candidates from raw course-site HTML via forced tool use."""

    def __init__(self, *, api_key: str, client: anthropic.Anthropic | None = None) -> None:
        self._client = client or anthropic.Anthropic(api_key=api_key)

    def extract(self, html: str) -> list[ExtractedItem]:
        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[{"role": "user", "content": html}],
        )
        tool_use = next(
            (block for block in response.content if isinstance(block, ToolUseBlock)), None
        )
        if tool_use is None:
            raise ExtractionError(
                f"Model did not return the {_TOOL_NAME} tool call "
                f"(stop_reason={response.stop_reason!r})"
            )
        raw_items = cast(list[dict[str, Any]], tool_use.input["items"])
        # Default a missing field to "" instead of letting ExtractedItem(**item) raise --
        # a field the model dropped despite the strict schema must still surface as a
        # rejected item downstream, not crash the whole extraction call.
        return [
            ExtractedItem(**{field: item.get(field, "") for field in _ITEM_FIELDS})
            for item in raw_items
        ]
