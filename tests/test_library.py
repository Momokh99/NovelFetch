"""Tests for core.library — the persistence store module."""
import json
import os
import tempfile

import core.library as lib


def test_read_meta_missing():
    with tempfile.TemporaryDirectory() as d:
        result = lib.read_meta("nonexistent", base_dir=d)
        assert result == {}
        assert not os.path.exists(os.path.join(d, "novels", "nonexistent", "meta.json"))


def test_write_meta_creates_file():
    with tempfile.TemporaryDirectory() as d:
        meta = {"title": "Test", "chapters": 10}
        lib.write_meta("test-slug", meta, base_dir=d)
        path = os.path.join(d, "novels", "test-slug", "meta.json")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["title"] == "Test"
        assert saved["chapters"] == 10


def test_read_meta_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        meta = {"title": "Roundtrip", "cover": "http://example.com/c.jpg", "tracked": True}
        lib.write_meta("slug-r", meta, base_dir=d)
        loaded = lib.read_meta("slug-r", base_dir=d)
        assert loaded["title"] == "Roundtrip"
        assert loaded["cover"] == "http://example.com/c.jpg"
        assert loaded["tracked"] is True


def test_meta_lang():
    with tempfile.TemporaryDirectory() as d:
        meta = {"lang": "en"}
        lib.write_meta("slug-lang", meta, base_dir=d)
        assert lib.meta_lang("slug-lang", base_dir=d) == "en"

    with tempfile.TemporaryDirectory() as d:
        assert lib.meta_lang("slug-nolang", base_dir=d) is None


def test_write_chapter():
    with tempfile.TemporaryDirectory() as d:
        ok = lib.write_chapter("my-novel", "Chapter 1", "Hello world", base_dir=d)
        assert ok is True
        path = os.path.join(d, "novels", "my-novel", "Chapter_1.txt")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            assert f.read() == "Hello world"


def test_write_chapter_with_lang():
    with tempfile.TemporaryDirectory() as d:
        lib.write_chapter("novel", "Ch1", "Translated", lang="fr", base_dir=d)
        path = os.path.join(d, "novels", "novel", "Ch1_fr.txt")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            assert f.read() == "Translated"


def test_local_chapters():
    with tempfile.TemporaryDirectory() as d:
        lib.write_chapter("nov", "Ch1", "c1", base_dir=d)
        lib.write_chapter("nov", "Ch2", "c2", base_dir=d)
        # Translation files are excluded from local_chapters
        chs = lib.local_chapters("nov", base_dir=d)
        assert len(chs) == 2
        titles = [c["title"] for c in chs]
        assert "Ch1" in titles
        assert "Ch2" in titles


def test_local_chapter_count():
    with tempfile.TemporaryDirectory() as d:
        lib.write_chapter("c", "A", "a", base_dir=d)
        lib.write_chapter("c", "B", "b", base_dir=d)
        assert lib.local_chapter_count("c", base_dir=d) == 2
        assert lib.local_chapter_count("missing", base_dir=d) == 0


def test_has_chapters():
    with tempfile.TemporaryDirectory() as d:
        assert lib.has_chapters("x", base_dir=d) is False
        lib.write_chapter("x", "A", "a", base_dir=d)
        assert lib.has_chapters("x", base_dir=d) is True


def test_missing_chapters():
    with tempfile.TemporaryDirectory() as d:
        lib.write_chapter("m", "Ch1", "c1", base_dir=d)
        online = [
            {"num": 1, "title": "Ch1", "url": "u1"},
            {"num": 2, "title": "Ch2", "url": "u2"},
            {"num": 3, "title": "Ch3", "url": "u3"},
        ]
        missing = lib.missing_chapters(online, "m", "", base_dir=d)
        assert len(missing) == 2
        titles = [c["title"] for c in missing]
        assert "Ch2" in titles
        assert "Ch3" in titles


def test_is_tracked():
    with tempfile.TemporaryDirectory() as d:
        lib.write_meta("t", {"tracked": True}, base_dir=d)
        assert lib.is_tracked("t", base_dir=d) is True


def test_delete_library():
    with tempfile.TemporaryDirectory() as d:
        lib.write_chapter("del", "A", "a", base_dir=d)
        lib.write_meta("del", {"title": "Del"}, base_dir=d)
        novel_dir = os.path.join(d, "novels", "del")
        assert os.path.isdir(novel_dir)
        lib.delete_library("del", base_dir=d)
        assert not os.path.isdir(novel_dir)


def test_display_title():
    with tempfile.TemporaryDirectory() as d:
        lib.write_meta("dt", {"title": "My Novel"}, base_dir=d)
        assert lib.display_title("dt", "Fallback", base_dir=d) == "My Novel"
        # When no meta, display_title derives from slug (not the fallback arg)
        assert lib.display_title("royalroad:12345/my-cool-novel", "Fallback", base_dir=d) == "My Cool Novel"


def test_scan_library():
    with tempfile.TemporaryDirectory() as d:
        lib.write_chapter("s1", "A", "a", base_dir=d)
        lib.write_meta("s1", {"title": "S1", "source": "royalroad"}, base_dir=d)
        lib.write_chapter("s2", "B", "b", base_dir=d)
        lib.write_meta("s2", {"title": "S2", "source": "scriblehub"}, base_dir=d)
        entries = lib._scan_library(d)
        slugs = [e["slug"] for e in entries]
        assert "s1" in slugs
        assert "s2" in slugs


def test_is_translation_file():
    assert lib.is_translation_file("Ch1_fr.txt") == "fr"
    assert lib.is_translation_file("Ch1_en.txt") == "en"
    assert lib.is_translation_file("Ch1.txt") is None


def test_chapter_path():
    with tempfile.TemporaryDirectory() as d:
        p = lib.chapter_path("Ch1", "nov", base_dir=d)
        assert os.path.join(d, "novels", "nov") in p
        assert "Ch1.txt" in p


def test_translated_path():
    with tempfile.TemporaryDirectory() as d:
        p = lib.translated_path("Ch1", "nov", "de", base_dir=d)
        assert "Ch1_de.txt" in p
        assert os.path.join(d, "novels", "nov") in p
