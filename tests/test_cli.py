from datetime import datetime, timezone

from coursepilot.cli import format_dry_run_report, format_summary
from coursepilot.dry_run import DryRunResult
from coursepilot.models import CourseItem
from coursepilot.run import ItemChange, RunResult
from coursepilot.validation import RejectedItem


def test_format_summary_with_some_inserted_and_some_skipped() -> None:
    result = RunResult(
        total=5, inserted=3, updated=0, archived=0, reactivated=0, skipped=2, rejected=[]
    )

    assert format_summary(result) == "5 items: 3 inserted, 0 updated, 0 archived, 0 reactivated, 2 skipped."


def test_format_summary_with_nothing_new() -> None:
    result = RunResult(
        total=4, inserted=0, updated=0, archived=0, reactivated=0, skipped=4, rejected=[]
    )

    assert format_summary(result) == "4 items: 0 inserted, 0 updated, 0 archived, 0 reactivated, 4 skipped."


def test_format_summary_with_no_items_at_all() -> None:
    result = RunResult(
        total=0, inserted=0, updated=0, archived=0, reactivated=0, skipped=0, rejected=[]
    )

    assert format_summary(result) == "0 items: 0 inserted, 0 updated, 0 archived, 0 reactivated, 0 skipped."


def test_format_summary_with_updates_archives_and_reactivations() -> None:
    result = RunResult(
        total=10, inserted=1, updated=2, archived=3, reactivated=4, skipped=0, rejected=[]
    )

    assert (
        format_summary(result)
        == "10 items: 1 inserted, 2 updated, 3 archived, 4 reactivated, 0 skipped."
    )


def test_format_summary_lists_rejected_items_with_reasons() -> None:
    result = RunResult(
        total=1,
        inserted=0,
        updated=0,
        archived=0,
        reactivated=0,
        skipped=0,
        rejected=[RejectedItem(title="Bad Item", reason="unparseable date")],
    )

    report = format_summary(result)

    assert report.startswith("1 items: 0 inserted, 0 updated, 0 archived, 0 reactivated, 0 skipped.")
    assert "Rejected 1 item(s):" in report
    assert "Bad Item: unparseable date" in report


def test_format_summary_lists_one_line_per_changed_item() -> None:
    inserted_item = CourseItem.build(
        course="CS 162",
        title="Homework 3",
        item_type="assignment",
        due_date=datetime(2026, 9, 15, 23, 59, tzinfo=timezone.utc),
        source="raw_site",
        source_url="https://cs162.org/assignments",
        extraction_confidence="llm_high",
    )
    archived_item = CourseItem.build(
        course="DATA C104-LEC-001",
        title="Homework 2",
        item_type="assignment",
        due_date=datetime(2026, 9, 10, 23, 59, tzinfo=timezone.utc),
        source="canvas",
        source_url="https://bcourses.berkeley.edu/courses/1/assignments/2",
        extraction_confidence="direct",
    )
    result = RunResult(
        total=2,
        inserted=1,
        updated=0,
        archived=1,
        reactivated=0,
        skipped=0,
        rejected=[],
        changes=[
            ItemChange(action="inserted", item=inserted_item),
            ItemChange(action="archived", item=archived_item),
        ],
    )

    report = format_summary(result)

    assert (
        "  - [inserted] Homework 3 (CS 162) due 2026-09-15T23:59:00+00:00" in report
    )
    assert (
        "  - [archived] Homework 2 (DATA C104-LEC-001) due 2026-09-10T23:59:00+00:00"
        in report
    )


def test_format_summary_has_no_change_lines_when_nothing_changed() -> None:
    result = RunResult(
        total=1, inserted=0, updated=0, archived=0, reactivated=0, skipped=1, rejected=[]
    )

    report = format_summary(result)

    assert report == "1 items: 0 inserted, 0 updated, 0 archived, 0 reactivated, 1 skipped."


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
