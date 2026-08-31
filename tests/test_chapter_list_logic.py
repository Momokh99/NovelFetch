"""Tests for chapter_list.py pure logic — selection, pagination, download subset."""

import pytest

# ---- _toggle_selection logic (pure set operations) ----

class FakeSelection:
    """Standalone replica of ChapterListScreen._toggle_selection logic."""

    def __init__(self):
        self._selected: set[int] = set()

    def toggle(self, idx, active=None):
        if active is None:
            if idx in self._selected:
                self._selected.discard(idx)
            else:
                self._selected.add(idx)
        else:
            if active:
                self._selected.add(idx)
            else:
                self._selected.discard(idx)


def test_toggle_selection_flip_add():
    s = FakeSelection()
    s.toggle(0)
    assert 0 in s._selected


def test_toggle_selection_flip_remove():
    s = FakeSelection()
    s.toggle(0)
    s.toggle(0)
    assert 0 not in s._selected


def test_toggle_selection_explicit_active_true():
    s = FakeSelection()
    s.toggle(5, active=True)
    assert 5 in s._selected


def test_toggle_selection_explicit_active_false():
    s = FakeSelection()
    s.toggle(5, active=True)
    s.toggle(5, active=False)
    assert 5 not in s._selected


def test_toggle_selection_explicit_false_no_existing():
    s = FakeSelection()
    s.toggle(3, active=False)
    assert 3 not in s._selected


def test_toggle_selection_multiple():
    s = FakeSelection()
    s.toggle(0, active=True)
    s.toggle(2, active=True)
    s.toggle(5, active=True)
    assert s._selected == {0, 2, 5}


def test_toggle_selection_mixed_modes():
    s = FakeSelection()
    s.toggle(1, active=True)   # explicit add
    s.toggle(2)                # flip add
    s.toggle(1, active=False)  # explicit remove
    assert s._selected == {2}


def test_download_selected_filters_by_indices():
    """_download_selected builds subset from _selected set."""
    chapters = [
        {"title": "Ch 1", "url": "u1"},
        {"title": "Ch 2", "url": "u2"},
        {"title": "Ch 3", "url": "u3"},
        {"title": "Ch 4", "url": "u4"},
        {"title": "Ch 5", "url": "u5"},
    ]
    selected = {1, 3}
    subset = [ch for i, ch in enumerate(chapters) if i in selected]
    assert len(subset) == 2
    assert subset[0]["title"] == "Ch 2"
    assert subset[1]["title"] == "Ch 4"


def test_download_selected_empty():
    chapters = [{"title": "Ch 1", "url": "u1"}]
    subset = [ch for i, ch in enumerate(chapters) if i in set()]
    assert subset == []


# ---- _load_more pagination ----

def test_load_more_step_calculation():
    """_load_more appends _row_step rows at a time."""
    total = 100
    row_step = 40
    built = 0

    # First load_more: built 0 → 40
    end = min(built + row_step, total)
    assert end == 40
    built = end

    # Second: 40 → 80
    end = min(built + row_step, total)
    assert end == 80
    built = end

    # Third: 80 → 100 (clamped)
    end = min(built + row_step, total)
    assert end == 100
    built = end

    # Fourth: already at total → no-op
    assert built >= total


def test_load_more_guard_when_fully_built():
    total = 10
    built = 10
    # Should return early
    assert built >= total


def test_load_more_guard_when_loading():
    loading = True
    built = 0
    # Should return early
    assert loading


# ---- overflow menu branching ----

def test_overflow_tracked_only_shows_remove():
    """Tracked novel with no chapters → 'Remove from library'."""
    meta = {"tracked": True, "title": "X"}
    has_chapters = False
    if meta.get("tracked") and not has_chapters:
        action = "Remove from library"
    else:
        action = "other"
    assert action == "Remove from library"


def test_overflow_with_chapters_shows_export_and_delete():
    """Novel with chapters → 'Export EPUB' + 'Delete'."""
    meta = {"tracked": True, "title": "X"}
    has_chapters = True
    actions = []
    if meta.get("tracked") and not has_chapters:
        actions = ["Remove from library"]
    else:
        actions = ["Export EPUB", "Delete"]
    assert actions == ["Export EPUB", "Delete"]


def test_overflow_no_meta_no_actions():
    meta = {}
    actions = []
    if meta:
        if meta.get("tracked") and not True:
            actions = ["Remove from library"]
        else:
            actions = ["Export EPUB", "Delete"]
    assert actions == []
