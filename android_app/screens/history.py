from datetime import datetime

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList
from kivymd.uix.screen import MDScreen

from progress import _scan_library, progress
from screens import utils
from screens.novel_list import _TapCard
from screens.topbar import TopBar


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
        self.topbar = TopBar(title="History")

        body = ScrollView()
        content = MDBoxLayout(orientation="vertical", adaptive_height=True,
                              padding="16dp", spacing="8dp")

        self.empty_label = MDLabel(
            text="", halign="center", bold=True, adaptive_height=True)
        content.add_widget(self.empty_label)

        self.list_view = MDList()
        content.add_widget(self.list_view)

        body.add_widget(content)
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(self.topbar)
        root.add_widget(body)
        self.add_widget(root)

        # Populate on first frame (after on_start sets up sources), like Home.
        Clock.schedule_once(lambda dt: self.refresh(), 0)

    def load(self, **kwargs):
        self.refresh()

    def refresh(self):
        self.list_view.clear_widgets()
        history = progress.get_history()
        if not history:
            self.empty_label.text = "No reading history yet."
            return
        self.empty_label.text = ""
        titles = {n["slug"]: n["title"] for n in _scan_library()}
        for h in history:
            slug = h["slug"]
            title = self._title_for(slug, titles)
            self.list_view.add_widget(self._make_row(slug, title, h))

    def _title_for(self, slug, titles):
        meta = utils._read_meta(slug)
        return meta.get("title") or titles.get(slug, slug.split(":", 1)[-1])

    def _make_row(self, slug, title, h):
        row = _TapCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(76),
            padding="12dp",
            spacing="16dp",
        )
        texts = MDBoxLayout(orientation="vertical", size_hint_y=1, spacing="2dp")
        texts.add_widget(MDLabel(
            text=title, bold=True,
            font_style="Subtitle1", size_hint_y=None, height="24dp"))
        texts.add_widget(MDLabel(
            text=f"Ch. {h['last'] + 1} · {_time_ago(h['last_time'])}",
            theme_text_color="Secondary",
            font_style="Caption", size_hint_y=None, height="18dp"))
        row.add_widget(texts)
        source = utils._get_source(slug)
        row.on_release = lambda s=slug, t=title, src=source: self._open(s, t, src)
        return row

    def _open(self, slug, title, source):
        raw = slug.split(":", 1)[-1] if ":" in slug else slug
        utils._open_chapters_for(
            {"slug": raw, "title": title or slug, "cover": ""},
            source,
            fallback=utils._local_chapters(slug),
        )