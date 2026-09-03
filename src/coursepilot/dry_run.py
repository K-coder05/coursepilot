from dataclasses import dataclass

from coursepilot.models import CourseItem
from coursepilot.raw_site import HtmlFetcher, ItemExtractor, fetch_and_validate
from coursepilot.validation import RejectedItem


@dataclass(frozen=True)
class DryRunResult:
    would_create: list[CourseItem]
    rejected: list[RejectedItem]


def dry_run(*, fetcher: HtmlFetcher, extractor: ItemExtractor, url: str) -> DryRunResult:
    """Fetch, extract, and validate a raw course site without writing anywhere."""
    result = fetch_and_validate(fetcher=fetcher, extractor=extractor, url=url)
    return DryRunResult(would_create=result.items, rejected=result.rejected)
