import os

import typer
from dotenv import load_dotenv

from coursepilot.canvas import CanvasClient
from coursepilot.config import Config
from coursepilot.notion import NotionClient
from coursepilot.run import RunResult
from coursepilot.run import run as run_pipeline
from coursepilot.store import Store

app = typer.Typer()


def format_summary(result: RunResult) -> str:
    return f"Inserted {result.inserted} of {result.total} items ({result.skipped} already synced)."


@app.command()
def run() -> None:
    """Fetch Canvas assignments/exams and insert any new ones into Notion."""
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
    notion_client = NotionClient(
        token=config.notion_token, database_id=config.notion_database_id
    )
    store = Store(config.db_path)

    result = run_pipeline(canvas_client=canvas_client, store=store, notion_client=notion_client)
    typer.echo(format_summary(result))


if __name__ == "__main__":
    app()
