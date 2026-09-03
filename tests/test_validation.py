from coursepilot.extraction import ExtractedItem
from coursepilot.validation import validate_extracted_items

SOURCE_URL = "https://cs162.org/assignments"


def make_extracted(**overrides: object) -> ExtractedItem:
    fields: dict[str, object] = dict(
        title="Homework 3",
        item_type="assignment",
        due_date="2026-09-15T23:59:00-07:00",
        course="CS 162",
        extraction_confidence="llm_high",
    )
    fields.update(overrides)
    return ExtractedItem(**fields)  # type: ignore[arg-type]


def test_valid_item_is_converted_to_a_course_item() -> None:
    result = validate_extracted_items([make_extracted()], source_url=SOURCE_URL)

    assert result.rejected == []
    assert len(result.items) == 1
    item = result.items[0]
    assert item.title == "Homework 3"
    assert item.course == "CS 162"
    assert item.item_type == "assignment"
    assert item.source == "raw_site"
    assert item.source_url == SOURCE_URL
    assert item.extraction_confidence == "llm_high"


def test_unparseable_due_date_is_rejected_with_a_reason() -> None:
    result = validate_extracted_items(
        [make_extracted(due_date="next friday")], source_url=SOURCE_URL
    )

    assert result.items == []
    assert len(result.rejected) == 1
    assert result.rejected[0].title == "Homework 3"
    assert result.rejected[0].reason


def test_missing_due_date_is_rejected_without_crashing() -> None:
    result = validate_extracted_items([make_extracted(due_date="")], source_url=SOURCE_URL)

    assert result.items == []
    assert len(result.rejected) == 1
    assert result.rejected[0].title == "Homework 3"


def test_timezone_naive_due_date_is_rejected() -> None:
    result = validate_extracted_items(
        [make_extracted(due_date="2026-09-15T23:59:00")], source_url=SOURCE_URL
    )

    assert result.items == []
    assert len(result.rejected) == 1


def test_invalid_item_type_is_rejected() -> None:
    result = validate_extracted_items(
        [make_extracted(item_type="homework")], source_url=SOURCE_URL
    )

    assert result.items == []
    assert len(result.rejected) == 1


def test_invalid_extraction_confidence_is_rejected() -> None:
    result = validate_extracted_items(
        [make_extracted(extraction_confidence="pretty_sure")], source_url=SOURCE_URL
    )

    assert result.items == []
    assert len(result.rejected) == 1


def test_valid_and_invalid_items_are_both_reported() -> None:
    valid = make_extracted()
    invalid = make_extracted(title="Bad Date Item", due_date="whenever")

    result = validate_extracted_items([valid, invalid], source_url=SOURCE_URL)

    assert len(result.items) == 1
    assert result.items[0].title == "Homework 3"
    assert len(result.rejected) == 1
    assert result.rejected[0].title == "Bad Date Item"


def test_no_items_produces_empty_result() -> None:
    result = validate_extracted_items([], source_url=SOURCE_URL)

    assert result.items == []
    assert result.rejected == []
