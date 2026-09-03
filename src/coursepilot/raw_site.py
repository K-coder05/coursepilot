from dataclasses import dataclass
from typing import Protocol

import httpx

from coursepilot.extraction import ExtractedItem
from coursepilot.run import FetchResult
from coursepilot.validation import ValidationResult, validate_extracted_items


class RawSiteFetcher:
    """Fetches raw HTML from a course website via a plain HTTP GET."""

    def __init__(self) -> None:
        self._client = httpx.Client()

    def fetch(self, url: str) -> str:
        response = self._client.get(url)
        response.raise_for_status()
        return response.text


class HtmlFetcher(Protocol):
    def fetch(self, url: str) -> str: ...


class ItemExtractor(Protocol):
    def extract(self, html: str) -> list[ExtractedItem]: ...


def fetch_and_validate(*, fetcher: HtmlFetcher, extractor: ItemExtractor, url: str) -> ValidationResult:
    """Fetch raw HTML, extract candidate items, and validate them into CourseItems."""
    html = fetcher.fetch(url)
    raw_items = extractor.extract(html)
    return validate_extracted_items(raw_items, source_url=url)


@dataclass(frozen=True)
class RawSiteSource:
    """Adapts the raw-site fetch/extract/validate pipeline to the CourseItemSource
    protocol, so raw-site items flow through the exact same sync engine as Canvas.

    Items that fail validation are reported back to run() as rejected rather than
    dropped, so they still surface in the CLI run summary even though they're
    never written to Notion.
    """

    fetcher: HtmlFetcher
    extractor: ItemExtractor
    url: str

    def fetch_course_items(self) -> FetchResult:
        result = fetch_and_validate(fetcher=self.fetcher, extractor=self.extractor, url=self.url)
        return FetchResult(course_items=result.items, rejected=result.rejected)
