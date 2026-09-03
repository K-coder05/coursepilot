from dataclasses import dataclass
from datetime import datetime
from typing import cast

from pydantic import ValidationError

from coursepilot.extraction import ExtractedItem
from coursepilot.models import CourseItem, ExtractionConfidence, ItemType


@dataclass(frozen=True)
class RejectedItem:
    title: str
    reason: str


@dataclass(frozen=True)
class ValidationResult:
    items: list[CourseItem]
    rejected: list[RejectedItem]


def validate_extracted_items(
    raw_items: list[ExtractedItem], *, source_url: str
) -> ValidationResult:
    """Convert LLM-extracted items into CourseItems, rejecting invalid ones.

    Rejects items with an unparseable or timezone-naive due date, or any
    other field that fails CourseItem's validation, instead of raising.
    """
    items: list[CourseItem] = []
    rejected: list[RejectedItem] = []

    for raw in raw_items:
        try:
            due_date = datetime.fromisoformat(raw.due_date)
            items.append(
                CourseItem.build(
                    course=raw.course,
                    title=raw.title,
                    item_type=cast(ItemType, raw.item_type),
                    due_date=due_date,
                    source="raw_site",
                    source_url=source_url,
                    extraction_confidence=cast(
                        ExtractionConfidence, raw.extraction_confidence
                    ),
                )
            )
        except (ValueError, ValidationError) as exc:
            rejected.append(RejectedItem(title=raw.title, reason=str(exc)))

    return ValidationResult(items=items, rejected=rejected)
