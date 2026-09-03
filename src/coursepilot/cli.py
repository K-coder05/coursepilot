import os

import typer
from dotenv import load_dotenv

from coursepilot.canvas import CanvasClient
from coursepilot.config import Config, RawSiteConfig
from coursepilot.dry_run import DryRunResult
from coursepilot.dry_run import dry_run as dry_run_pipeline
from coursepilot.extraction import LLMExtractor
from coursepilot.notion import NotionClient
from coursepilot.raw_site import RawSiteFetcher, RawSiteSource
from coursepilot.run import ItemChange, RunResult
from coursepilot.run import run as run_pipeline
from coursepilot.store import Store
from coursepilot.validation import RejectedItem

app = typer.Typer()


def _format_rejected_lines(rejected: list[RejectedItem]) -> list[str]:
    lines = [f"Rejected {len(rejected)} item(s):"]
    for item in rejected:
        lines.append(f"  - {item.title}: {item.reason}")
    return lines


def _format_change_lines(changes: list[ItemChange]) -> list[str]:
    return [
        f"  - [{change.action}] {change.item.title} ({change.item.course}) "
        f"due {change.item.due_date.isoformat()}"
        for change in changes
    ]


def format_summary(result: RunResult) -> str:
    lines = [
        f"{result.total} items: {result.inserted} inserted, {result.updated} updated, "
        f"{result.archived} archived, {result.reactivated} reactivated, "
        f"{result.skipped} skipped."
    ]
    lines.extend(_format_change_lines(result.changes))
    if result.rejected:
        lines.extend(_format_rejected_lines(result.rejected))
    return "\n".join(lines)


def format_dry_run_report(result: DryRunResult) -> str:
    """Plain-text report of items that would be created plus rejected items with reasons."""
    lines = [f"Would create {len(result.would_create)} item(s):"]
    for item in result.would_create:
        lines.append(
            f"  - [{item.item_type}] {item.title} ({item.course}) due "
            f"{item.due_date.isoformat()} [{item.extraction_confidence}]"
        )
    lines.extend(_format_rejected_lines(result.rejected))
    return "\n".join(lines)


@app.command()
def run() -> None:
    """Fetch Canvas and raw-site items and sync any changes into Notion."""
    load_dotenv()
    try:
        config = Config.from_env(os.environ)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    canvas_client = CanvasClient(
        base_url=config.canvas_base_url,
        token=config.canvas_token,
        course_id=config.canvas_course_id,
    )
    raw_site_source = RawSiteSource(
        fetcher=RawSiteFetcher(),
        extractor=LLMExtractor(api_key=config.anthropic_api_key),
        url=config.raw_site_url,
    )
    notion_client = NotionClient(
        token=config.notion_token, database_id=config.notion_database_id
    )
    store = Store(config.db_path)

    result = run_pipeline(
        sources={"canvas": canvas_client, "raw_site": raw_site_source},
        store=store,
        notion_client=notion_client,
    )
    typer.echo(format_summary(result))


@app.command(name="dry-run")
def dry_run() -> None:
    """Fetch, extract, and validate the raw course site without writing anywhere."""
    load_dotenv()
    try:
        config = RawSiteConfig.from_env(os.environ)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    fetcher = RawSiteFetcher()
    extractor = LLMExtractor(api_key=config.anthropic_api_key)

    result = dry_run_pipeline(fetcher=fetcher, extractor=extractor, url=config.raw_site_url)
    typer.echo(format_dry_run_report(result))


if __name__ == "__main__":
    app()
