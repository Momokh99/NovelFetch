"""Tests for the sources registry — offline, no network."""

import asyncio

import pytest
from bs4 import BeautifulSoup

from sources import REGISTRY

KEYS = {"novelfire", "royalroad", "scribblehub", "wuxiaspot"}


def test_registry_keys():
    assert set(REGISTRY) == KEYS


@pytest.mark.parametrize("key", sorted(KEYS))
def test_source_surface(key):
    src = REGISTRY[key]
    assert src.name
    assert src.label
    assert isinstance(src.browse_urls, dict)
    assert src.browse_urls
    assert isinstance(src.genres, dict)
    assert src.genres
    assert callable(getattr(src, "search", None))
    assert callable(getattr(src, "fetch_chapters", None))
    assert callable(getattr(src, "parse_slug", None))
    assert callable(getattr(src, "qualify_slug", None))
    assert callable(getattr(src, "extract_novel_rows", None))


def test_name_vs_registry_key():
    # registry keys match each source's own name.
    assert REGISTRY["scribblehub"].name == "scribblehub"
    assert REGISTRY["royalroad"].name == "royalroad"
    assert REGISTRY["wuxiaspot"].name == "wuxiaspot"
    assert REGISTRY["novelfire"].name == "novelfire"


def test_names_match_registry_keys():
    # guards the scriblehub/scribblehub typo from ever coming back: a source
    # whose registry key differs from its name breaks _get_source() round-trips.
    for key, src in REGISTRY.items():
        assert src.name == key


def test_get_source_roundtrip():
    from core.utils import _get_source

    for src in REGISTRY.values():
        assert _get_source(src.qualify_slug("abc")) is src


@pytest.mark.parametrize(
    ("key", "prefix"),
    [
        ("novelfire", "novelfire"),
        ("royalroad", "royalroad"),
        ("scribblehub", "scribblehub"),
        ("wuxiaspot", "wuxiaspot"),
    ],
)
def test_qualify_slug(key, prefix):
    assert REGISTRY[key].qualify_slug("abc") == f"{prefix}:abc"
    assert REGISTRY[key].qualify_slug("") == f"{prefix}:"


# ---- parse_slug ----


def test_parse_slug_royalroad():
    rr = REGISTRY["royalroad"]
    assert (
        rr.parse_slug("https://www.royalroad.com/fiction/12345/a-title")
        == "12345/a-title"
    )
    assert rr.parse_slug("https://www.royalroad.com/fiction/99/") == "99"
    assert rr.parse_slug("https://example.com/nope") is None
    assert rr.parse_slug("https://other-site.com/fiction/1") is None


def test_parse_slug_scribblehub():
    sh = REGISTRY["scribblehub"]
    assert sh.parse_slug("https://www.scribblehub.com/series/1234/name/") == "1234/name"
    assert (
        sh.parse_slug("https://www.scribblehub.com/series/5678/deep/slug/")
        == "5678/deep/slug"
    )
    assert sh.parse_slug("https://example.com/x") is None


def test_parse_slug_wuxiaspot():
    ws = REGISTRY["wuxiaspot"]
    assert ws.parse_slug("https://www.wuxiaspot.com/novel/my-novel.html") == "my-novel"
    assert ws.parse_slug("https://www.wuxiaspot.com/novel/x.html") == "x"
    assert ws.parse_slug("https://example.com/x") is None


def test_parse_slug_novelfire():
    nf = REGISTRY["novelfire"]
    # bare slug — the registry prefix is added later by qualify_slug.
    assert nf.parse_slug("https://novelfire.net/book/my-novel") == "my-novel"
    assert nf.parse_slug("https://www.novelfire.net/book/my-novel/") == "my-novel"
    assert nf.parse_slug("https://novelfire.net/author/someone") is None
    assert nf.parse_slug("https://novelfire.net/home") is None
    assert nf.parse_slug("https://novelfire.net/book/my-novel/chapter-1") is None
    assert nf.parse_slug("https://example.com/book/x") is None


# ---- extract_novel_rows ----


def test_extract_novel_rows_royalroad_offline():
    html = """
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
    rows = REGISTRY["royalroad"].extract_novel_rows(BeautifulSoup(html, "html.parser"))
    assert len(rows) == 2
    assert rows[0]["title"] == "One"
    assert rows[0]["slug"] == "111/one"
    assert rows[0]["cover"] == "https://www.royalroad.com/covers/one.jpg"
    assert rows[1]["title"] == "Two"
    assert rows[1]["slug"] == "222/two"
    assert rows[1]["cover"] == ""


def test_extract_novel_rows_royalroad_empty():
    rows = REGISTRY["royalroad"].extract_novel_rows(
        BeautifulSoup("<div></div>", "html.parser")
    )
    assert rows == []


def test_extract_novel_rows_novelfire_lazy_cover():
    # Browse pages lazy-load: data-src holds the real URL, src a data: placeholder.
    html = """
    <li class="novel-item">
      <a href="/book/my-novel">
        <figure class="novel-cover">
          <img data-src="/server-1/my-novel.jpg" src="data:image/gif;base64,R0lGOD">
        </figure>
        <h4 class="novel-title text2row">My Novel</h4>
      </a>
      <div class="novel-stats">12 Chapters</div>
    </li>
    """
    rows = REGISTRY["novelfire"].extract_novel_rows(BeautifulSoup(html, "html.parser"))
    assert rows == [
        {
            "title": "My Novel",
            "author": "Unknown",
            "slug": "my-novel",
            "latest": "",
            "cover": "https://novelfire.net/server-1/my-novel.jpg",
        }
    ]
    assert "base64" not in rows[0]["cover"]


def test_extract_novel_rows_novelfire_eager_cover():
    # Search pages embed the URL directly in src, with no data-src.
    html = """
    <li class="novel-item">
      <a href="/book/other">
        <figure class="novel-cover"><img src="/server-1/other.jpg"></figure>
        <h4 class="novel-title text1row">Other</h4>
      </a>
    </li>
    """
    rows = REGISTRY["novelfire"].extract_novel_rows(BeautifulSoup(html, "html.parser"))
    assert len(rows) == 1
    assert rows[0]["slug"] == "other"
    assert rows[0]["cover"] == "https://novelfire.net/server-1/other.jpg"


def test_extract_novel_rows_novelfire_empty():
    nf = REGISTRY["novelfire"]
    assert nf.extract_novel_rows(BeautifulSoup("<div></div>", "html.parser")) == []
    # Rows without a title or a link are skipped, not crashed on.
    assert (
        nf.extract_novel_rows(
            BeautifulSoup(
                '<li class="novel-item"><a href="/book/x"></a></li>', "html.parser"
            )
        )
        == []
    )


# ---- _absolutize ----


def test_absolutize_royalroad():
    rr = REGISTRY["royalroad"]
    assert rr._absolutize("/img.jpg") == "https://www.royalroad.com/img.jpg"
    assert rr._absolutize("https://x.com/img.jpg") == "https://x.com/img.jpg"


def test_absolutize_wuxiaspot():
    ws = REGISTRY["wuxiaspot"]
    assert ws._absolutize("/img.jpg") == "https://www.wuxiaspot.com/img.jpg"
    assert ws._absolutize("https://x.com/img.jpg") == "https://x.com/img.jpg"


def test_absolutize_scribblehub():
    sh = REGISTRY["scribblehub"]
    assert sh._absolutize("/img.jpg") == "https://www.scribblehub.com/img.jpg"


def test_absolutize_novelfire():
    nf = REGISTRY["novelfire"]
    assert nf._absolutize("/img.jpg") == "https://novelfire.net/img.jpg"
    assert nf._absolutize("https://x.com/img.jpg") == "https://x.com/img.jpg"


def test_novelfire_genres_match_live_slugs():
    # A wrong key renders a browse chip that 404s in the UI.
    genres = REGISTRY["novelfire"].genres
    assert len(genres) == 47
    for key in ("all", "arts", "fan-fiction"):
        assert key in genres
    for stale in ("genre-all", "art", "fanfiction"):
        assert stale not in genres


def test_novelfire_browse_urls_use_real_sort_keys():
    urls = REGISTRY["novelfire"].browse_urls
    assert urls["home"] == "https://novelfire.net/home"
    assert "sort-latest-release" in urls["newest"]
    # sort-newest is a typo the site does not serve.
    assert not any("sort-newest" in u for u in urls.values())


def test_novelfire_fetch_chapters_paces_page_requests(monkeypatch):
    """novelfire rate-limits bursty paging, so pages must not be hammered."""
    import sources.novelfire as nf_mod

    sleeps = []

    class _FakeAsyncio:
        @staticmethod
        async def sleep(seconds):
            sleeps.append(seconds)

    monkeypatch.setattr(nf_mod, "asyncio", _FakeAsyncio)

    def _row(n):
        return (
            f'<li><a href="/book/x/chapter-{n}">'
            f'<span class="chapter-no">{n}</span>'
            f'<strong class="chapter-title">Chapter {n}</strong></a></li>'
        )

    pages = [
        "<ul class='chapter-list'>" + _row(1) + _row(2) + "</ul>",
        "<ul class='chapter-list'>" + _row(2) + _row(3) + "</ul>",
        "<html><body>nothing here</body></html>",
    ]
    seen = []

    async def fake_fetch_url(url, params=None):
        seen.append(params)
        return BeautifulSoup(pages[len(seen) - 1], "html.parser")

    src = REGISTRY["novelfire"]
    monkeypatch.setattr(src, "fetch_url", fake_fetch_url)

    chapters = asyncio.run(src.fetch_chapters("x"))

    # Every page that yielded rows waits before the next request; the empty
    # terminal page breaks out without a trailing sleep.
    assert sleeps == [src.PAGE_DELAY, src.PAGE_DELAY]
    assert seen == [{"page": 1}, {"page": 2}, {"page": 3}]
    assert [c["num"] for c in chapters] == [1, 2, 3]
    assert len({c["url"] for c in chapters}) == 3
