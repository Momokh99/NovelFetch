from datetime import datetime
import os

from kivy.clock import Clock
from kivy.metrics import dp

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.fitimage import FitImage
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from progress import _scan_library, progress
from async_runner import async_loop
from screens import utils, theme
from screens.novel_list import _TapCard


def _time_ago(timestamp):
    if not timestamp:
        return ""
    delta = datetime.now().timestamp() - timestamp
    if delta < 60:
        return "just now"
    minutes = int(delta // 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h ago"
    days = int(hours // 24)
    if days < 7:
        return f"{days}d ago"
    weeks = int(days // 7)
    return f"{weeks}w ago"


class HistoryTab(MDScreen):
    """Recently-read novels, newest first, with the last chapter reached."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Widget tree lives in kv/history.kv; alias the runtime-touched nodes.
        self.topbar = self.ids.topbar
        self.topbar.set_actions([("delete", self._clear_history)])
        self.empty_box = self.ids.empty_box
        self.list_view = self.ids.list_view

        # Populate on first frame (after on_start sets up sources), like Home.
        Clock.schedule_once(lambda dt: self.refresh(), 0)

    def load(self, **kwargs):
        self.refresh()

    def refresh(self):
        self.list_view.clear_widgets()

        async def coro():
            history = progress.get_history()
            titles = {n["slug"]: n["title"] for n in _scan_library()}
            return history, titles

        def on_done(result, error):
            if error is not None:
                return
            history, titles = result
            if not history:
                self.empty_box.opacity = 1
                self.empty_box.height = self.empty_box.minimum_height
                return
            self.empty_box.opacity = 0
            self.empty_box.height = 0
            for h in history:
                slug = h["slug"]
                title = self._title_for(slug, titles)
                self.list_view.add_widget(self._make_row(slug, title, h))

        async_loop.run(coro(), on_done, timeout=10)

    def _clear_history(self):
        progress.clear_history()
        self.refresh()
        utils._snack("History cleared")

    def _title_for(self, slug, titles):
        meta = utils._read_meta(slug)
        return meta.get("title") or titles.get(slug, slug.split(":", 1)[-1])

    def _make_row(self, slug, title, h):
        row = _TapCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(76),
            padding=theme.CARD_PAD, spacing=theme.CARD_GAP,
        )
        cover = self._cover_path(slug)
        if cover:
            cover_box = MDBoxLayout(
                size_hint=(None, 1), width=dp(48),
                radius=[8, 8, 8, 8], md_bg_color=theme.surface_color(),
            )
            cover_box.add_widget(FitImage(
                source=cover, radius=[8, 8, 8, 8], size_hint=(1, 1)))
            row.add_widget(cover_box)
        texts = MDBoxLayout(orientation="vertical", size_hint_y=1, spacing="2dp")
        texts.add_widget(MDLabel(
            text=title, bold=True,
            font_style="Subtitle1", size_hint_y=None, height="24dp",
            shorten=True, shorten_from="right", max_lines=1))
        texts.add_widget(MDLabel(
            text=f"Ch. {h['last'] + 1} · {_time_ago(h['last_time'])}",
            theme_text_color="Secondary",
            font_style="Caption", size_hint_y=None, height="18dp"))
        row.add_widget(texts)
        source = utils._get_source(slug)
        row.on_release = lambda s=slug, t=title, src=source: self._open(s, t, src)
        return row

    def _cover_path(self, slug):
        meta = utils._read_meta(slug)
        cover = meta.get("cover")
        if not cover:
            return ""
        path = os.path.join("novels", slug, cover)
        return path if os.path.exists(path) else ""

    def _open(self, slug, title, source):
        raw = slug.split(":", 1)[-1] if ":" in slug else slug
        utils._open_chapters_for(
            {"slug": raw, "title": title or slug, "cover": ""},
            source,
            fallback=utils._local_chapters(slug),
        )