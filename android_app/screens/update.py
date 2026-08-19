from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar

from async_runner import async_loop
from screens import utils
from screens.novel_list import _TapCard
from screens.topbar import TopBar


class UpdateTab(MDScreen):
    """Checks each library novel against its source's chapter list and lists
    the ones that have new chapters online, with a per-row update download."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._busy = False
        self._results = []

        self.topbar = TopBar(
            title="Updates",
            actions=[("refresh", self.refresh)],
        )

        body = ScrollView()
        content = MDBoxLayout(orientation="vertical", adaptive_height=True,
                              padding="16dp", spacing="8dp")

        self.info_label = MDLabel(
            text="", theme_text_color="Secondary",
            font_style="Caption", adaptive_height=True)
        content.add_widget(self.info_label)

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
        if self._busy:
            return
        self._busy = True
        self.list_view.clear_widgets()
        self.empty_label.text = ""
        self.info_label.text = "Checking for updates…"

        async def coro():
            out = []
            for n in utils._library_entries():
                slug = n["slug"]
                source = utils._get_source(slug)
                if source is None or getattr(source, "blocked", False):
                    continue
                raw = slug.split(":", 1)[-1] if ":" in slug else slug
                try:
                    chapters = await utils._get_chapters(source, raw)
                except Exception:
                    continue
                if not chapters:
                    continue
                local = len(utils._local_chapters(slug))
                if len(chapters) > local:
                    out.append({
                        "slug": slug,
                        "title": n["title"],
                        "new": len(chapters) - local,
                        "chapters": chapters[local:],
                        "source": source,
                        "total": len(chapters),
                    })
            return out

        async_loop.run(coro(), self._on_done)

    def _on_done(self, results, error):
        self._busy = False
        self.list_view.clear_widgets()
        if error is not None:
            self.info_label.text = ""
            self.empty_label.text = "Update check failed. Check your connection."
            return
        self._results = results or []
        if not self._results:
            self.info_label.text = ""
            self.empty_label.text = "All novels are up to date."
            return
        self.info_label.text = f"{len(self._results)} novel(s) with new chapters"
        for r in self._results:
            self.list_view.add_widget(self._make_row(r))

    def _make_row(self, res):
        row = _TapCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(76),
            padding="12dp",
            spacing="16dp",
        )
        texts = MDBoxLayout(orientation="vertical", size_hint_y=1, spacing="2dp")
        texts.add_widget(MDLabel(
            text=res["title"], bold=True,
            font_style="Subtitle1", size_hint_y=None, height="24dp"))
        texts.add_widget(MDLabel(
            text=f"{res['new']} new chapter(s)", theme_text_color="Secondary",
            font_style="Caption", size_hint_y=None, height="18dp"))
        row.add_widget(texts)
        btn = MDIconButton(icon="download", on_release=lambda *_, r=res: self._update(r))
        row.add_widget(btn)
        row.on_release = lambda r=res: self._open(r)
        return row

    def _open(self, res):
        utils._open_chapters_for(
            {"slug": res["slug"].split(":", 1)[-1], "title": res["title"], "cover": ""},
            res["source"],
            fallback=utils._local_chapters(res["slug"]),
        )

    def _update(self, res):
        if not res.get("chapters"):
            return
        MDApp.get_running_app().goto(
            "download_progress",
            chapters=res["chapters"],
            slug=res["slug"],
            source=res["source"],
            title=res["title"],
            total=res["total"],
        )