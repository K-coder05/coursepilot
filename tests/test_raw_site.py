import httpx
import respx

from coursepilot.extraction import ExtractedItem
from coursepilot.raw_site import RawSiteFetcher, RawSiteSource

URL = "https://cs162.org/assignments"


@respx.mock
def test_fetch_returns_the_response_body_as_text() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, text="<html>hello</html>"))

    html = RawSiteFetcher().fetch(URL)

    assert html == "<html>hello</html>"


@respx.mock
def test_fetch_raises_on_a_non_2xx_response() -> None:
    respx.get(URL).mock(return_value=httpx.Response(404, text="not found"))

    try:
        RawSiteFetcher().fetch(URL)
    except httpx.HTTPStatusError:
        pass
    else:
        raise AssertionError("expected HTTPStatusError")


class FakeFetcher:
    def __init__(self, html: str) -> None:
        self._html = html

    def fetch(self, url: str) -> str:
        assert url == URL
        return self._html


class FakeExtractor:
    def __init__(self, items: list[ExtractedItem]) -> None:
        self._items = items

    def extract(self, html: str) -> list[ExtractedItem]:
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


def test_raw_site_source_fetch_course_items_returns_validated_items() -> None:
    source = RawSiteSource(
        fetcher=FakeFetcher("<html></html>"),
        extractor=FakeExtractor([make_extracted()]),
        url=URL,
    )

    result = source.fetch_course_items()

    assert len(result.course_items) == 1
    assert result.course_items[0].title == "Homework 3"
    assert result.course_items[0].source == "raw_site"
    assert result.course_items[0].source_url == URL
    assert result.rejected == []


def test_raw_site_source_reports_items_that_fail_validation_as_rejected() -> None:
    source = RawSiteSource(
        fetcher=FakeFetcher("<html></html>"),
        extractor=FakeExtractor([make_extracted(due_date="not a date")]),
        url=URL,
    )

    result = source.fetch_course_items()

    assert result.course_items == []
    assert len(result.rejected) == 1
    assert result.rejected[0].title == "Homework 3"
