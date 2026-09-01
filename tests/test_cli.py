from coursepilot.cli import format_summary
from coursepilot.run import RunResult


def test_format_summary_with_some_inserted_and_some_skipped() -> None:
    result = RunResult(total=5, inserted=3, updated=0, archived=0, reactivated=0, skipped=2)

    assert format_summary(result) == "5 items: 3 inserted, 0 updated, 0 archived, 0 reactivated, 2 skipped."


def test_format_summary_with_nothing_new() -> None:
    result = RunResult(total=4, inserted=0, updated=0, archived=0, reactivated=0, skipped=4)

    assert format_summary(result) == "4 items: 0 inserted, 0 updated, 0 archived, 0 reactivated, 4 skipped."


def test_format_summary_with_no_items_at_all() -> None:
    result = RunResult(total=0, inserted=0, updated=0, archived=0, reactivated=0, skipped=0)

    assert format_summary(result) == "0 items: 0 inserted, 0 updated, 0 archived, 0 reactivated, 0 skipped."


def test_format_summary_with_updates_archives_and_reactivations() -> None:
    result = RunResult(total=10, inserted=1, updated=2, archived=3, reactivated=4, skipped=0)

    assert (
        format_summary(result)
        == "10 items: 1 inserted, 2 updated, 3 archived, 4 reactivated, 0 skipped."
    )
