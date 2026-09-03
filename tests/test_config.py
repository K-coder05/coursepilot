import pytest

from coursepilot.config import Config, RawSiteConfig

RAW_SITE_ENV = {
    "RAW_SITE_URL": "https://cs162.org/assignments",
    "ANTHROPIC_API_KEY": "sk-ant-test",
}

REQUIRED_ENV = {
    "CANVAS_BASE_URL": "https://bcourses.berkeley.edu",
    "CANVAS_TOKEN": "canvas-token-abc",
    "CANVAS_COURSE_ID": "12345",
    "NOTION_TOKEN": "notion-token-xyz",
    "NOTION_DATABASE_ID": "db-abc-123",
    "TIMEZONE": "America/Los_Angeles",
    **RAW_SITE_ENV,
}


def test_from_env_builds_config_from_all_required_vars() -> None:
    config = Config.from_env(REQUIRED_ENV)

    assert config.canvas_base_url == "https://bcourses.berkeley.edu"
    assert config.canvas_token == "canvas-token-abc"
    assert config.canvas_course_id == "12345"
    assert config.notion_token == "notion-token-xyz"
    assert config.notion_database_id == "db-abc-123"
    assert config.raw_site_url == "https://cs162.org/assignments"
    assert config.anthropic_api_key == "sk-ant-test"
    assert config.timezone == "America/Los_Angeles"
    assert config.db_path == "coursepilot.db"


def test_from_env_honors_optional_db_path_override() -> None:
    env = {**REQUIRED_ENV, "COURSEPILOT_DB_PATH": "/tmp/custom.db"}

    config = Config.from_env(env)

    assert config.db_path == "/tmp/custom.db"


@pytest.mark.parametrize("missing_key", list(REQUIRED_ENV))
def test_from_env_raises_a_clear_error_when_a_required_var_is_missing(
    missing_key: str,
) -> None:
    env = {k: v for k, v in REQUIRED_ENV.items() if k != missing_key}

    with pytest.raises(ValueError, match=missing_key):
        Config.from_env(env)


def test_raw_site_config_from_env_builds_from_its_own_vars_only() -> None:
    config = RawSiteConfig.from_env(RAW_SITE_ENV)

    assert config.raw_site_url == "https://cs162.org/assignments"
    assert config.anthropic_api_key == "sk-ant-test"


@pytest.mark.parametrize("missing_key", list(RAW_SITE_ENV))
def test_raw_site_config_from_env_raises_a_clear_error_when_a_required_var_is_missing(
    missing_key: str,
) -> None:
    env = {k: v for k, v in RAW_SITE_ENV.items() if k != missing_key}

    with pytest.raises(ValueError, match=missing_key):
        RawSiteConfig.from_env(env)
