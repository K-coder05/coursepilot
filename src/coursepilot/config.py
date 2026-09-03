from dataclasses import dataclass
from typing import Mapping

_REQUIRED_KEYS = (
    "CANVAS_BASE_URL",
    "CANVAS_TOKEN",
    "CANVAS_COURSE_ID",
    "NOTION_TOKEN",
    "NOTION_DATABASE_ID",
)

_RAW_SITE_REQUIRED_KEYS = ("RAW_SITE_URL", "ANTHROPIC_API_KEY")


def _require(env: Mapping[str, str], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if not env.get(key)]
    if missing:
        raise ValueError(f"Missing required environment variable(s): {', '.join(missing)}")


@dataclass(frozen=True)
class Config:
    canvas_base_url: str
    canvas_token: str
    canvas_course_id: str
    notion_token: str
    notion_database_id: str
    db_path: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Config":
        _require(env, _REQUIRED_KEYS)
        return cls(
            canvas_base_url=env["CANVAS_BASE_URL"],
            canvas_token=env["CANVAS_TOKEN"],
            canvas_course_id=env["CANVAS_COURSE_ID"],
            notion_token=env["NOTION_TOKEN"],
            notion_database_id=env["NOTION_DATABASE_ID"],
            db_path=env.get("COURSEPILOT_DB_PATH", "coursepilot.db"),
        )


@dataclass(frozen=True)
class RawSiteConfig:
    """Env-derived settings for the raw-site dry-run command.

    Kept separate from `Config` so `dry-run` never requires unrelated
    Canvas/Notion credentials.
    """

    raw_site_url: str
    anthropic_api_key: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "RawSiteConfig":
        _require(env, _RAW_SITE_REQUIRED_KEYS)
        return cls(
            raw_site_url=env["RAW_SITE_URL"],
            anthropic_api_key=env["ANTHROPIC_API_KEY"],
        )
