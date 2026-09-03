import httpx


class RawSiteFetcher:
    """Fetches raw HTML from a course website via a plain HTTP GET."""

    def __init__(self) -> None:
        self._client = httpx.Client()

    def fetch(self, url: str) -> str:
        response = self._client.get(url)
        response.raise_for_status()
        return response.text
