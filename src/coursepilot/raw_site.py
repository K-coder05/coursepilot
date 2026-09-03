from dataclasses import dataclass
from typing import Protocol

import httpx

from coursepilot.extraction import ExtractedItem
from coursepilot.models import CourseItem
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

    Items that fail validation are dropped rather than surfaced -- run() has no
    rejected-item report; that's only available through the dry-run command.
    """

    fetcher: HtmlFetcher
    extractor: ItemExtractor
    url: str

    def fetch_course_items(self) -> list[CourseItem]:
        return fetch_and_validate(fetcher=self.fetcher, extractor=self.extractor, url=self.url).items
