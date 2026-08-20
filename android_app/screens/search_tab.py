from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import AsyncImage

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar

from async_runner import async_loop
from screens import utils, theme
from screens.browse import BrowseSection
from screens.novel_list import _TapCard
from screens.source_picker import open_source_picker


class SearchTab(MDScreen):
    """Browse rows + genres on top, with a live search bar above them.
    Search results render inline below the bar; browsing hides while shown."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._busy = False
        self._debounce = None
        self._clearing = False

        # Widget tree lives in kv/search_tab.kv; alias the runtime-touched nodes.
        self.topbar = self.ids.topbar
        self.source_label = self.ids.source_label
        self.source_btn = self.ids.source_btn
        self.search_field = self.ids.search_field
        self.clear_btn = self.ids.clear_btn
        self.browse_box = self.ids.browse_box
        self.results_box = self.ids.results_box
        self.results_list = self.ids.results_list

        # current_source is set in App.on_start(), AFTER build(). A zero-delay
        # Clock callback fires on the first frame — after on_start has run.
        Clock.schedule_once(lambda dt: self.refresh_source(), 0)

    def _open_source_picker(self):
        open_source_picker()

    # ---------- source switcher ----------

    def refresh_source(self):
        """Update the source-switch button label to the active source."""
        source = MDApp.get_running_app().current_source
        self.source_label.text = f"Source: {source.label}" if source else "No source"
        self.source_btn.icon = "swap-horizontal"

    # ---------- search ----------

    def _on_text_changed(self):
        if self._clearing:
            return
        # Debounce: cancel the previous timer, re-arm for 700ms of quiet typing.
        if self._debounce is not None:
            self._debounce.cancel()
        self._debounce = Clock.schedule_once(lambda dt: self._do_search(), 0.7)

    def _on_enter(self):
        if self._debounce is not None:
            self._debounce.cancel()
            self._debounce = None
        self._do_search()

    def _do_search(self):
        query = self.search_field.text.strip()
        if not query or self._busy:
            return
        source = MDApp.get_running_app().current_source
        if source is None:
            MDSnackbar(MDLabel(text="No source selected.")).open()
            return
        if not source.search_supported:
            MDSnackbar(MDLabel(text="Search is not supported for this source.")).open()
            return

        async def coro():
            novels, _pages = await source.search(query, page=1)
            return novels

        self._busy = True
        self.search_field.disabled = True
        async_loop.run(coro(), lambda res, err, q=query: self._on_done(res, err, q))

    def _on_done(self, novels, error, query):
        self._busy = False
        self.search_field.disabled = False
        source = MDApp.get_running_app().current_source
        blocked = getattr(source, "blocked", False)
        if error is not None:
            self._clear_results()
            MDSnackbar(MDLabel(text="Search failed. Check your connection.")).open()
        elif blocked:
            self._clear_results()
            MDSnackbar(MDLabel(text=f"{source.label} is blocked by anti-bot protection.")).open()
        elif not novels:
            self._clear_results()
            MDSnackbar(MDLabel(text="No novels found.")).open()
        else:
            self._show_results(novels)

    # ---------- inline results ----------

    def _show_results(self, novels):
        self.results_list.clear_widgets()
        for n in novels:
            self.results_list.add_widget(self._make_row(n))
        # Swap: drop browse, surface results right under the search bar.
        if self.browse_box.parent is not None:
            self.browse_box.parent.remove_widget(self.browse_box)
        self.results_box.opacity = 1
        self.results_box.disabled = False

    def _make_row(self, novel):
        row = _TapCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(120),
            padding=theme.CARD_PAD, spacing=theme.CARD_GAP,
        )
        cover = novel.get("cover", "") or ""
        img = AsyncImage(
            source="",               # set via httpx cache (see set_image_url)
            size_hint=(None, 1),
            width=dp(70),
            keep_ratio=True,
            allow_stretch=True,
        )
        if cover:
            utils.set_image_url(img, cover)
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
        row.add_widget(utils._add_to_library_icon(
            novel, MDApp.get_running_app().current_source))
        row.on_release = lambda n=novel: self._open(n)
        return row

    def _open(self, novel):
        # Tapping a result drills into the chapter list (full screen, as before).
        source = MDApp.get_running_app().current_source
        utils._open_chapters_for(
            novel, source,
            set_loading=lambda s: setattr(self.results_list, "disabled", s))

    def _clear_results(self):
        self.results_list.clear_widgets()
        self.results_box.opacity = 0
        self.results_box.disabled = True
        # Restore browse right under the search bar (parent = the scroll content).
        if self.results_box.parent is not None and self.browse_box.parent is None:
            self.results_box.parent.add_widget(self.browse_box)

    def _clear(self):
        if self._debounce is not None:
            self._debounce.cancel()
            self._debounce = None
        self._clearing = True
        self.search_field.text = ""
        self._clearing = False
        self._clear_results()