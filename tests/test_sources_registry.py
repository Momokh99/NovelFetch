"""Tests for the sources registry — offline, no network."""

import pytest
from bs4 import BeautifulSoup

from sources import REGISTRY

KEYS = {"royalroad", "scriblehub", "wuxiaspot"}


def test_registry_keys():
    assert set(REGISTRY) == KEYS


@pytest.mark.parametrize("key", sorted(KEYS))
def test_source_surface(key):
    src = REGISTRY[key]
    assert src.name
    assert src.label
    assert isinstance(src.browse_urls, dict) and src.browse_urls
    assert isinstance(src.genres, dict) and src.genres
    assert callable(getattr(src, "search", None))
    assert callable(getattr(src, "fetch_chapters", None))
    assert callable(getattr(src, "parse_slug", None))
    assert callable(getattr(src, "qualify_slug", None))
    assert callable(getattr(src, "extract_novel_rows", None))


def test_scriblehub_name_vs_key():
    # registry key has the typo; the source's own name spells it correctly.
    assert REGISTRY["scriblehub"].name == "scribblehub"
    assert REGISTRY["royalroad"].name == "royalroad"
    assert REGISTRY["wuxiaspot"].name == "wuxiaspot"


@pytest.mark.parametrize("key,prefix", [
    ("royalroad", "royalroad"),
    ("scriblehub", "scribblehub"),
    ("wuxiaspot", "wuxiaspot"),
])
def test_qualify_slug(key, prefix):
    assert REGISTRY[key].qualify_slug("abc") == f"{prefix}:abc"
    assert REGISTRY[key].qualify_slug("") == f"{prefix}:"


# ---- parse_slug ----

def test_parse_slug_royalroad():
    rr = REGISTRY["royalroad"]
    assert rr.parse_slug("https://www.royalroad.com/fiction/12345/a-title") == "12345/a-title"
    assert rr.parse_slug("https://www.royalroad.com/fiction/99/") == "99"
    assert rr.parse_slug("https://example.com/nope") is None
    assert rr.parse_slug("https://other-site.com/fiction/1") is None


def test_parse_slug_scribblehub():
    sh = REGISTRY["scriblehub"]
    assert sh.parse_slug("https://www.scribblehub.com/series/1234/name/") == "1234/name"
    assert sh.parse_slug("https://www.scribblehub.com/series/5678/deep/slug/") == "5678/deep/slug"
    assert sh.parse_slug("https://example.com/x") is None


def test_parse_slug_wuxiaspot():
    ws = REGISTRY["wuxiaspot"]
    assert ws.parse_slug("https://www.wuxiaspot.com/novel/my-novel.html") == "my-novel"
    assert ws.parse_slug("https://www.wuxiaspot.com/novel/x.html") == "x"
    assert ws.parse_slug("https://example.com/x") is None


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
    rows = REGISTRY["royalroad"].extract_novel_rows(BeautifulSoup("<div></div>", "html.parser"))
    assert rows == []


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
    sh = REGISTRY["scriblehub"]
    assert sh._absolutize("/img.jpg") == "https://www.scribblehub.com/img.jpg"
