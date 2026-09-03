import httpx
import respx

from coursepilot.raw_site import RawSiteFetcher

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
