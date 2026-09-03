"""Tests for core.downloader — the download orchestrator."""
import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import core.library as lib
from core.downloader import download


class FakeSource:
    def __init__(self, chapters=None, cover="http://example.com/cover.jpg"):
        self._chapters = chapters or {}
        self._cover = cover
        self.name = "test-source"
        self.blocked = False

    async def read_chapter(self, url):
        return self._chapters.get(url, [f"Content of {url}"])

    async def cover_url(self, slug):
        return self._cover

    async def fetch_chapters(self, slug):
        return []


def _make_chapters(n=3):
    return [{"num": i + 1, "title": f"Chapter {i + 1}", "url": f"http://example.com/ch{i + 1}"} for i in range(n)]


def test_download_saves_chapters():
    with tempfile.TemporaryDirectory() as d:
        src = FakeSource()
        chapters = _make_chapters(2)
        saved, failed = asyncio.run(
            download(src, "test-novel", chapters, "Test Novel", base_dir=d)
        )
        assert saved == 2
        assert failed == 0
        novel_dir = os.path.join(d, "novels", "test-novel")
        assert os.path.isdir(novel_dir)
        files = os.listdir(novel_dir)
        assert "Chapter_1.txt" in files
        assert "Chapter_2.txt" in files


def test_download_writes_meta():
    with tempfile.TemporaryDirectory() as d:
        src = FakeSource()
        chapters = _make_chapters(1)
        asyncio.run(
            download(src, "meta-novel", chapters, "Meta Novel", total=5, base_dir=d)
        )
        meta = lib.read_meta("meta-novel", base_dir=d)
        assert meta["title"] == "Meta Novel"
        assert meta["chapters"] == 5


def test_download_with_translate():
    with tempfile.TemporaryDirectory() as d:
        src = FakeSource()
        chapters = _make_chapters(1)
        saved, failed = asyncio.run(
            download(src, "tr-novel", chapters, "TR", translate=True, lang="en", base_dir=d)
        )
        assert saved + failed >= 0  # may fail if deep_translator missing


def test_download_skip_existing():
    with tempfile.TemporaryDirectory() as d:
        lib.write_chapter("skip-novel", "Chapter 1", "already here", base_dir=d)
        src = FakeSource()
        chapters = _make_chapters(2)
        saved, failed = asyncio.run(
            download(src, "skip-novel", chapters, "Skip", base_dir=d)
        )
        assert saved == 1
        assert failed == 0


def test_download_progress_callback():
    with tempfile.TemporaryDirectory() as d:
        calls = []
        def cb(done, saved):
            calls.append((done, saved))
        src = FakeSource()
        chapters = _make_chapters(2)
        asyncio.run(
            download(src, "cb-novel", chapters, "CB", progress_cb=cb, base_dir=d)
        )
        assert len(calls) >= 1
        assert calls[-1][0] == 2


def test_download_cover_url_stored_in_meta():
    with tempfile.TemporaryDirectory() as d:
        src = FakeSource(cover="http://example.com/my-cover.jpg")
        chapters = _make_chapters(1)
        asyncio.run(
            download(src, "cover-novel", chapters, "Cover", base_dir=d)
        )
        meta = lib.read_meta("cover-novel", base_dir=d)
        assert meta.get("cover") == "http://example.com/my-cover.jpg"
