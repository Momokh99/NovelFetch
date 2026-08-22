"""Tests for android_app/screens/utils.py pure helpers (no network/UI)."""

import json
import os

import pytest

from screens import utils


# ---- translation-file detection ----

def test_is_translation_file_supported_langs():
    f = utils._is_translation_file
    assert f("Ch_1_ar.txt") == "ar"
    assert f("Ch_1_zh-cn.txt") == "zh-cn"
    assert f("Ch_1_pt.txt") == "pt"


def test_is_translation_file_rejects():
    f = utils._is_translation_file
    assert f("Ch_1.txt") is None
    assert f("Ch_1_xx.txt") is None
    assert f("meta.json") is None
    assert f("") is None


# ---- chapter ordering ----

def test_chapter_sort_key_numeric_not_lexicographic():
    names = ["Chapter_10.txt", "Chapter_2.txt", "Chapter_1.txt"]
    assert sorted(names, key=utils._chapter_sort_key) == [
        "Chapter_1.txt", "Chapter_2.txt", "Chapter_10.txt"]


def test_chapter_sort_key_no_digits():
    assert utils._chapter_sort_key("no-digits.txt") == 0


def test_chapter_sort_key_leading_zeros():
    names = ["ch-002.txt", "ch-010.txt", "ch-001.txt"]
    assert sorted(names, key=utils._chapter_sort_key) == [
        "ch-001.txt", "ch-002.txt", "ch-010.txt"]


# ---- local chapters ----

def test_local_chapters_excludes_translations_and_sorts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "novels" / "rr:demo"
    d.mkdir(parents=True)
    for name in ("Chapter_10.txt", "Chapter_2.txt", "Chapter_2_es.txt"):
        (d / name).write_text("x")

    chapters = utils._local_chapters("rr:demo")
    assert [c["num"] for c in chapters] == [1, 2]
    titles = [c["title"] for c in chapters]
    assert titles == ["Chapter 2", "Chapter 10"]
    assert all(c["url"] == "" for c in chapters)


def test_local_chapters_missing_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert utils._local_chapters("nope") == []


def test_local_chapters_empty_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "novels" / "empty"
    d.mkdir(parents=True)
    assert utils._local_chapters("empty") == []


def test_local_chapters_only_translations(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "novels" / "tr"
    d.mkdir(parents=True)
    (d / "Ch_1_ar.txt").write_text("x")
    (d / "Ch_1_es.txt").write_text("x")
    assert utils._local_chapters("tr") == []


def test_local_chapters_non_txt_ignored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "novels" / "misc"
    d.mkdir(parents=True)
    (d / "cover.jpg").write_text("x")
    (d / "meta.json").write_text("{}")
    assert utils._local_chapters("misc") == []


# ---- slug/source helpers ----

def test_get_source_from_qualified_slug():
    src = utils._get_source("royalroad:some-novel")
    assert src is not None and src.name == "royalroad"
    assert utils._get_source("unqualified") is None
    assert utils._get_source("") is None
    assert utils._get_source("unknown:slug") is None


def test_read_meta_missing_or_bad(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert utils._read_meta("ghost") == {}
    d = tmp_path / "novels" / "bad"
    d.mkdir(parents=True)
    (d / "meta.json").write_text("{oops")
    assert utils._read_meta("bad") == {}


def test_read_meta_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "novels" / "ok"
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"title": "Ok", "lang": "es"}))
    meta = utils._read_meta("ok")
    assert meta["title"] == "Ok"
    assert utils._meta_lang("ok") == "es"
    assert utils._meta_lang("missing") is None


def test_translated_path():
    p = utils._translated_path("Chapter 1/2", "rr:x", "ar")
    assert p.endswith("Chapter_1-2_ar.txt")
    assert utils._translated_path("t", "slug", "") == ""


def test_has_chapters_ignores_translation_only_folders(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "novels" / "tr-only"
    d.mkdir(parents=True)
    (d / "C_1_fr.txt").write_text("x")
    assert not utils._has_chapters("tr-only")
    (d / "C_1.txt").write_text("x")
    assert utils._has_chapters("tr-only")


def test_has_chapters_empty_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "novels" / "empty"
    d.mkdir(parents=True)
    assert not utils._has_chapters("empty")


def test_has_chapters_missing_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert not utils._has_chapters("nope")


# ---- cover cache paths ----

def test_cover_cache_path_deterministic_and_ext():
    a = utils._cover_cache_path("http://x/c.png")
    b = utils._cover_cache_path("http://x/c.png?size=big")
    assert a != b
    assert a.endswith(".png")
    weird = utils._cover_cache_path("http://x/c")
    assert weird.endswith(".jpg")
    assert utils._cover_cache_path("") == ""


def test_cached_cover_miss_then_hit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    url = "http://x/c.png"
    assert utils._cached_cover(url) == ""
    path = utils._cover_cache_path(url)
    os.makedirs(utils._COVER_CACHE_DIR, exist_ok=True)
    open(path, "wb").write(b"x")
    assert utils._cached_cover(url) == path


def test_cached_cover_different_urls_different_paths():
    a = utils._cover_cache_path("http://x/a.png")
    b = utils._cover_cache_path("http://y/a.png")
    assert a != b
