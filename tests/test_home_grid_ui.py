"""Tests for the Mihon-style Home library grid: bare covers, unread badges,
and the library count in the top bar."""

import json
import os

import pytest
from kivy.core.window import Window
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.label import MDLabel

from screens.home_tab import _badge_text, _unread_count

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "android_app")


def _find(widget, cls):
    if isinstance(widget, cls):
        return widget
    for child in widget.children:
        found = _find(child, cls)
        if found:
            return found
    return None


def _labels(widget):
    texts = []
    if isinstance(widget, MDLabel):
        texts.append(widget.text)
    for child in widget.children:
        texts.extend(_labels(child))
    return texts


class _HomeApp(MDApp):
    def build(self):
        from screens.home_tab import HomeTab
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
    yield win


def _make_novel(slug, chapters, last=None, title=None, cover="cover.png"):
    os.makedirs(os.path.join("novels", slug), exist_ok=True)
    if cover:
        open(os.path.join("novels", slug, cover), "wb").write(b"x")
    meta = {"title": title or slug, "cover": cover, "chapters": chapters}
    with open(os.path.join("novels", slug, "meta.json"), "w") as f:
        json.dump(meta, f)
    if last is not None:
        from progress import progress
        progress.mark_seen(slug, last)
    return {"slug": slug, "title": title or slug, "count": chapters}


# ---------- pure helpers ----------

def test_unread_count_from_start():
    assert _unread_count(10, None) == 10


def test_unread_count_after_reading():
    assert _unread_count(10, 3) == 6  # last is a 0-based index


def test_unread_count_fully_read():
    assert _unread_count(5, 4) == 0


def test_unread_count_does_not_go_negative():
    assert _unread_count(3, 10) == 0


def test_unread_count_no_chapters():
    assert _unread_count(0, None) == 0


def test_badge_text_small():
    assert _badge_text(5) == "5"


def test_badge_text_caps_at_999():
    assert _badge_text(999) == "999"
    assert _badge_text(1000) == "999+"
    assert _badge_text(1300) == "999+"


# ---------- cover rendering path ----------

def test_grid_card_draws_cover(tab):
    from screens.home_tab import _FitCover
    novel = _make_novel("a:cover_g", chapters=4)
    card = tab._grid_card(novel, cols=2)
    cover = _find(card, _FitCover)
    assert cover is not None
    assert cover.source == os.path.join("novels", novel["slug"], "cover.png")


def test_continue_card_draws_cover(tab):
    from screens.home_tab import _FitCover
    novel = _make_novel("a:cover_c", chapters=4, last=1)
    card = tab._continue_card(novel)
    cover = _find(card, _FitCover)
    assert cover is not None
    assert cover.source == os.path.join("novels", novel["slug"], "cover.png")


def test_grid_cover_has_direct_cover_child(tab):
    from kivy.uix.floatlayout import FloatLayout
    from screens.home_tab import _FitCover
    novel = _make_novel("a:direct_g", chapters=10, last=2)
    cbox = tab._grid_cover(novel, cols=2)
    assert _find(cbox, FloatLayout) is None  # no overlay between cbox and cover
    cover = _find(cbox, _FitCover)
    assert cover is not None
    assert cover.parent is cbox


def test_continue_card_cover_has_direct_child(tab):
    from kivy.uix.floatlayout import FloatLayout
    from screens.home_tab import _FitCover
    novel = _make_novel("a:direct_c", chapters=4, last=0)
    card = tab._continue_card(novel)
    assert _find(card, FloatLayout) is None
    cover = _find(card, _FitCover)
    assert cover is not None
    assert cover.parent is not None


# ---------- grid card widgets ----------

def test_grid_card_is_bare(tab):
    novel = _make_novel("a:one", chapters=4)
    card = tab._grid_card(novel, cols=2)
    assert card.elevation == 0
    assert card.md_bg_color == [0, 0, 0, 0]


def test_grid_card_shows_only_title_below_cover(tab):
    novel = _make_novel("a:two", chapters=4)
    from screens.novel_list import _TapCard as _Card
    card = tab._grid_card(novel, cols=2)
    assert isinstance(card, _Card)
    texts = _labels(card)
    assert novel["title"] in texts
    assert not any(t.startswith("Ch.") for t in texts)  # no progress caption


def test_grid_card_badge_shows_unread(tab):
    from screens.home_tab import UnreadBadge
    novel = _make_novel("a:three", chapters=10, last=3)
    card = tab._grid_card(novel, cols=2)
    badge = _find(card, UnreadBadge)
    assert badge is not None
    assert badge.count == 6
    assert badge._label.text == "6"


def test_grid_card_no_badge_when_fully_read(tab):
    from screens.home_tab import UnreadBadge
    novel = _make_novel("a:four", chapters=5, last=4)
    card = tab._grid_card(novel, cols=2)
    assert _find(card, UnreadBadge) is None


def test_continue_card_gets_unread_badge(tab):
    from screens.home_tab import UnreadBadge
    novel = _make_novel("a:five", chapters=8)
    card = tab._continue_card(novel)
    badge = _find(card, UnreadBadge)
    assert badge is not None
    assert badge.count == 8


# ---------- top bar count ----------

def test_topbar_title_shows_library_count(tab):
    tab._build_library([_make_novel("a:six", chapters=2),
                        _make_novel("b:seven", chapters=3)])
    assert tab.topbar.ids.title_label.text == "NovelFetch · 2"


def test_topbar_title_resets_when_empty(tab):
    tab._build_library([])
    assert tab.topbar.ids.title_label.text == "NovelFetch"


def test_layout_a_uses_bare_grid_card(tab):
    _make_novel("a:eight", chapters=4)
    _make_novel("b:nine", chapters=3)
    from screens.novel_list import _TapCard as _Card
    tab._layout_A([
        {"slug": "a:eight", "title": "eight", "count": 4},
        {"slug": "b:nine", "title": "nine", "count": 3},
    ])
    # Every grid tile is a bare tap card, not a raised one.
    for card in tab.content_box.walk():
        if isinstance(card, _Card):
            assert card.elevation == 0