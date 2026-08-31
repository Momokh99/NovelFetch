"""Tests for the Home tab's novel multi-select + batch download logic:
selection set math, card visual wiring, mock-free pure helpers (_picker_options,
_selected_entries), and progress-mutation actions (mark read/unread, track)."""

import json
import os

import pytest
from kivy.core.window import Window
from kivy.lang import Builder
from kivymd.app import MDApp

from gui.screens.home_tab import _picker_options

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "gui")


def _find(widget, cls):
    if isinstance(widget, cls):
        return widget
    for child in widget.children:
        found = _find(child, cls)
        if found:
            return found
    return None


class MockTouch:
    """Minimal stand-in for a Kivy touch event. pos/x/y stay in sync like the
    real MotionEvent property bindings, which the long-press mixin relies on."""

    def __init__(self, pos):
        self.x, self.y = pos

    @property
    def pos(self):
        return (self.x, self.y)

    @pos.setter
    def pos(self, value):
        self.x, self.y = value


class _HomeApp(MDApp):
    def build(self):
        from gui.screens.home_tab import HomeTab
        return HomeTab()


@pytest.fixture
def tab(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("novels", exist_ok=True)
    Builder.load_file(os.path.join(APP, "kv/topbar.kv"))
    Builder.load_file(os.path.join(APP, "kv/home_tab.kv"))
    import kivy
    app = _HomeApp()
    kivy.app.App._app_instance = app
    win = app.build()
    Window.add_widget(win)
    win.pos = (0, 0)
    win.size = Window.size
    return win


def _make_novel(slug, chapters, last=None, title=None, tracked=False):
    os.makedirs(os.path.join("novels", slug), exist_ok=True)
    meta = {"title": title or slug, "cover": "", "chapters": chapters}
    if tracked:
        meta["tracked"] = True
    with open(os.path.join("novels", slug, "meta.json"), "w") as f:
        json.dump(meta, f)
    if last is not None:
        from core.progress import progress
        progress.mark_seen(slug, last)
    return {"slug": slug, "title": title or slug, "count": chapters}


def _chapters(n=12):
    return [{"title": f"Chapter {i + 1}", "url": f"https://x/{i}"}
            for i in range(n)]


# ---------- _picker_options ----------

def test_picker_options_original_section():
    opts = _picker_options(_chapters(12), seen=set(), downloaded=0, lang="ar")
    labels = [o["label"] for o in opts]
    assert "Original" in labels
    # Next rows label off the actual subset size (capped by chapter count),
    # matching the existing DownloadPickerScreen behaviour.
    assert "Next 5" in labels
    assert "Next 10" in labels
    assert "Next 12" in labels
    assert "All unread (12)" in labels
    assert "All (12)" in labels


def test_picker_options_unread_excludes_seen():
    opts = _picker_options(_chapters(12), seen={0, 1, 2}, downloaded=0,
                           lang="ar")
    unread = [o for o in opts if o["label"].startswith("All unread")]
    assert unread[0] == {"label": "All unread (9)", "subset": [
        c for c in _chapters(12) if c not in _chapters(12)[:3]],
        "translate": False}


def test_picker_options_remaining_skips_downloaded():
    opts = _picker_options(_chapters(10), seen=set(), downloaded=4, lang="ar")
    assert "Original" in [o["label"] for o in opts]   # remaining = 6 > 0
    next25 = [o for o in opts if o["label"] == "Next 6"][0]
    assert len(next25["subset"]) == 6
    all_opt = [o for o in opts if o["label"] == "All (10)"][0]
    assert len(all_opt["subset"]) == 10


def test_picker_options_fully_downloaded_no_original():
    opts = _picker_options(_chapters(5), seen=set(), downloaded=5, lang="ar")
    labels = [o["label"] for o in opts]
    assert "Original" not in labels          # no remaining chapters
    assert "Translated (Arabic)" in labels


def test_picker_options_empty_chapters():
    assert _picker_options([], seen=set(), downloaded=0, lang="ar") == []


def test_picker_options_translated_section_uses_lang_label():
    opts = _picker_options(_chapters(5), seen=set(), downloaded=0, lang="fr")
    labels = [o["label"] for o in opts]
    assert "Translated (French)" in labels
    translated = [o for o in opts if o.get("translate")]
    assert translated
    assert all(o["translate"] for o in translated)


def test_picker_options_fresh_novel_default_counts():
    opts = _picker_options(_chapters(8), seen=set(), downloaded=0, lang="ar")
    original_all = [o for o in opts if o["label"] == "All (8)"][0]
    assert len(original_all["subset"]) == 8
    assert original_all["translate"] is False


# ---------- selection state ----------

def test_enter_select_sets_mode_and_selects(tab):
    _make_novel("a:sel1", chapters=5)
    tab._build_library([
        {"slug": "a:sel1", "title": "sel1", "count": 5}])
    tab._enter_select("a:sel1")
    assert tab._select_mode is True
    assert tab._selected == {"a:sel1"}
    assert tab.sel_footer.height > 0
    assert tab.sel_count.text == "1 selected"


def test_toggle_select_add_remove(tab):
    tab._enter_select("a:one")
    tab._toggle_select("b:two")
    assert tab._selected == {"a:one", "b:two"}
    assert tab.sel_count.text == "2 selected"
    tab._toggle_select("a:one")
    assert tab._selected == {"b:two"}
    assert tab.sel_count.text == "1 selected"


def test_exit_select_clears_state(tab):
    tab._enter_select("a:one")
    tab._exit_select()
    assert tab._select_mode is False
    assert tab._selected == set()
    assert tab.sel_footer.height == 0


def test_card_badge_tracks_selection(tab):
    # Real KivyMD cards (ripple FBO) cannot be constructed in the headless
    # test env, so exercise the badge-wiring logic through stub cards.
    class FakeBadge:
        selected = False

    tab.content_box.clear_widgets()
    from kivy.uix.widget import Widget
    card = Widget()
    card._slug = "a:badge"
    card._sel_badge = FakeBadge()
    tab.content_box.add_widget(card)
    assert card._sel_badge.selected is False
    tab._enter_select("a:badge")
    assert card._sel_badge.selected is True
    tab._toggle_select("a:badge")   # unselect while still in select mode
    assert card._sel_badge.selected is False
    tab._toggle_select("a:badge")
    assert card._sel_badge.selected is True
    tab._exit_select()
    assert card._sel_badge.selected is False


def test_card_release_toggles_in_select_mode(tab):
    _make_novel("a:rel", chapters=5)
    tab._build_library([{"slug": "a:rel", "title": "rel", "count": 5}])
    tab._open_library_novel = lambda *a, **k: None   # count invocations
    calls = []

    def _spy(slug, title, cover):
        calls.append(slug)
    tab._open_library_novel = _spy
    tab._card_release(card=None, slug="a:rel", title="rel", cover="")
    assert calls == ["a:rel"]                       # normal tap opens
    tab._enter_select("z:other")
    calls.clear()
    tab._card_release(card=None, slug="a:rel", title="rel", cover="")
    assert calls == []                               # select-mode tap toggles
    assert "a:rel" in tab._selected


def test_card_release_after_long_press_is_swallowed(tab):
    _make_novel("a:lp", chapters=5)
    tab._build_library([{"slug": "a:lp", "title": "lp", "count": 5}])
    card = type("C", (), {"_long_fired": True, "_sel_badge": None, "_slug": "a:lp"})
    tab._selected = set()
    tab._card_release(card, "a:lp", "lp", "")
    assert tab._selected == set()   # release right after a hold: no toggle


def test_selected_entries_sorted(tab):
    _make_novel("a:x", chapters=3)
    _make_novel("b:y", chapters=4)
    tab._library = [
        {"slug": "b:y", "title": "Y", "count": 4},
        {"slug": "a:x", "title": "X", "count": 3},
    ]
    tab._selected = {"b:y", "a:x"}
    slugs = [s for s, _n in tab._selected_entries()]
    assert slugs == ["a:x", "b:y"]


# ---------- long-press detection ----------

def test_long_press_fires_and_flags_release(tab):
    # The mixin combined with a plain Widget avoids MDCard's ripple FBO, which
    # cannot initialize in the headless test environment.
    from kivy.uix.widget import Widget

    from gui.screens.home_tab import _LongPressMixin

    class Card(_LongPressMixin, Widget):
        pass

    card = Card(pos=(0, 0), size=(100, 50))
    fired = []
    card.on_long_press = lambda: fired.append(1)
    touch = MockTouch(pos=(50, 25))
    card._lp_touch = touch               # simulate the held touch mid-hold
    card._fire_long(touch)
    assert fired == [1]
    assert card._long_fired is True
    # The release right after a hold must not re-toggle: the guard reads the
    # flag and the mixin resets it after dispatching to super.
    card.on_touch_up(touch)
    assert card._long_fired is False


def test_long_press_cancelled_by_movement(tab):
    from kivy.uix.widget import Widget

    from gui.screens.home_tab import _LongPressMixin

    class Card(_LongPressMixin, Widget):
        pass

    card = Card(pos=(0, 0), size=(100, 50))
    fired = []
    card.on_long_press = lambda: fired.append(1)
    touch = MockTouch(pos=(50, 25))
    card.on_touch_down(touch)
    assert card._lp_event is not None
    touch.pos = (90, 25)                 # same touch moved: scroll gesture
    card.on_touch_move(touch)
    assert card._lp_event is None        # long-press cancelled: no orphan timer
    assert card._lp_touch is None
    assert fired == []                   # a cancelled hold never triggers
    touch.pos = (50, 25)
    for _ in range(2):
        # A cancelled hold must not fire even if the finger returns to the card.
        card.on_touch_move(touch)
    assert fired == []


def test_long_press_ignored_outside_card(tab):
    from kivy.uix.widget import Widget

    from gui.screens.home_tab import _LongPressMixin

    class Card(_LongPressMixin, Widget):
        pass

    card = Card(pos=(0, 0), size=(100, 50))
    touch = MockTouch(pos=(500, 400))   # outside the card
    card.on_touch_down(touch)
    assert card._lp_event is None


# ---------- overlay touch pass-through ----------

def test_hidden_overlay_lets_touches_fall_through(tab):
    # A full-screen overlay must NOT eat touches while hidden, or the library
    # grid behind it can't be tapped/scrolled. This is the regression that
    # blocked select + short-press after the overlay was added.
    from gui.screens.home_tab import _TouchPassThrough

    overlay = _TouchPassThrough()
    overlay.opacity = 0
    overlay.size_hint = (1, 1)
    touch = MockTouch(pos=(100, 100))
    assert overlay.on_touch_down(touch) is False
    assert overlay.on_touch_move(touch) is False
    assert overlay.on_touch_up(touch) is False


def test_visible_overlay_consumes_touch(tab):
    from gui.screens.home_tab import _TouchPassThrough

    overlay = _TouchPassThrough()
    overlay.opacity = 1
    overlay.size_hint = (1, 1)
    touch = MockTouch(pos=(100, 100))
    # A visible overlay (or a hit round-trips through children) must not leak
    # touches down to the library. on_touch_down returns None from the base
    # when no child consumes it.
    assert overlay.on_touch_down(touch) is None


# ---------- batch actions ----------

def test_batch_mark_read_sets_last_chapter(tab):
    _make_novel("a:read", chapters=7)
    from core.progress import progress
    progress.flush()
    tab._library = [{"slug": "a:read", "title": "read", "count": 7}]
    tab._selected = {"a:read"}
    tab._batch_mark_read()
    assert progress.get_last("a:read") == 6   # count - 1 (0-based)
    progress.flush()


def test_batch_mark_read_skips_empty_novel(tab):
    _make_novel("a:none", chapters=0)
    from core.progress import progress
    tab._library = [{"slug": "a:none", "title": "none", "count": 0}]
    tab._selected = {"a:none"}
    tab._batch_mark_read()
    assert progress.get_last("a:none") is None


def test_batch_mark_unread_removes_history(tab):
    _make_novel("a:unread", chapters=5, last=3)
    from core.progress import progress
    progress.flush()
    tab._library = [{"slug": "a:unread", "title": "unread", "count": 5}]
    tab._selected = {"a:unread"}
    tab._batch_mark_unread()
    assert progress.get_last("a:unread") is None


def test_batch_track_and_untrack(tab):
    _make_novel("a:tr", chapters=5)
    from core.progress import progress
    progress.track("a:tr", "tr")
    tab._library = [{"slug": "a:tr", "title": "tr", "count": 5}]
    tab._selected = {"a:tr"}
    tab._batch_untrack()
    assert progress.is_tracked("a:tr") is False
    tab._batch_track()
    assert progress.is_tracked("a:tr") is True


def test_batch_delete_removes_folder_and_clears_selection(tab):
    _make_novel("a:del", chapters=3)
    tab._library = [{"slug": "a:del", "title": "del", "count": 3}]
    tab._selected = {"a:del"}
    tab._select_mode = True
    from unittest import mock
    with mock.patch("gui.screens.utils._delete_library") as deleter:
        tab._do_batch_delete(mock.Mock())
        assert deleter.call_args_list == [mock.call("a:del")]
    assert tab._selected == set()
    assert tab._select_mode is False
