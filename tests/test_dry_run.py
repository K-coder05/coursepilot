from coursepilot.dry_run import dry_run
from coursepilot.extraction import ExtractedItem

URL = "https://cs162.org/assignments"


class FakeFetcher:
    def __init__(self, html: str) -> None:
        self._html = html

    def fetch(self, url: str) -> str:
        assert url == URL
        return self._html


class FakeExtractor:
    def __init__(self, items: list[ExtractedItem]) -> None:
        self._items = items
        self.received_html: str | None = None

    def extract(self, html: str) -> list[ExtractedItem]:
        self.received_html = html
        return self._items


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


def test_dry_run_passes_fetched_html_to_the_extractor() -> None:
    fetcher = FakeFetcher("<html>content</html>")
    extractor = FakeExtractor([])

    dry_run(fetcher=fetcher, extractor=extractor, url=URL)

    assert extractor.received_html == "<html>content</html>"


def test_dry_run_reports_valid_items_as_would_create() -> None:
    fetcher = FakeFetcher("<html></html>")
    extractor = FakeExtractor([make_extracted()])

    result = dry_run(fetcher=fetcher, extractor=extractor, url=URL)

    assert len(result.would_create) == 1
    assert result.would_create[0].title == "Homework 3"
    assert result.would_create[0].source_url == URL
    assert result.rejected == []


def test_dry_run_reports_invalid_items_as_rejected() -> None:
    fetcher = FakeFetcher("<html></html>")
    extractor = FakeExtractor([make_extracted(due_date="not a date")])

    result = dry_run(fetcher=fetcher, extractor=extractor, url=URL)

    assert result.would_create == []
    assert len(result.rejected) == 1
    assert result.rejected[0].title == "Homework 3"


def test_dry_run_never_writes_anywhere_it_only_returns_a_result() -> None:
    fetcher = FakeFetcher("<html></html>")
    extractor = FakeExtractor([make_extracted(), make_extracted(title="Bad", due_date="bad")])

    result = dry_run(fetcher=fetcher, extractor=extractor, url=URL)

    assert len(result.would_create) == 1
    assert len(result.rejected) == 1
