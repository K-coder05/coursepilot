from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from coursepilot.models import CourseItem


def make_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = dict(
        course="DATA C104-LEC-001",
        title="Homework 3",
        item_type="assignment",
        due_date=datetime(2026, 9, 15, 23, 59, tzinfo=timezone.utc),
        source="canvas",
        source_url="https://bcourses.berkeley.edu/courses/1/assignments/42",
        extraction_confidence="direct",
    )
    kwargs.update(overrides)
    return kwargs


def test_build_computes_a_stable_id_from_source_and_source_url() -> None:
    item_a = CourseItem.build(**make_kwargs())
    item_b = CourseItem.build(**make_kwargs())

    assert item_a.id == item_b.id
    assert item_a.id != ""


def test_build_id_changes_when_source_url_changes() -> None:
    item_a = CourseItem.build(**make_kwargs())
    item_b = CourseItem.build(
        **make_kwargs(source_url="https://bcourses.berkeley.edu/courses/1/assignments/43")
    )

    assert item_a.id != item_b.id


def test_build_content_hash_stable_for_identical_content() -> None:
    item_a = CourseItem.build(**make_kwargs())
    item_b = CourseItem.build(**make_kwargs())

    assert item_a.content_hash == item_b.content_hash


def test_build_content_hash_changes_when_title_changes() -> None:
    item_a = CourseItem.build(**make_kwargs())
    item_b = CourseItem.build(**make_kwargs(title="Homework 3 (revised)"))

    assert item_a.content_hash != item_b.content_hash


def test_build_content_hash_changes_when_due_date_changes() -> None:
    item_a = CourseItem.build(**make_kwargs())
    item_b = CourseItem.build(
        **make_kwargs(due_date=datetime(2026, 9, 16, 23, 59, tzinfo=timezone.utc))
    )

    assert item_a.content_hash != item_b.content_hash


def test_build_defaults_last_synced_at_to_none() -> None:
    item = CourseItem.build(**make_kwargs())

    assert item.last_synced_at is None


def test_rejects_invalid_item_type() -> None:
    with pytest.raises(ValidationError):
        CourseItem.build(**make_kwargs(item_type="homework"))


def test_rejects_invalid_source() -> None:
    with pytest.raises(ValidationError):
        CourseItem.build(**make_kwargs(source="blackboard"))


def test_rejects_invalid_extraction_confidence() -> None:
    with pytest.raises(ValidationError):
        CourseItem.build(**make_kwargs(extraction_confidence="pretty_sure"))


def test_rejects_naive_due_date() -> None:
    with pytest.raises(ValidationError):
        CourseItem.build(**make_kwargs(due_date=datetime(2026, 9, 15, 23, 59)))
