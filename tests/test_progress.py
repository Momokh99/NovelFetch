"""Tests for ProgressTracker (progress.py)."""

import json

import pytest

import progress as progress_mod
from progress import ProgressTracker


@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "novels").mkdir()
    return ProgressTracker(str(tmp_path / "novels" / "progress.json"))


@pytest.fixture()
def mock_time(monkeypatch):
    """Return a callable that yields deterministic timestamps in sequence."""
    clock = iter(range(1000, 10000))
    monkeypatch.setattr(progress_mod.time, "time", lambda: next(clock))


def test_mark_seen_and_reads(tracker):
    tracker.mark_seen("rr:foo", 0)
    tracker.mark_seen("rr:foo", 3)
    assert tracker.get_last("rr:foo") == 3
    assert tracker.get_seen("rr:foo") == {0, 3}
    assert tracker.get_last("missing") is None
    assert tracker.get_seen("missing") == set()


def test_mark_seen_appends_seen_not_duplicates(tracker):
    tracker.mark_seen("x", 1)
    tracker.mark_seen("x", 1)
    tracker.mark_seen("x", 1)
    assert tracker.get_seen("x") == {1}


def test_history_newest_first(tracker, mock_time):
    tracker.mark_seen("a", 1)
    tracker.mark_seen("b", 2)
    hist = tracker.get_history()
    assert [h["slug"] for h in hist] == ["b", "a"]
    assert hist[0]["last"] == 2
    assert hist[1]["last"] == 1


def test_history_excludes_no_time(tracker):
    # mark_seen then clear_history strips last_time
    tracker.mark_seen("a", 1)
    tracker.clear_history()
    assert tracker.get_history() == []


def test_clear_history_keeps_progress_and_tracking(tracker, mock_time):
    tracker.mark_seen("a", 5)
    tracker.track("a", "Novel A")
    tracker.clear_history()

    assert tracker.get_last("a") is None
    assert tracker.get_history() == []
    assert tracker.get_seen("a") == {5}
    assert tracker.is_tracked("a")


def test_clear_history_on_empty_tracker(tracker):
    tracker.clear_history()
    assert tracker.get_history() == []


def test_remove_history_entry_only_affects_one(tracker, mock_time):
    tracker.mark_seen("a", 1)
    tracker.mark_seen("b", 2)
    tracker.remove_history_entry("a")
    assert tracker.get_last("a") is None
    assert tracker.get_last("b") == 2
    assert [h["slug"] for h in tracker.get_history()] == ["b"]


def test_remove_history_entry_keeps_progress_and_tracking(tracker, mock_time):
    tracker.mark_seen("a", 5)
    tracker.track("a", "Novel A")
    tracker.remove_history_entry("a")
    assert tracker.get_last("a") is None
    assert tracker.get_seen("a") == {5}
    assert tracker.is_tracked("a")


def test_remove_history_entry_nonexistent_is_noop(tracker):
    tracker.remove_history_entry("ghost")
    assert tracker.get_last("ghost") is None


def test_remove_forgets_entry(tracker, mock_time):
    tracker.mark_seen("a", 1)
    tracker.remove("a")
    assert tracker.get_last("a") is None
    assert tracker.get_seen("a") == set()


def test_remove_nonexistent_is_noop(tracker):
    tracker.remove("ghost")
    assert tracker.get_last("ghost") is None


def test_track_untrack(tracker):
    tracker.track("x:y", "Title")
    assert tracker.is_tracked("x:y")
    assert tracker.tracked_novels() == [{"slug": "x:y", "title": "Title"}]
    tracker.untrack("x:y")
    assert not tracker.is_tracked("x:y")
    tracker.untrack("never-there")  # no-op, must not raise


def test_track_updates_title_on_change(tracker):
    tracker.track("a", "Old Title")
    tracker.track("a", "New Title")
    assert tracker.tracked_novels() == [{"slug": "a", "title": "New Title"}]


def test_track_same_title_no_dirty_flag(tracker):
    tracker.track("a", "Title")
    tracker._tracked_dirty = False
    tracker.track("a", "Title")  # same title — dirty flag should stay False
    assert not tracker._tracked_dirty


def test_flush_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "novels").mkdir()
    path = "novels/progress.json"
    clock = iter([8000])
    monkeypatch.setattr(progress_mod.time, "time", lambda: next(clock))

    t = ProgressTracker(path)
    t.mark_seen("s", 2)
    t.track("s", "T")
    t.flush()

    t2 = ProgressTracker(path)
    assert t2.get_last("s") == 2
    assert t2.is_tracked("s")
    assert t2.get_seen("s") == {2}

    data = json.loads((tmp_path / "novels" / "progress.json").read_text())
    assert data["s"]["last"] == 2


def test_flush_noop_when_not_dirty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "novels").mkdir()
    t = ProgressTracker("novels/progress.json")
    # no writes → flush should not create the file
    t.flush()
    assert not (tmp_path / "novels" / "progress.json").exists()


def test_flush_creates_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    t = ProgressTracker("deep/nested/progress.json")
    t.mark_seen("x", 1)
    t.flush()
    assert (tmp_path / "deep" / "nested" / "progress.json").exists()


def test_legacy_int_entries_migrate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    novels = tmp_path / "novels"
    novels.mkdir()
    path = novels / "progress.json"
    path.write_text(json.dumps({"old": 4}))
    t = ProgressTracker(str(path))
    assert t.get_last("old") == 4
    assert t.get_seen("old") == {4}


def test_tracked_novels_sorted_by_slug(tracker):
    tracker.track("c", "Charlie")
    tracker.track("a", "Alpha")
    tracker.track("b", "Bravo")
    assert [n["slug"] for n in tracker.tracked_novels()] == ["a", "b", "c"]


def test_tracked_novels_empty(tracker):
    assert tracker.tracked_novels() == []


def test_is_translation_file():
    f = progress_mod._is_translation_file
    assert f("Chapter_1_ar.txt") == "ar"
    assert f("Chapter_1_zh-cn.txt") == "zh-cn"
    assert f("Chapter_1_xx.txt") is None
    assert f("Chapter_1.txt") is None
    assert f("cover.jpg") is None
    assert f("") is None


def test_scan_library_counts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "novels" / "rr:demo"
    d.mkdir(parents=True)
    (d / "meta.json").write_text('{"title": "Demo"}')
    (d / "Ch_1.txt").write_text("x")
    (d / "Ch_2.txt").write_text("x")
    (d / "Ch_2_es.txt").write_text("translated")
    (d / "cover.jpg").write_bytes(b"x")

    lib = progress_mod._scan_library()
    assert len(lib) == 1
    entry = lib[0]
    assert entry["slug"] == "rr:demo"
    assert entry["count"] == 4
    assert entry["title"] == "Demo"


def test_scan_library_multiple_novels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    novels = tmp_path / "novels"
    for slug in ("rr:alpha", "rr:beta"):
        d = novels / slug
        d.mkdir(parents=True)
        (d / "meta.json").write_text('{"title": "X"}')
        (d / "Ch_1.txt").write_text("x")

    lib = progress_mod._scan_library()
    assert len(lib) == 2
    assert [e["slug"] for e in lib] == ["rr:alpha", "rr:beta"]
    assert all(e["count"] == 2 for e in lib)  # meta + 1 chapter


def test_scan_library_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "novels").mkdir()
    assert progress_mod._scan_library() == []


def test_scan_library_no_novels_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert progress_mod._scan_library() == []


def test_slug_to_title():
    assert progress_mod._slug_to_title("my-novel") == "My Novel"
    assert progress_mod._slug_to_title("rr:the-beginning") == "The Beginning"
    assert progress_mod._slug_to_title("plain") == "Plain"
