from dataclasses import dataclass
from typing import Mapping

_REQUIRED_KEYS = (
    "CANVAS_BASE_URL",
    "CANVAS_TOKEN",
    "CANVAS_COURSE_ID",
    "NOTION_TOKEN",
    "NOTION_DATABASE_ID",
)


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
        missing = [key for key in _REQUIRED_KEYS if not env.get(key)]
        if missing:
            raise ValueError(f"Missing required environment variable(s): {', '.join(missing)}")
        return cls(
            canvas_base_url=env["CANVAS_BASE_URL"],
            canvas_token=env["CANVAS_TOKEN"],
            canvas_course_id=env["CANVAS_COURSE_ID"],
            notion_token=env["NOTION_TOKEN"],
            notion_database_id=env["NOTION_DATABASE_ID"],
            db_path=env.get("COURSEPILOT_DB_PATH", "coursepilot.db"),
        )
