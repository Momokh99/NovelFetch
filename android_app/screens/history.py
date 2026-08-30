from datetime import datetime, timedelta
import os

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.relativelayout import RelativeLayout

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.fitimage import FitImage
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from progress import _scan_library, progress
from async_runner import async_loop
from screens import utils, theme

_time_ago = utils._time_ago


def _gap_spacer():
    return MDBoxLayout(size_hint_y=None, height=theme.SECTION_GAP)


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
            first = True
            for bucket, rows in self._bucket(history):
                if not first:
                    self.list_view.add_widget(_gap_spacer())
                first = False
                if bucket:
                    self.list_view.add_widget(self._make_header(bucket))
                for h in rows:
                    slug = h["slug"]
                    title = self._title_for(slug, titles)
                    self.list_view.add_widget(self._make_row(slug, title, h))

        async_loop.run(coro(), on_done, timeout=10)

    @staticmethod
    def _bucket(history):
        """Bucket history rows (newest first) into Today / Yesterday /
        This week / Older, inserting a bucket header before each group."""
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())

        def bucket_for(h):
            dt = datetime.fromtimestamp(h["last_time"]).replace(
                hour=0, minute=0, second=0, microsecond=0)
            if dt >= today:
                return "Today"
            if dt >= yesterday:
                return "Yesterday"
            if dt >= week_start:
                return "This week"
            return "Older"

        order = ["Today", "Yesterday", "This week", "Older"]
        buckets = {b: [] for b in order}
        for h in history:
            buckets[bucket_for(h)].append(h)
        out = []
        for b in order:
            if buckets[b]:
                out.append((b, buckets[b]))
        return out

    @staticmethod
    def _make_header(text):
        box = MDBoxLayout(
            orientation="vertical", adaptive_height=True,
            padding=(dp(4), dp(2), dp(4), dp(10)))
        box.add_widget(MDLabel(
            text=text, bold=True,
            theme_text_color="Secondary",
            font_style="Label", role="large"))
        return box

    def _clear_history(self):
        progress.clear_history()
        self.refresh()
        utils._snack("History cleared")

    def _title_for(self, slug, titles):
        meta = utils._read_meta(slug)
        return meta.get("title") or titles.get(slug, slug.split(":", 1)[-1])

    def _make_row(self, slug, title, h):
        row = MDCard(
            orientation="horizontal",
            size_hint_y=None,
            height="68dp",
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

        texts = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(48), spacing="2dp",
                            pos_hint={"center_x": 0.5, "center_y": 0.5})
        texts.add_widget(MDLabel(
            text=title, bold=True,
            font_style="Title", role="medium", size_hint_y=None, height="26dp",
            shorten=True, shorten_from="right", max_lines=1))
        texts.add_widget(MDLabel(
            text=f"Ch. {h['last'] + 1} · {_time_ago(h['last_time'])}",
            theme_text_color="Secondary",
            font_style="Label", role="large", size_hint_y=None, height="20dp"))
        texts_rl = RelativeLayout(size_hint=(1, 1))
        texts_rl.add_widget(texts)
        row.add_widget(texts_rl)

        source = utils._get_source(slug)
        remove = MDIconButton(
            icon="delete", theme_text_color="Secondary",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            on_release=lambda *_, s=slug: self._remove_entry(s))
        # Center the action button vertically within the row.
        remove_rl = RelativeLayout(size_hint=(None, 1), width=dp(48))
        remove_rl.add_widget(remove)
        row.add_widget(remove_rl)

        def _tap(*_, s=slug, t=title, src=source, last=h["last"]):
            self._resume(s, t, src, last)
        row.on_release = _tap
        return row

    def _remove_entry(self, slug):
        progress.remove_history_entry(slug)
        self.refresh()
        utils._snack("Removed from history")

    def _resume(self, slug, title, source, last):
        """Resume reading at the last chapter if we have it, else open the
        chapter list."""
        chapters = utils._local_chapters(slug)
        if chapters:
            MDApp.get_running_app().goto(
                "reader",
                chapters=chapters,
                slug=slug,
                source=source,
                title=title or slug,
                start=last if 0 <= last < len(chapters) else 0,
            )
            return
        self._open(slug, title, source)

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