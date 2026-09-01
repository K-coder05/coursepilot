import hashlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

ItemType = Literal["assignment", "exam", "quiz", "other"]
Source = Literal["canvas", "raw_site", "gradescope"]
ExtractionConfidence = Literal["direct", "llm_high", "llm_needs_review"]


class CourseItem(BaseModel):
    """The unified record every source's raw data is normalized into."""

    id: str
    course: str
    title: str
    item_type: ItemType
    due_date: datetime
    source: Source
    source_url: str
    content_hash: str
    last_synced_at: datetime | None = None
    extraction_confidence: ExtractionConfidence

    @field_validator("due_date", "last_synced_at")
    @classmethod
    def _require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return value

    @classmethod
    def build(
        cls,
        *,
        course: str,
        title: str,
        item_type: ItemType,
        due_date: datetime,
        source: Source,
        source_url: str,
        extraction_confidence: ExtractionConfidence,
    ) -> "CourseItem":
        """Construct a CourseItem, deriving its stable `id` and `content_hash`."""
        return cls(
            id=_compute_id(source, source_url),
            course=course,
            title=title,
            item_type=item_type,
            due_date=due_date,
            source=source,
            source_url=source_url,
            content_hash=_compute_content_hash(title, item_type, due_date),
            last_synced_at=None,
            extraction_confidence=extraction_confidence,
        )


def _compute_id(source: str, source_url: str) -> str:
    return hashlib.sha256(f"{source}:{source_url}".encode()).hexdigest()


def _compute_content_hash(title: str, item_type: str, due_date: datetime) -> str:
    return hashlib.sha256(
        f"{title}:{item_type}:{due_date.isoformat()}".encode()
    ).hexdigest()
