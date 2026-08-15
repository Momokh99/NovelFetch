from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList
from kivymd.uix.screen import MDScreen
from kivymd.uix.toolbar import MDTopAppBar

from screens import utils


class _TapCard(MDCard, ButtonBehavior):
    """MDCard lacks ButtonBehavior in KivyMD 1.2, so MDCard.on_release doesn't
    exist. Adding ButtonBehavior gives us a working on_release for taps."""


class NovelListScreen(MDScreen):
    """Search/browse results. Data arrives via load(), the goto() contract."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.novels = []
        self.source = None

        self.topbar = MDTopAppBar(
            title="Results",
            left_action_items=[["arrow-left", lambda *_: self._back()]],
        )
        self.add_widget(self.topbar)

        body = ScrollView()
        self.list_view = MDList()
        body.add_widget(self.list_view)
        self.add_widget(body)

    def load(self, novels, source=None, title="Results"):
        # Populated fresh on every goto("novel_list", ...) call.
        self.novels = novels
        self.source = source
        self.topbar.title = f"{title} ({len(novels)})" if novels else title
        self.list_view.clear_widgets()
        for n in novels:
            self.list_view.add_widget(self._make_row(n))

    def _make_row(self, novel):
        row = _TapCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(120),
            padding="12dp",
            spacing="16dp",
        )
        cover = novel.get("cover", "") or ""
        img = AsyncImage(
            source=cover,               # loads http cover off-thread
            size_hint=(None, 1),
            width=dp(70),
            keep_ratio=True,
            allow_stretch=True,
        )
        texts = MDBoxLayout(orientation="vertical", size_hint_y=1, spacing="2dp")
        texts.add_widget(MDLabel(
            text=novel["title"], bold=True,
            font_style="Subtitle1", size_hint_y=None, height="28dp"))
        sub = novel.get("author", "") or ""
        if novel.get("latest"):
            sub += f"  ·  {novel['latest']}"
        texts.add_widget(MDLabel(
            text=sub, theme_text_color="Secondary",
            font_style="Caption", size_hint_y=None, height="20dp"))
        row.add_widget(img)
        row.add_widget(texts)
        row.add_widget(utils._add_to_library_icon(novel, self.source))
        row.on_release = lambda: self._open(novel)   # closure: one novel per row
        return row

    def _open(self, novel):
        # Basic guard: disable further taps while one fetch is in flight.
        source = self.source or utils._get_source(novel.get("slug", ""))
        utils._open_chapters_for(novel, source,
                                 set_loading=lambda s: setattr(self.list_view, "disabled", s))

    def _back(self):
        MDApp.get_running_app().back()