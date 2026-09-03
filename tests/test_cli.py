from datetime import datetime, timezone

from coursepilot.cli import format_dry_run_report, format_summary
from coursepilot.dry_run import DryRunResult
from coursepilot.models import CourseItem
from coursepilot.run import RunResult
from coursepilot.validation import RejectedItem


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


def make_item() -> CourseItem:
    return CourseItem.build(
        course="CS 162",
        title="Homework 3",
        item_type="assignment",
        due_date=datetime(2026, 9, 15, 23, 59, tzinfo=timezone.utc),
        source="raw_site",
        source_url="https://cs162.org/assignments",
        extraction_confidence="llm_high",
    )


def test_format_dry_run_report_with_no_items() -> None:
    result = DryRunResult(would_create=[], rejected=[])

    report = format_dry_run_report(result)

    assert report == "Would create 0 item(s):\nRejected 0 item(s):"


def test_format_dry_run_report_lists_items_that_would_be_created() -> None:
    result = DryRunResult(would_create=[make_item()], rejected=[])

    report = format_dry_run_report(result)

    assert "Would create 1 item(s):" in report
    assert (
        "[assignment] Homework 3 (CS 162) due 2026-09-15T23:59:00+00:00 [llm_high]" in report
    )


def test_format_dry_run_report_lists_rejected_items_with_reasons() -> None:
    result = DryRunResult(
        would_create=[],
        rejected=[RejectedItem(title="Bad Item", reason="unparseable date")],
    )

    report = format_dry_run_report(result)

    assert "Rejected 1 item(s):" in report
    assert "Bad Item: unparseable date" in report
