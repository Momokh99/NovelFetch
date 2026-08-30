"""Regression test for _download_novel: chapters must download concurrently
(bounded by the semaphore) rather than one at a time, and the returned
saved/failed counts plus progress_cb must stay correct either way."""

import asyncio
import os

import pytest

from screens import utils


class _FakeSource:
    """save_chapter() sleeps briefly so overlap is observable, and fails for
    one chapter on purpose to exercise the failed-count path."""

    name = "fake"

    def __init__(self):
        self.max_concurrent = 0
        self._inflight = 0

    async def save_chapter(self, url, title, slug):
        self._inflight += 1
        self.max_concurrent = max(self.max_concurrent, self._inflight)
        try:
            await asyncio.sleep(0.05)
            if title == "Chapter 3":
                return False
            path = os.path.join("novels", slug, f"{title}.txt")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("x")
            return True
        finally:
            self._inflight -= 1

    async def cover_url(self, slug):
        return ""


def _chapters(n):
    return [{"num": i, "title": f"Chapter {i}", "url": f"http://x/{i}"}
            for i in range(1, n + 1)]


def test_download_novel_runs_chapters_concurrently(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = _FakeSource()
    saved, failed = asyncio.run(
        utils._download_novel(source, "fake:demo", _chapters(8), "Demo"))

    assert saved == 7
    assert failed == 1
    # With a Semaphore(4) and 8 chapters that each take 50ms, strictly
    # sequential execution could never exceed 1 in flight; concurrent
    # execution should reach the semaphore's cap.
    assert source.max_concurrent > 1


def test_download_novel_progress_cb_reaches_total(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = _FakeSource()
    calls = []
    asyncio.run(utils._download_novel(
        source, "fake:demo2", _chapters(5), "Demo2",
        progress_cb=lambda done, saved: calls.append((done, saved))))

    assert len(calls) == 5
    # done values are a permutation-free count of completions: the final
    # call must report all 5 chapters processed.
    assert max(c[0] for c in calls) == 5
    # "Chapter 3" is the fake source's forced failure -> 4 of 5 saved.
    assert max(c[1] for c in calls) == 4


def test_download_novel_skips_already_downloaded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    slug = "fake:demo3"
    os.makedirs(os.path.join("novels", slug), exist_ok=True)
    with open(os.path.join("novels", slug, "Chapter_1.txt"), "w") as f:
        f.write("already here")

    source = _FakeSource()
    saved, failed = asyncio.run(
        utils._download_novel(source, slug, _chapters(3), "Demo3"))

    # Chapter 1 already exists -> skipped (not re-saved, not failed);
    # chapter 3 is the fake-source's forced failure; chapter 2 saves.
    assert saved == 1
    assert failed == 1
