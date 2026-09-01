from coursepilot.cli import format_summary
from coursepilot.run import RunResult


def test_format_summary_with_some_inserted_and_some_skipped() -> None:
    result = RunResult(total=5, inserted=3, skipped=2)

    assert format_summary(result) == "Inserted 3 of 5 items (2 already synced)."


def test_format_summary_with_nothing_new() -> None:
    result = RunResult(total=4, inserted=0, skipped=4)

    assert format_summary(result) == "Inserted 0 of 4 items (4 already synced)."


def test_format_summary_with_no_items_at_all() -> None:
    result = RunResult(total=0, inserted=0, skipped=0)

    assert format_summary(result) == "Inserted 0 of 0 items (0 already synced)."
