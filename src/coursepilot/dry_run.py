from dataclasses import dataclass
from typing import Protocol

from coursepilot.extraction import ExtractedItem
from coursepilot.models import CourseItem
from coursepilot.validation import RejectedItem, validate_extracted_items


class HtmlFetcher(Protocol):
    def fetch(self, url: str) -> str: ...


class ItemExtractor(Protocol):
    def extract(self, html: str) -> list[ExtractedItem]: ...


@dataclass(frozen=True)
class DryRunResult:
    would_create: list[CourseItem]
    rejected: list[RejectedItem]


def dry_run(*, fetcher: HtmlFetcher, extractor: ItemExtractor, url: str) -> DryRunResult:
    """Fetch, extract, and validate a raw course site without writing anywhere."""
    html = fetcher.fetch(url)
    raw_items = extractor.extract(html)
    result = validate_extracted_items(raw_items, source_url=url)
    return DryRunResult(would_create=result.items, rejected=result.rejected)
