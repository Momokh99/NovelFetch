"""Tests for core.http_client's parsing + error-wording helpers.

Offline: HTTP is exercised through httpx.MockTransport, never the network.
"""

import asyncio

import httpx
import pytest
from bs4 import BeautifulSoup

from core.http_client import HTML_PARSER, describe_error, fetch_soup, parse_html
from sources.scriblehub import ScribbleHubSource
from sources.wuxiaspot import WuxiaSpotSource

ROW_HTML = """
<div class="fiction-list-item row">
  <h2 class="fiction-title">
    <a class="font-red-sunglo bold" href="/fiction/111/one">One</a>
  </h2>
  <img data-type="cover" src="/covers/one.jpg">
</div>
<div class="fiction-list-item row">
  <h2 class="fiction-title">
    <a class="font-red-sunglo bold" href="/fiction/222/two">Two</a>
  </h2>
</div>
"""


def _lxml_available() -> bool:
    try:
        BeautifulSoup("", "lxml")
    except Exception:
        return False
    return True


# ---- parser selection ----------------------------------------------------


def test_html_parser_is_a_known_bs4_builder():
    assert HTML_PARSER in ("lxml", "html.parser")


def test_lxml_is_selected_when_available():
    if not _lxml_available():
        pytest.skip("lxml not installed")
    assert HTML_PARSER == "lxml"


def test_parsers_agree_on_extract_novel_rows():
    """lxml must not change what the scrapers see versus html.parser."""
    if not _lxml_available():
        pytest.skip("lxml not installed")
    from sources import REGISTRY

    src = REGISTRY["royalroad"]
    via_lxml = src.extract_novel_rows(BeautifulSoup(ROW_HTML, "lxml"))
    via_stdlib = src.extract_novel_rows(BeautifulSoup(ROW_HTML, "html.parser"))
    assert via_lxml == via_stdlib
    assert len(via_lxml) == 2


def test_parsers_agree_on_malformed_markup():
    """Unclosed tags are where lxml and html.parser most often diverge."""
    if not _lxml_available():
        pytest.skip("lxml not installed")
    broken = "<div class='fiction-list-item row'><p>alpha <b>beta</div>"
    lxml_text = BeautifulSoup(broken, "lxml").select_one("p").get_text()
    std_text = BeautifulSoup(broken, "html.parser").select_one("p").get_text()
    assert lxml_text == std_text == "alpha beta"


# ---- parse_html ----------------------------------------------------------


def test_parse_html_returns_soup():
    soup = asyncio.run(parse_html('<p class="x">hello</p>'))
    assert isinstance(soup, BeautifulSoup)
    assert soup.select_one("p.x").get_text() == "hello"


def test_parse_html_uses_detected_parser():
    soup = asyncio.run(parse_html("<p>hi</p>"))
    assert soup.builder.NAME in ("lxml", "html.parser", "lxml-xml")


# ---- fetch_soup ----------------------------------------------------------


def _mock_client(handler):
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.test"
    )


@pytest.fixture(autouse=True)
def retry_sleeps(monkeypatch):
    """Record retry backoff instead of actually sleeping.

    Autouse so every test in this module stays instant, including the ones
    below that deliberately exhaust their attempts.
    """
    sleeps: list[float] = []

    async def _record(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("core.http_client._sleep", _record)
    return sleeps


def test_fetch_soup_parses_200():
    def handler(request):
        return httpx.Response(200, text='<p id="ok">hello</p>')

    async def run():
        async with _mock_client(handler) as client:
            return await fetch_soup(client, "/page")

    soup = asyncio.run(run())
    assert soup.select_one("p#ok").get_text() == "hello"


def test_fetch_soup_raises_on_404():
    def handler(request):
        return httpx.Response(404, text="gone")

    async def run():
        async with _mock_client(handler) as client:
            await fetch_soup(client, "/missing")

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        asyncio.run(run())
    assert excinfo.value.response.status_code == 404


def test_fetch_soup_retries_transient_status_then_succeeds(retry_sleeps):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, text='<p id="ok">recovered</p>')

    async def run():
        async with _mock_client(handler) as client:
            return await fetch_soup(client, "/page")

    soup = asyncio.run(run())
    assert calls["n"] == 3
    assert retry_sleeps == [1.0, 2.0]
    assert soup.select_one("p#ok").get_text() == "recovered"


def test_fetch_soup_honors_retry_after(retry_sleeps):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429, text="rate limited", headers={"Retry-After": "3"}
            )
        return httpx.Response(200, text='<p id="ok">ok</p>')

    async def run():
        async with _mock_client(handler) as client:
            return await fetch_soup(client, "/page")

    asyncio.run(run())
    assert retry_sleeps == [3.0]


def test_fetch_soup_caps_an_absurd_retry_after(retry_sleeps):
    """A 10-minute Retry-After would eat async_loop.run's whole 30s timeout."""
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, text="slow down", headers={"Retry-After": "600"})
        return httpx.Response(200, text='<p id="ok">ok</p>')

    async def run():
        async with _mock_client(handler) as client:
            return await fetch_soup(client, "/page")

    asyncio.run(run())
    assert retry_sleeps == [8.0]


def test_fetch_soup_raises_once_attempts_are_spent(retry_sleeps):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503, text="down")

    async def run():
        async with _mock_client(handler) as client:
            await fetch_soup(client, "/page")

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        asyncio.run(run())
    assert excinfo.value.response.status_code == 503
    assert calls["n"] == 3
    assert retry_sleeps == [1.0, 2.0]


def test_fetch_soup_does_not_retry_a_removed_page(retry_sleeps):
    """404 is permanent — retrying a novel the site dropped just wastes time."""
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404, text="gone")

    async def run():
        async with _mock_client(handler) as client:
            await fetch_soup(client, "/book/removed")

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(run())
    assert calls["n"] == 1
    assert retry_sleeps == []


# ---- describe_error ------------------------------------------------------


def _http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.test/x")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


@pytest.mark.parametrize(
    ("status", "fragment"),
    [
        (404, "page not found (404)"),
        (403, "access denied (403)"),
        (429, "rate limited (429)"),
        (503, "server error (503)"),
        (418, "HTTP 418"),
    ],
)
def test_describe_error_reports_status(status, fragment):
    message = describe_error(_http_error(status), "Search failed")
    assert message.startswith("Search failed")
    assert fragment in message


def test_describe_error_generic_exception():
    assert (
        describe_error(ValueError("nope"), "Search failed")
        == "Search failed. Check your connection."
    )


def test_describe_error_timeout():
    message = describe_error(httpx.ConnectTimeout("slow"), "Search failed")
    assert "timed out" in message


def test_describe_error_transport():
    message = describe_error(httpx.ConnectError("refused"), "Search failed")
    assert "could not reach the server" in message


# ---- scriblehub blocked guard --------------------------------------------


def _fake_fetch(src, status: int, blocked_flag: bool | None):
    async def fetch(url, data=None, params=None):
        if blocked_flag is not None:
            src._blocked = blocked_flag
        return httpx.Response(
            status, text="<html>Just a moment</html>", request=httpx.Request("GET", url)
        )

    src._fetch = fetch


def test_scriblehub_search_sends_query_via_params():
    """The query must travel as a params dict, not raw f-string
    interpolation — unencoded spaces/&/unicode corrupt the URL."""
    src = ScribbleHubSource()
    seen = {}

    async def fetch(url, data=None, params=None):
        seen["url"] = url
        seen["params"] = params
        return httpx.Response(
            200, text="<html></html>", request=httpx.Request("GET", url)
        )

    src._fetch = fetch
    novels, pages = asyncio.run(src.search("war & peace", 3))
    assert seen["params"] == {"sf": 1, "sh": "war & peace", "pg": 3}
    assert "war" not in seen["url"]  # nothing interpolated into the URL itself
    assert novels == []
    assert pages == 2  # empty page → max(1, 3 - 1)


def test_scriblehub_blocked_403_returns_soup():
    """A flagged Cloudflare 403 must not raise: callers show the 'blocked'
    message only when fetch_url returns normally."""
    src = ScribbleHubSource()
    _fake_fetch(src, 403, blocked_flag=True)
    soup = asyncio.run(src.fetch_url("https://www.scribblehub.com/series/x/"))
    assert isinstance(soup, BeautifulSoup)


def test_scriblehub_unflagged_403_raises():
    src = ScribbleHubSource()
    _fake_fetch(src, 403, blocked_flag=False)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(src.fetch_url("https://www.scribblehub.com/series/x/"))


def test_scriblehub_500_raises_even_when_blocked():
    """The guard is status-specific: a server error is still an error."""
    src = ScribbleHubSource()
    _fake_fetch(src, 500, blocked_flag=True)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(src.fetch_url("https://www.scribblehub.com/series/x/"))


# ---- source catch-alls must not swallow HTTP errors ----------------------


def test_wuxiaspot_search_propagates_http_error():
    src = WuxiaSpotSource()

    class _Client:
        async def post(self, url, data=None):
            return httpx.Response(
                503, text="unavailable", request=httpx.Request("POST", url)
            )

    src._client = _Client()
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(src.search("query"))


def test_wuxiaspot_browse_genre_propagates_http_error():
    src = WuxiaSpotSource()

    class _Client:
        async def get(self, url, params=None, headers=None):
            return httpx.Response(500, text="boom", request=httpx.Request("GET", url))

    src._client = _Client()
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(src.browse_genre("action"))
