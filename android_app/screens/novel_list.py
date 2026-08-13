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
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.toolbar import MDTopAppBar

from async_runner import async_loop
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
        self.topbar.title = title
        self.topbar.subtitle = f"{len(novels)} novels"
        self.list_view.clear_widgets()
        for n in novels:
            self.list_view.add_widget(self._make_row(n))

    def _make_row(self, novel):
        row = _TapCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(76),
            padding="12dp",
            spacing="12dp",
        )
        cover = novel.get("cover", "") or ""
        img = AsyncImage(
            source=cover,               # loads http cover off-thread
            size_hint=(None, None),
            size=(dp(44), dp(60)),
            keep_ratio=True,
            allow_stretch=True,
        )
        texts = MDBoxLayout(orientation="vertical", adaptive_height=True)
        texts.add_widget(MDLabel(text=novel["title"], bold=True, adaptive_height=True))
        sub = novel.get("author", "") or ""
        if novel.get("latest"):
            sub += f"  ·  {novel['latest']}"
        texts.add_widget(MDLabel(
            text=sub, theme_text_color="Secondary",
            font_style="Caption", adaptive_height=True))
        row.add_widget(img)
        row.add_widget(texts)
        row.on_release = lambda: self._open(novel)   # closure: one novel per row
        return row

    def _open(self, novel):
        # Basic guard: disable further taps while one fetch is in flight.
        self.list_view.disabled = True
        source = self.source or utils._get_source(novel.get("slug", ""))
        if source is None:
            MDSnackbar(text="No source for this novel.").open()
            self.list_view.disabled = False
            return
        bare = novel["slug"]

        async def coro():
            return await utils._get_chapters(source, bare)

        async_loop.run(coro(), lambda res, err: self._on_chapters(res, err, novel, source))

    def _on_chapters(self, chapters, error, novel, source):
        self.list_view.disabled = False
        if error is not None:
            MDSnackbar(text="Failed to fetch chapters. Check your connection.").open()
        elif not chapters:
            MDSnackbar(text="No chapters found.").open()
        else:
            MDApp.get_running_app().goto(
                "chapter_list",
                chapters=chapters,
                slug=source.qualify_slug(novel["slug"]),
                source=source,
                title=novel["title"],
            )

    def _back(self):
        MDApp.get_running_app().goto("tabs")